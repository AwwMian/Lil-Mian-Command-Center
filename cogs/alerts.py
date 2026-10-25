import os
import time
import xml.etree.ElementTree as ET
import aiohttp
import discord
from discord.ext import commands, tasks
import database as db
import core_engine as engine

TWITCH_CLIENT_ID = engine.TWITCH_CLIENT_ID
TWITCH_CLIENT_SECRET = engine.TWITCH_CLIENT_SECRET
TWITCH_CHANNEL = engine.TWITCH_CHANNEL
YOUTUBE_API_KEY = engine.YOUTUBE_API_KEY
YOUTUBE_CHANNEL_ID = engine.clean_env("YOUTUBE_CHANNEL_ID")

class AlertsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.twitch_oauth_token: str = ""
        self.resolved_yt_channel_id: str = YOUTUBE_CHANNEL_ID
        self.check_twitch_live.start()
        self.check_youtube_rss.start()

    def cog_unload(self):
        self.check_twitch_live.cancel()
        self.check_youtube_rss.cancel()

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
        # Find @awwmian or Server Owner
        member = discord.utils.find(lambda m: m.name.lower() == "awwmian", guild.members) or guild.owner
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
                    # Stream just started!
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
                        embed.set_footer(text="Lil Mian Streamcord Engine • JST (GMT+9)")

                        ping_text = f"{ping_role.mention} **AwwMian is LIVE!** Tap in now!" if ping_role else "**AwwMian is LIVE!**"
                        await alert_ch.send(content=ping_text, embed=embed)

                elif not is_live_now and was_live:
                    # Stream ended
                    await db.save_guild_config(guild.id, is_currently_live=0)
                    await self.toggle_streamer_live_role(guild, live_role_id, False)

    # ==========================================
    # 2. YOUTUBE RSS MONITOR (SHORTS VS LONG-FORM)
    # ==========================================
    @tasks.loop(minutes=5)
    async def check_youtube_rss(self):
        await self.bot.wait_until_ready()
        async with aiohttp.ClientSession() as session:
            # Auto-resolve @NotAwwMian's UC... Channel ID if not set in .env
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

                # Check the newest video
                latest = entries[0]
                video_id = latest.find("yt:videoId", ns).text
                title = latest.find("atom:title", ns).text
                published = latest.find("atom:published", ns).text
                link_elem = latest.find("atom:link", ns)
                video_url = link_elem.attrib.get("href", f"https://youtu.be/{video_id}") if link_elem is not None else f"https://youtu.be/{video_id}"

                if await db.is_video_posted(video_id):
                    return

                # Mark as posted
                await db.mark_video_posted(video_id, published)

                # Detect if it's a Short vs Long-Form Video
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

async def setup(bot: commands.Bot):
    await bot.add_cog(AlertsCog(bot))