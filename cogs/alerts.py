import os
import re
import time
import xml.etree.ElementTree as ET
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks
import database as db
import core_engine as engine

TWITCH_CLIENT_ID = engine.TWITCH_CLIENT_ID
TWITCH_CLIENT_SECRET = engine.TWITCH_CLIENT_SECRET
TWITCH_CHANNEL = engine.TWITCH_CHANNEL
YOUTUBE_API_KEY = engine.YOUTUBE_API_KEY
YOUTUBE_CHANNEL_ID = engine.clean_env("YOUTUBE_CHANNEL_ID")
TWITTER_USERNAME = engine.clean_env("TWITTER_USERNAME", "tei_0415").lstrip("@")

NITTER_RSS_MIRRORS = [
    "https://nitter.poast.org/{user}/rss",
    "https://nitter.privacydev.net/{user}/rss",
    "https://xcancel.com/{user}/rss",
    "https://nitter.net/{user}/rss"
]

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

    async def get_twitch_token(self, session: aiohttp.ClientSession) -> str:
        if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
            return ""
        url = "https://id.twitch.tv/oauth2/token"
        params = {
            "client_id": TWITCH_CLIENT_ID,
            "client_secret": TWITCH_CLIENT_SECRET,
            "grant_type": "client_credentials"
        }
        async with session.post(url, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                self.twitch_oauth_token = data.get("access_token", "")
        return self.twitch_oauth_token

    async def toggle_streamer_live_role(self, guild: discord.Guild, role_id: int, is_live: bool):
        if not role_id:
            return
        role = guild.get_role(role_id)
        if not role:
            return
        member = guild.get_member(1156965426044080188) or guild.owner
        if not member:
            return
        try:
            if is_live and role not in member.roles:
                await member.add_roles(role, reason="AwwMian went LIVE on Twitch")
            elif not is_live and role in member.roles:
                await member.remove_roles(role, reason="AwwMian stream ended")
        except Exception:
            pass

    # ==========================================
    # 1. TWITCH HELIX LIVE MONITOR (EVERY 60s)
    # ==========================================
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

            headers = {
                "Client-ID": TWITCH_CLIENT_ID,
                "Authorization": f"Bearer {self.twitch_oauth_token}"
            }
            url = f"https://api.twitch.tv/helix/streams?user_login={TWITCH_CHANNEL}"
            async with session.get(url, headers=headers) as resp:
                if resp.status == 401:
                    await self.get_twitch_token(session)
                    return
                if resp.status != 200:
                    return
                data = await resp.json()

            streams = data.get("data", [])
            is_live_now = len(streams) > 0

            for guild in self.bot.guilds:
                cfg = await db.get_guild_config(guild.id)
                if not cfg or not cfg.get("twitch_channel_id"):
                    continue

                was_live = bool(cfg.get("is_currently_live", 0))
                live_role_id = cfg.get("live_streamer_role_id")

                if is_live_now and not was_live:
                    stream_info = streams[0]
                    await db.save_guild_config(guild.id, is_currently_live=1)
                    await self.toggle_streamer_live_role(guild, live_role_id, True)

                    alert_ch = guild.get_channel(cfg["twitch_channel_id"])
                    ping_role = guild.get_role(cfg.get("stream_ping_role_id") or 0)
                    if alert_ch:
                        title = stream_info.get("title", "LIVE NOW!")
                        game = stream_info.get("game_name", "VALORANT / osu!")
                        viewers = stream_info.get("viewer_count", 1)
                        thumb_url = stream_info.get("thumbnail_url", "").replace("{width}", "1280").replace("{height}", "720")
                        thumb_url = f"{thumb_url}?t={int(time.time())}"

                        embed = discord.Embed(
                            title=f"🟣 {TWITCH_CHANNEL} is LIVE on Twitch!",
                            description=f"### [{title}](https://twitch.tv/{TWITCH_CHANNEL})",
                            url=f"https://twitch.tv/{TWITCH_CHANNEL}",
                            color=discord.Color.purple()
                        )
                        embed.add_field(name="🎮 Playing", value=game, inline=True)
                        embed.add_field(name="👁️ Viewers", value=str(viewers), inline=True)
                        embed.add_field(name="🔗 Watch Now", value=f"[twitch.tv/{TWITCH_CHANNEL}](https://twitch.tv/{TWITCH_CHANNEL})", inline=True)
                        if thumb_url.startswith("http"):
                            embed.set_image(url=thumb_url)
                        embed.set_footer(text="Lil Mian Live Engine • JST (GMT+9)")

                        ping_text = f"{ping_role.mention} **AwwMian is LIVE!** Tap in now!" if ping_role else "**AwwMian is LIVE!**"
                        await alert_ch.send(content=ping_text, embed=embed)

                elif not is_live_now and was_live:
                    await db.save_guild_config(guild.id, is_currently_live=0)
                    await self.toggle_streamer_live_role(guild, live_role_id, False)

    # ==========================================
    # 2. YOUTUBE RSS MONITOR (SHORTS VS LONG-FORM)
    # ==========================================
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

            if not self.resolved_yt_channel_id or not self.resolved_yt_channel_id.startswith("UC"):
                return

            rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={self.resolved_yt_channel_id}"
            async with session.get(rss_url) as resp:
                if resp.status != 200:
                    return
                xml_text = await resp.text()

            try:
                root = ET.fromstring(xml_text)
                ns = {
                    "atom": "http://www.w3.org/2005/Atom",
                    "yt": "http://www.youtube.com/xml/schemas/2015"
                }
                entries = root.findall("atom:entry", ns)
                if not entries:
                    return

                latest = entries[0]
                video_id = latest.find("yt:videoId", ns).text
                title = latest.find("atom:title", ns).text
                published = latest.find("atom:published", ns).text
                link_elem = latest.find("atom:link", ns)
                video_url = link_elem.attrib.get("href", f"https://youtu.be/{video_id}") if link_elem is not None else f"https://youtu.be/{video_id}"

                if await db.is_video_posted(video_id):
                    return
                await db.mark_video_posted(video_id, published)

                is_short = "/shorts/" in video_url.lower() or "#shorts" in title.lower()

                for guild in self.bot.guilds:
                    cfg = await db.get_guild_config(guild.id)
                    if not cfg:
                        continue
                    if is_short:
                        ch = guild.get_channel(cfg.get("shorts_channel_id") or 0)
                        role = guild.get_role(cfg.get("shorts_ping_role_id") or 0)
                        if ch:
                            ping_str = f"{role.mention} " if role else ""
                            await ch.send(f"📱 {ping_str}**New YouTube Short from @NotAwwMian!**\n**{title}**\n{video_url}")
                    else:
                        ch = guild.get_channel(cfg.get("yt_channel_id") or 0)
                        role = guild.get_role(cfg.get("yt_ping_role_id") or 0)
                        if ch:
                            ping_str = f"{role.mention} " if role else ""
                            await ch.send(f"📺 {ping_str}**@NotAwwMian just uploaded a new video!**\n**{title}**\n{video_url}")
            except Exception:
                pass

    # ==========================================
    # 3. AUTOMATIC TWITTER FEED MONITOR (EVERY 4 MINS)
    # ==========================================
    @tasks.loop(minutes=4)
    async def check_twitter_feed(self):
        await self.bot.wait_until_ready()
        if not TWITTER_USERNAME:
            return

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LilMianTwitterBot/5.0"}
        xml_data = None

        async with aiohttp.ClientSession(headers=headers) as session:
            for mirror in NITTER_RSS_MIRRORS:
                url = mirror.format(user=TWITTER_USERNAME)
                try:
                    async with session.get(url, timeout=6) as resp:
                        if resp.status == 200:
                            text = await resp.text()
                            if "<item>" in text:
                                xml_data = text
                                break
                except Exception:
                    continue

        if not xml_data:
            return

        try:
            root = ET.fromstring(xml_data)
            channel = root.find("channel")
            if channel is None:
                return
            items = channel.findall("item")
            if not items:
                return

            latest = items[0]
            link = latest.find("link").text if latest.find("link") is not None else ""
            pub_date = latest.find("pubDate").text if latest.find("pubDate") is not None else ""

            # Extract numeric Tweet ID from URL
            match = re.search(r"/status/(\d+)", link)
            if not match:
                return
            tweet_id = match.group(1)

            if await db.is_tweet_posted(tweet_id):
                return
            await db.mark_tweet_posted(tweet_id, pub_date)

            # Use fxtwitter.com so Discord natively embeds full Twitter videos, multiple photos & text!
            fx_url = f"https://fxtwitter.com/{TWITTER_USERNAME}/status/{tweet_id}"

            for guild in self.bot.guilds:
                cfg = await db.get_guild_config(guild.id)
                if not cfg:
                    continue
                ch = guild.get_channel(cfg.get("twitter_channel_id") or 0)
                if not ch:
                    ch = discord.utils.find(lambda c: "twitter" in c.name.lower() or "tweets" in c.name.lower(), guild.text_channels)
                role = guild.get_role(cfg.get("twitter_ping_role_id") or 0)

                if ch:
                    ping_str = f"{role.mention} " if role else ""
                    await ch.send(f"🐦 {ping_str}**@{TWITTER_USERNAME} just posted a new Tweet!**\n{fx_url}")
        except Exception:
            pass

    @app_commands.command(name="post_tweet", description="[ADMIN/AWWMIAN ONLY] Instantly beam a Tweet link into #twitter-feed with rich media!")
    @app_commands.default_permissions(administrator=True)
    async def post_tweet_cmd(self, interaction: discord.Interaction, tweet_url: str):
        await interaction.response.defer(ephemeral=True)
        # Convert x.com or twitter.com into fxtwitter.com for rich Discord video/image cards
        clean_url = re.sub(r"https?://(www\.)?(twitter\.com|x\.com)", "https://fxtwitter.com", tweet_url.strip())
        cfg = await db.get_guild_config(interaction.guild.id)
        ch = interaction.guild.get_channel(cfg.get("twitter_channel_id") or 0) if cfg else None
        if not ch:
            ch = discord.utils.find(lambda c: "twitter" in c.name.lower(), interaction.guild.text_channels) or interaction.channel
        role = interaction.guild.get_role(cfg.get("twitter_ping_role_id") or 0) if cfg else None
        ping_str = f"{role.mention} " if role else ""

        await ch.send(f"🐦 {ping_str}**New Tweet from AwwMian!**\n{clean_url}")
        await interaction.followup.send(f"✅ Tweet beamed to {ch.mention}!", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(AlertsCog(bot))