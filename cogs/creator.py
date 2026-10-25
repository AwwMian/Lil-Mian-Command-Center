import discord
from discord import app_commands
from discord.ext import commands
import core_engine as engine
import database as db
from cogs.roles import (
    deploy_all_role_panels,
    COLOR_ROLES,
    IDENTITY_ROLES,
    GAME_ROLES
)
from cogs.security import VerificationView

AWWMIAN_USER_ID = 1156965426044080188

def is_awwmian_or_admin():
    """Strictly restricts command execution to @awwmian (1156965426044080188) or Admin role holders."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.id == AWWMIAN_USER_ID:
            return True
        if interaction.guild and isinstance(interaction.user, discord.Member):
            if interaction.user.id == interaction.guild.owner_id:
                return True
            if interaction.user.guild_permissions.administrator:
                return True
            if any(r.name.lower() in ("admin", "administrator") for r in interaction.user.roles):
                return True

        await interaction.response.send_message(
            "⛔ **Access Denied:** This command is strictly locked to **@awwmian** (`1156965426044080188`) and Server **Admins**.",
            ephemeral=True
        )
        return False
    return app_commands.check(predicate)


class CreatorCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="server_setup", description="[ADMIN/AWWMIAN ONLY] Auto-build Verification Gate, Memes, Clips, Feedback & Self-Roles!")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    @is_awwmian_or_admin()
    async def server_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if not guild:
            return

        async def get_or_create_role(name: str, color: discord.Color, hoist: bool = False) -> discord.Role:
            role = discord.utils.get(guild.roles, name=name)
            if not role:
                role = await guild.create_role(name=name, color=color, hoist=hoist, reason="Lil Mian /server_setup")
            return role

        # 1. Core Roles (Including @✅ Verified)
        verified_role = await get_or_create_role("✅ Verified", discord.Color.from_rgb(46, 204, 113), hoist=False)
        live_role = await get_or_create_role("🟣 LIVE NOW", discord.Color.purple(), hoist=True)
        stream_ping = await get_or_create_role("🔴 Stream Ping", discord.Color.from_rgb(230, 57, 70))
        yt_ping = await get_or_create_role("📺 YouTube Ping", discord.Color.from_rgb(214, 40, 40))
        shorts_ping = await get_or_create_role("📱 Shorts Ping", discord.Color.from_rgb(247, 127, 0))

        lvl5_role = await get_or_create_role("⭐ Level 5 (Newcomer)", discord.Color.teal())
        lvl10_role = await get_or_create_role("🌟 Level 10 (Regular)", discord.Color.blue())
        lvl25_role = await get_or_create_role("💎 Level 25 (Veteran)", discord.Color.gold(), hoist=True)
        lvl50_role = await get_or_create_role("👑 Level 50 (AwwMian Legend)", discord.Color.magenta(), hoist=True)

        for c_name, _, c_color in COLOR_ROLES:
            await get_or_create_role(c_name, c_color)
        for i_name, i_color in IDENTITY_ROLES + GAME_ROLES:
            await get_or_create_role(i_name, i_color)

        # Grant @✅ Verified to all current human members so existing members aren't locked out!
        for member in guild.members:
            if not member.bot and verified_role not in member.roles:
                try:
                    await member.add_roles(verified_role, reason="Initial Verification Setup")
                except Exception:
                    pass

        # 2. Permission Overwrites (Verification Gate Layer)
        # Unverified (@everyone) can see #rules, #verify, #joins
        verify_gate_overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            verified_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True)
        }
        # Read-only for Verified members (Announcements, Self-Roles, Alerts)
        verified_readonly_overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            verified_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True)
        }
        # Interactive Community Channels for Verified members (#memes, #clips, #lil-mian-feedback)
        verified_chat_overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            verified_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True)
        }

        cat_welcome = discord.utils.get(guild.categories, name="📌 WELCOME & INFO")
        if not cat_welcome:
            cat_welcome = await guild.create_category("📌 WELCOME & INFO", position=0)

        cat_hub = discord.utils.get(guild.categories, name="📡 AWWMIAN MEDIA HUB")
        if not cat_hub:
            cat_hub = await guild.create_category("📡 AWWMIAN MEDIA HUB")

        cat_comm = discord.utils.get(guild.categories, name="🎮 COMMUNITY & FUN")
        if not cat_comm:
            cat_comm = await guild.create_category("🎮 COMMUNITY & FUN")

        cat_sec = discord.utils.get(guild.categories, name="🛡️ STAFF & SECURITY")
        if not cat_sec:
            sec_overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            cat_sec = await guild.create_category("🛡️ STAFF & SECURITY", overwrites=sec_overwrites)

        async def get_or_create_channel(name: str, category: discord.CategoryChannel, overwrites=None) -> tuple[discord.TextChannel, bool]:
            ch = discord.utils.get(guild.text_channels, name=name)
            created = False
            if not ch:
                ch = await guild.create_text_channel(name=name, category=category, overwrites=overwrites or {})
                created = True
            else:
                if overwrites:
                    await ch.edit(overwrites=overwrites)
            return ch, created

        # Welcome & Verification Channels
        ch_verify, _ = await get_or_create_channel("✅・verify", cat_welcome, verify_gate_overwrites)
        ch_rules, rules_new = await get_or_create_channel("📜・rules", cat_welcome, verify_gate_overwrites)
        ch_ann, _ = await get_or_create_channel("📢・announcements", cat_welcome, verified_readonly_overwrites)
        ch_roles, _ = await get_or_create_channel("🎭・self-roles", cat_welcome, verified_readonly_overwrites)
        ch_joins, _ = await get_or_create_channel("👋・joins", cat_welcome, verify_gate_overwrites)
        ch_leaves, _ = await get_or_create_channel("💔・leaves", cat_welcome, verified_readonly_overwrites)

        # Media Hub Channels
        ch_twitch, _ = await get_or_create_channel("🔔・live-alerts", cat_hub, verified_readonly_overwrites)
        ch_yt, _ = await get_or_create_channel("📺・youtube-uploads", cat_hub, verified_readonly_overwrites)
        ch_shorts, _ = await get_or_create_channel("📱・shorts-and-reels", cat_hub, verified_readonly_overwrites)

        # Community & Fun Channels (#memes, #clips, #lil-mian-feedback)
        ch_memes, _ = await get_or_create_channel("😂・memes", cat_comm, verified_chat_overwrites)
        ch_clips, _ = await get_or_create_channel("🎬・clips", cat_comm, verified_chat_overwrites)
        ch_feedback, _ = await get_or_create_channel("💡・lil-mian-feedback", cat_comm, verified_chat_overwrites)

        # Staff Security Channel
        ch_modlogs, _ = await get_or_create_channel("🛡️・mod-logs", cat_sec)

        await db.save_guild_config(
            guild.id,
            twitch_channel_id=ch_twitch.id,
            yt_channel_id=ch_yt.id,
            shorts_channel_id=ch_shorts.id,
            mod_log_channel_id=ch_modlogs.id,
            roles_channel_id=ch_roles.id,
            rules_channel_id=ch_rules.id,
            announcements_channel_id=ch_ann.id,
            joins_channel_id=ch_joins.id,
            leaves_channel_id=ch_leaves.id,
            verify_channel_id=ch_verify.id,
            feedback_channel_id=ch_feedback.id,
            memes_channel_id=ch_memes.id,
            clips_channel_id=ch_clips.id,
            verified_role_id=verified_role.id,
            stream_ping_role_id=stream_ping.id,
            yt_ping_role_id=yt_ping.id,
            shorts_ping_role_id=shorts_ping.id,
            live_streamer_role_id=live_role.id,
            lvl5_role_id=lvl5_role.id,
            lvl10_role_id=lvl10_role.id,
            lvl25_role_id=lvl25_role.id,
            lvl50_role_id=lvl50_role.id
        )

        # 3. Deploy Human Verification Card in #✅・verify
        try:
            await ch_verify.purge(limit=10, check=lambda m: m.author == self.bot.user)
        except Exception:
            pass
        verify_embed = discord.Embed(
            title=f"🛡️ {guild.name} — Security Verification Gate",
            description=(
                "Welcome! To protect **AwwMian's Server** against automated bots and raids, please verify that you are human.\n\n"
                "👉 **Click the green `✅ Verify Me (Human Check)` button below** to instantly unlock:\n"
                f"• {ch_roles.mention} (Claim your VALORANT Agent, Pronouns & Color Roles)\n"
                f"• {ch_memes.mention} & {ch_clips.mention} (Post VALORANT/osu! clips & Dank Memes)\n"
                f"• {ch_feedback.mention} (Suggest new bot features & stream ideas)"
            ),
            color=discord.Color.from_rgb(46, 204, 113)
        )
        verify_embed.set_image(url="https://media1.tenor.com/m/ce9I2j28pI4AAAAd/anime-wave.gif")
        await ch_verify.send(embed=verify_embed, view=VerificationView())

        # 4. Auto-post Rules Embed in #📜・rules
        if rules_new or ch_rules.last_message_id is None:
            rules_embed = discord.Embed(
                title=f"📜 {guild.name} — Official Server Rules",
                description=(
                    "Welcome to **AwwMian's Official Discord**! Keep the vibes chill and follow these rules:\n\n"
                    "**1. Verify First** ✅\n"
                    f"Click the button in {ch_verify.mention} to unlock the server.\n\n"
                    "**2. Be Respectful & Chill** 🤝\n"
                    "No harassment, hate speech, slurs, or toxicity.\n\n"
                    "**3. No Spam, Raids or Unauthorized Invites** 🚨\n"
                    "Lil Mian's Anti-Raid & Auto-Mod will automatically timeout spammers and delete invite links.\n\n"
                    "**4. Keep Content Safe (Strict SFW)** 🛡️\n"
                    "We have both `🔞 Adult` and `🌱 Minor` members. Keep all channels strictly SFW.\n\n"
                    "**5. Grab Your Roles!** 🎭\n"
                    f"Head over to {ch_roles.mention} to equip your **Pronouns, Name Color, VALORANT Main Agent, and Stream Pings**!"
                ),
                color=discord.Color.from_rgb(219, 70, 145)
            )
            rules_embed.set_image(url="https://media1.tenor.com/m/wU6C2-kK2vUAAAAd/marin-kitagawa-anime-wave.gif")
            await ch_rules.send(embed=rules_embed)

        # 5. Deploy Self-Roles Panels
        try:
            await ch_roles.purge(limit=10, check=lambda m: m.author == self.bot.user)
        except Exception:
            pass
        await deploy_all_role_panels(ch_roles)

        await interaction.followup.send(
            f"✅ **Version 4.0 Server Setup Complete!**\n"
            f"• **Security Gate:** {ch_verify.mention} (Grants {verified_role.mention})\n"
            f"• **New Community Hub:** {ch_memes.mention}, {ch_clips.mention}, {ch_feedback.mention}\n"
            f"• **New Commands Ready:** `/game_stats`, `/memes`, `/emote`, `/shop`, `/buy`, `/hunt`, `/crime`, `/slots`, `/trivia`, `/feedback`!",
            ephemeral=True
        )

    @app_commands.command(name="keywords", description="[ADMIN/AWWMIAN ONLY] Live VALORANT & osu! viral trends + SNS keywords")
    @app_commands.default_permissions(administrator=True)
    @is_awwmian_or_admin()
    async def keywords_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        trends = engine.get_sns_trends_and_keywords()
        embed = discord.Embed(
            title="🔥 VALORANT & osu! Viral Trends + Keywords",
            description="Private Creator Intelligence for @awwmian:",
            color=discord.Color.red()
        )
        for platform, data in trends.items():
            if platform == "Live Web & Gaming Surges":
                embed.add_field(name="🌐 Live Search Surges (Japan / Global)", value=", ".join(data), inline=False)
            else:
                topics = "\n• ".join(data["viral_topics"])
                kws = "`" + "`, `".join(data["keywords"]) + "`"
                embed.add_field(name=f"📌 {platform}", value=f"**Trending Now:**\n• {topics}\n**Tags:** {kws}", inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="ideas", description="[ADMIN/AWWMIAN ONLY] Generate AI VALORANT/osu! video ideas & 14-day predictions")
    @app_commands.describe(focus="Specific agent, weapon, osu! beatmap, or challenge idea")
    @app_commands.default_permissions(administrator=True)
    @is_awwmian_or_admin()
    async def ideas_cmd(self, interaction: discord.Interaction, focus: str = "VALORANT Ranked & osu! Handcam Clips"):
        await interaction.response.defer(ephemeral=True)
        report = engine.generate_ideas_and_predictions(focus)
        embed = discord.Embed(
            title=f"🧠 Lil Mian AI Strategist ({focus})",
            description=report[:4000],
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="clip_idea", description="[ADMIN/AWWMIAN ONLY] Save a video/stream idea from phone/MacBook to Windows PC")
    @app_commands.describe(idea="Type your video idea, hook, or clip timestamp note")
    @app_commands.default_permissions(administrator=True)
    @is_awwmian_or_admin()
    async def clip_idea_cmd(self, interaction: discord.Interaction, idea: str):
        engine.save_clip_idea(idea, source=f"Discord ({interaction.user.name})")
        await interaction.response.send_message(f"💾 **Saved to Windows PC Vault!**\n> *{idea}*", ephemeral=True)

    @app_commands.command(name="start_stream_prep", description="[ADMIN/AWWMIAN ONLY] Remotely launch Twitch Manager, YT Studio & OBS on Windows PC!")
    @app_commands.default_permissions(administrator=True)
    @is_awwmian_or_admin()
    async def stream_prep_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        launched = engine.trigger_windows_stream_prep()
        items = "\n• ".join(launched)
        await interaction.followup.send(f"🖥️ **Windows PC Stream Prep Triggered!**\nLaunched on host PC:\n• {items}", ephemeral=True)

    @app_commands.command(name="stats", description="Live telemetry for Twitch.tv/AwwMian, @NotAwwMian & @awwmianlive (JST)")
    async def stats_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer()
        stats = engine.get_social_stats()
        sched = engine.get_next_stream_info()
        embed = discord.Embed(
            title="📊 Live Creator Telemetry — AwwMian",
            url="https://twitch.tv/AwwMian",
            color=discord.Color.purple()
        )
        embed.add_field(name="🟣 Twitch Status", value=f"**{stats['twitch_status']}**", inline=True)
        embed.add_field(name="👥 Twitch Followers", value=f"{stats['twitch_followers']:,}", inline=True)
        embed.add_field(name="🎮 Category / Viewers", value=f"{stats['twitch_game']} ({stats['twitch_viewers']} watching)", inline=True)
        embed.add_field(name="🔴 YouTube (@NotAwwMian)", value=f"**{stats['yt_subscribers']:,}** Subs\n`{stats['yt_total_views']:,}` Views ({stats['yt_video_count']} vids)", inline=True)
        embed.add_field(name="📸 Instagram", value=f"[**{stats['ig_handle']}**](https://instagram.com/awwmianlive)", inline=True)
        embed.add_field(name="⏰ Next Broadcast (JST)", value=f"**{sched['label']}**\n📅 `{sched['next_date']}`\n⏳ **{sched['countdown']}**", inline=False)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="schedule", description="Countdown to next Twitch.tv/AwwMian stream in Japan Time (JST / GMT+9)")
    async def schedule_cmd(self, interaction: discord.Interaction):
        sched = engine.get_next_stream_info()
        await interaction.response.send_message(
            f"🎥 **Next Stream for Twitch.tv/AwwMian (JST / GMT+9):**\n"
            f"> **{sched['label']}**\n"
            f"> 📅 Date: `{sched['next_date']}`\n"
            f"> ⏳ Countdown: **{sched['countdown']}**"
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(CreatorCog(bot))