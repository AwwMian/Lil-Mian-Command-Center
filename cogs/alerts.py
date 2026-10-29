import os
import re
import time
import xml.etree.ElementTree as ET
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks
import core_engine as engine

TWITCH_CLIENT_ID = engine.TWITCH_CLIENT_ID
TWITCH_CLIENT_SECRET = engine.TWITCH_CLIENT_SECRET
TWITCH_CHANNEL = engine.TWITCH_CHANNEL
YOUTUBE_API_KEY = engine.YOUTUBE_API_KEY
YOUTUBE_CHANNEL_ID = engine.clean_env("YOUTUBE_CHANNEL_ID")
TWITTER_USERNAME = engine.clean_env("TWITTER_USERNAME", "tei_0415").lstrip("@")

class AlertsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.twitch_oauth_token: str = ""
        self.resolved_yt_channel_id: str = YOUTUBE_CHANNEL_ID
        self.check_twitch_live.start()
        self.check_youtube_rss.start()
        self.check_twitter_feed.start()

    def cog_unload(self):
        self.check_twitch_live.cancel()
        self.check_youtube_rss.cancel()
        self.check_twitter_feed.cancel()

    async def get_guild_cfg(self, guild_id: int) -> dict:
        cfg = await engine.get_guild_config(guild_id)
        return cfg or {}

    async def ensure_twitter_channel(self, guild: discord.Guild, cfg: dict) -> discord.TextChannel:
        ch = guild.get_channel(cfg.get("twitter_channel_id") or 0)
        if not ch:
            ch = discord.utils.find(lambda c: "twitter" in c.name.lower() or "tweets" in c.name.lower(), guild.text_channels)
        if not ch:
            cat = discord.utils.get(guild.categories, name="📡 AWWMIAN MEDIA HUB")
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(send_messages=False, read_messages=True),
                guild.me: discord.PermissionOverwrite(send_messages=True, read_messages=True, embed_links=True)
            }
            ch = await guild.create_text_channel("🐦・twitter-feed", category=cat, overwrites=overwrites)
            await engine.save_guild_config(guild.id, twitter_channel_id=ch.id)
        return ch

    async def get_twitch_token(self, session: aiohttp.ClientSession) -> str:
        if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
            return ""
        url = "https://id.twitch.tv/oauth2/token"
        params = {"client_id": TWITCH_CLIENT_ID, "client_secret": TWITCH_CLIENT_SECRET, "grant_type": "client_credentials"}
        async with session.post(url, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                self.twitch_oauth_token = data.get("access_token", "")
        return self.twitch_oauth_token

    @tasks.loop(seconds=60)
    async def check_twitch_live(self):
        await self.bot.wait_until_ready()
        if not TWITCH_CLIENT_ID or TWITCH_CLIENT_ID == "your_twitch_client_id":
            return
        async with aiohttp.ClientSession() as session:
            if not self.twitch_oauth_token:
                await self.get_twitch_token(session)
            if not self.twitch_oauth_token:
                return
            headers = {"Client-ID": TWITCH_CLIENT_ID, "Authorization": f"Bearer {self.twitch_oauth_token}"}
            url = f"https://api.twitch.tv/helix/streams?user_login={TWITCH_CHANNEL}"
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    streams = data.get("data", [])
                    is_live = len(streams) > 0
                    for guild in self.bot.guilds:
                        cfg = await self.get_guild_cfg(guild.id)
                        was_live = bool(cfg.get("is_currently_live", 0))
                        if is_live and not was_live:
                            await engine.save_guild_config(guild.id, is_currently_live=1)
                            alert_ch = guild.get_channel(cfg.get("twitch_channel_id") or 0)
                            if alert_ch:
                                await alert_ch.send(f"🟣 **AwwMian is LIVE on Twitch!** https://twitch.tv/{TWITCH_CHANNEL}")
                        elif not is_live and was_live:
                            await engine.save_guild_config(guild.id, is_currently_live=0)

    @tasks.loop(minutes=5)
    async def check_youtube_rss(self):
        await self.bot.wait_until_ready()
        async with aiohttp.ClientSession() as session:
            if (not self.resolved_yt_channel_id or not self.resolved_yt_channel_id.startswith("UC")) and YOUTUBE_API_KEY:
                api_url = f"https://www.googleapis.com/youtube/v3/channels?part=id&forHandle=@NotAwwMian&key={YOUTUBE_API_KEY}"
                async with session.get(api_url) as resp:
                    if resp.status == 200:
                        js = await resp.json()
                        items = js.get("items", [])
                        if items:
                            self.resolved_yt_channel_id = items[0]["id"]
            if not self.resolved_yt_channel_id:
                return
            rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={self.resolved_yt_channel_id}"
            async with session.get(rss_url) as resp:
                if resp.status != 200:
                    return
                xml_text = await resp.text()
            try:
                root = ET.fromstring(xml_text)
                ns = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
                entries = root.findall("atom:entry", ns)
                if not entries:
                    return
                latest = entries[0]
                video_id = latest.find("yt:videoId", ns).text
                title = latest.find("atom:title", ns).text
                published = latest.find("atom:published", ns).text
                if await engine.is_video_posted(video_id):
                    return
                await engine.mark_video_posted(video_id, published)
                video_url = f"https://youtu.be/{video_id}"
                for guild in self.bot.guilds:
                    cfg = await self.get_guild_cfg(guild.id)
                    ch = guild.get_channel(cfg.get("yt_channel_id") or 0)
                    if ch:
                        await ch.send(f"📺 **@NotAwwMian uploaded a new video!**\n**{title}**\n{video_url}")
            except Exception:
                pass

    @tasks.loop(minutes=3)
    async def check_twitter_feed(self):
        await self.bot.wait_until_ready()
        if not TWITTER_USERNAME:
            return

        # Query public Syndication JSON endpoint (works 100% reliably on cloud IPs)
        url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{TWITTER_USERNAME}"
        async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
            try:
                async with session.get(url, timeout=6) as resp:
                    if resp.status != 200:
                        return
                    text = await resp.text()
                    ids = re.findall(r'status/(\d{15,22})', text)
                    if not ids:
                        ids = re.findall(r'"id_str"\s*:\s*"(\d{15,22})"', text)
                    if not ids:
                        return
                    tweet_id = str(max(int(i) for i in ids))
            except Exception:
                return

        if await engine.is_tweet_posted(tweet_id):
            return
        await engine.mark_tweet_posted(tweet_id, str(int(time.time())))

        fx_url = f"https://fxtwitter.com/{TWITTER_USERNAME}/status/{tweet_id}"

        for guild in self.bot.guilds:
            cfg = await self.get_guild_cfg(guild.id)
            ch = await self.ensure_twitter_channel(guild, cfg)
            if ch:
                await ch.send(f"🐦 **New Tweet from @{TWITTER_USERNAME}!**\n{fx_url}")

    @app_commands.command(name="post_tweet", description="[ADMIN ONLY] Instantly beam a Tweet link into #twitter-feed with rich embed")
    @app_commands.default_permissions(administrator=True)
    async def post_tweet_cmd(self, interaction: discord.Interaction, tweet_url: str):
        await interaction.response.defer(ephemeral=True)
        clean_url = re.sub(r"https?://(www\.)?(twitter\.com|x\.com)", "https://fxtwitter.com", tweet_url.strip())
        cfg = await self.get_guild_cfg(interaction.guild.id)
        ch = await self.ensure_twitter_channel(interaction.guild, cfg)
        await ch.send(f"🐦 **New Tweet from @{TWITTER_USERNAME}!**\n{clean_url}")
        await interaction.followup.send(f"✅ Tweet beamed to {ch.mention}!", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(AlertsCog(bot))