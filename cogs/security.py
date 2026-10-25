import re
import time
import datetime
from collections import defaultdict, deque
import discord
from discord import app_commands
from discord.ext import commands
import database as db

INVITE_REGEX = re.compile(r"(discord\.gg/|discordapp\.com/invite/|discord\.com/invite/)[a-zA-Z0-9]+", re.IGNORECASE)

# ==========================================
# PERSISTENT HUMAN VERIFICATION BUTTON VIEW
# ==========================================
class VerificationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Verify Me (Human Check)", emoji="✅", style=discord.ButtonStyle.success, custom_id="persistent:verify_human")
    async def verify_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.defer(ephemeral=True)

        cfg = await db.get_guild_config(interaction.guild.id)
        role = None
        if cfg and cfg.get("verified_role_id"):
            role = interaction.guild.get_role(cfg["verified_role_id"])
        if not role:
            role = discord.utils.get(interaction.guild.roles, name="✅ Verified")
        if not role:
            role = await interaction.guild.create_role(
                name="✅ Verified",
                color=discord.Color.from_rgb(46, 204, 113),
                reason="Lil Mian Verification Gate"
            )

        if role in interaction.user.roles:
            await interaction.followup.send("✅ You are already verified and have full server access!", ephemeral=True)
            return

        # Account Age Security Check (Warn in mod-logs if account is < 1 day old)
        account_age_hours = (datetime.datetime.now(datetime.timezone.utc) - interaction.user.created_at).total_seconds() / 3600
        await interaction.user.add_roles(role, reason="Passed Human Button Verification")

        roles_ch_id = cfg.get("roles_channel_id") if cfg else None
        roles_mention = f"<#{roles_ch_id}>" if roles_ch_id else "`#🎭・self-roles`"

        await interaction.followup.send(
            f"🎉 **Verification Complete!** You now have full access to **{interaction.guild.name}**!\n"
            f"👉 Head over to {roles_mention} to claim your **VALORANT Main Agent, Pronouns & Color Roles**!",
            ephemeral=True
        )

        if account_age_hours < 24 and cfg and cfg.get("mod_log_channel_id"):
            log_ch = interaction.guild.get_channel(cfg["mod_log_channel_id"])
            if log_ch:
                embed = discord.Embed(
                    title="⚠️ New Alt/Fresh Account Verified",
                    description=f"**Member:** {interaction.user.mention} (`{interaction.user.id}`)\n**Account Age:** `{account_age_hours:.1f} hours old`",
                    color=discord.Color.gold()
                )
                await log_ch.send(embed=embed)


class SecurityCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.msg_buckets = defaultdict(lambda: deque(maxlen=10))
        self.admin_nuke_tracker = defaultdict(lambda: deque(maxlen=10))
        self.join_raid_tracker = defaultdict(lambda: deque(maxlen=15))

    async def send_mod_log(self, guild: discord.Guild, embed: discord.Embed):
        cfg = await db.get_guild_config(guild.id)
        if cfg and cfg.get("mod_log_channel_id"):
            ch = guild.get_channel(cfg["mod_log_channel_id"])
            if ch:
                try:
                    await ch.send(embed=embed)
                except Exception:
                    pass

    # ==========================================
    # 1. ANTI-RAID JOIN VELOCITY DETECTOR
    # ==========================================
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        now = time.time()
        tracker = self.join_raid_tracker[member.guild.id]
        tracker.append(now)

        # If 5+ accounts join within 10 seconds -> Raid Alert + Timeout suspicious new joins
        recent_joins = [t for t in tracker if now - t <= 10.0]
        if len(recent_joins) >= 5:
            try:
                await member.timeout(datetime.timedelta(minutes=30), reason="Lil Mian Anti-Raid Shield: Mass Join Detected")
            except Exception:
                pass
            embed = discord.Embed(
                title="🚨 ANTI-RAID SHIELD ACTIVATED!",
                description=(
                    f"Detected **{len(recent_joins)} joins in under 10 seconds**!\n"
                    f"Latest Join: {member.mention} (`{member.id}`) — Auto-applied 30m quarantine timeout."
                ),
                color=discord.Color.dark_red(),
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            await self.send_mod_log(member.guild, embed)

    # ==========================================
    # 2. ANTI-SPAM, ANTI-INVITE & AUTO-CLIP REACTIONS
    # ==========================================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild or not isinstance(message.author, discord.Member):
            return

        # Auto-hype clips posted in #clips!
        if "clips" in message.channel.name.lower() and (message.attachments or "http" in message.content.lower()):
            try:
                await message.add_reaction("🔥")
                await message.add_reaction("💀")
            except Exception:
                pass

        # Exempt @awwmian & server admins from moderation filters
        if (
            message.author.id in (1156965426044080188, message.guild.owner_id)
            or message.author.guild_permissions.administrator
        ):
            return

        # Check 1: Anti-Invite Link Filter
        if INVITE_REGEX.search(message.content):
            try:
                await message.delete()
                await message.channel.send(
                    f"🚫 {message.author.mention}, posting external Discord server invites is not allowed!",
                    delete_after=6
                )
            except Exception:
                pass
            embed = discord.Embed(
                title="🔗 Blocked Unauthorized Server Invite",
                description=f"**User:** {message.author.mention} in {message.channel.mention}\n**Content:** `{message.content[:300]}`",
                color=discord.Color.orange()
            )
            await self.send_mod_log(message.guild, embed)
            return

        # Check 2: Velocity Spam (>5 msgs in 3s) & Mass Mentions (>4 mentions)
        now = time.time()
        bucket = self.msg_buckets[(message.guild.id, message.author.id)]
        bucket.append(now)

        recent_5 = [t for t in bucket if now - t <= 3.0]
        is_vel_spam = len(recent_5) > 5
        total_mentions = len(message.mentions) + len(message.role_mentions)
        is_mention_spam = total_mentions > 4

        if is_vel_spam or is_mention_spam:
            reason = "Message Velocity Spam (>5 msgs/3s)" if is_vel_spam else f"Mass Mention Spam ({total_mentions} mentions)"
            try:
                await message.channel.purge(limit=6, check=lambda m: m.author.id == message.author.id)
                await message.author.timeout(datetime.timedelta(minutes=10), reason=f"Lil Mian Auto-Mod: {reason}")
            except Exception:
                pass

            embed = discord.Embed(
                title="🚨 Auto-Mod Gatekeeper Triggered",
                description=f"**Offender:** {message.author.mention} (`{message.author.id}`)\n**Action:** 10-Minute Timeout & Message Purge\n**Reason:** {reason}",
                color=discord.Color.red(),
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            await self.send_mod_log(message.guild, embed)

    # ==========================================
    # 3. ANTI-NUKE PROTECTION
    # ==========================================
    async def check_anti_nuke(self, guild: discord.Guild, action_type: discord.AuditLogAction, threshold: int):
        try:
            async for entry in guild.audit_logs(limit=1, action=action_type):
                perp = entry.user
                if not perp or perp.id in (self.bot.user.id, guild.owner_id, 1156965426044080188):
                    return
                now = time.time()
                tracker = self.admin_nuke_tracker[(guild.id, perp.id)]
                tracker.append(now)
                recent = [t for t in tracker if now - t <= 10.0]

                if len(recent) > threshold and isinstance(perp, discord.Member):
                    safe_roles = [
                        r for r in perp.roles
                        if not (r.permissions.administrator or r.permissions.ban_members or r.permissions.manage_channels)
                    ]
                    await perp.edit(roles=safe_roles, reason="Lil Mian Anti-Nuke: Exceeded destructive rate limit!")
                    embed = discord.Embed(
                        title="🛑 ANTI-NUKE TRIGGERED: Staff Stripped!",
                        description=(
                            f"**Staff Member:** {perp.mention} (`{perp.id}`)\n"
                            f"**Violation:** Performed >{threshold} `{action_type.name}` actions in under 10 seconds.\n"
                            f"**Action Taken:** Stripped all administrative/moderation roles immediately!"
                        ),
                        color=discord.Color.dark_red(),
                        timestamp=datetime.datetime.now(datetime.timezone.utc)
                    )
                    await self.send_mod_log(guild, embed)
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        await self.check_anti_nuke(channel.guild, discord.AuditLogAction.channel_delete, threshold=2)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        await self.check_anti_nuke(guild, discord.AuditLogAction.ban, threshold=3)
        embed = discord.Embed(
            title="🔨 Member Banned",
            description=f"**User:** {user.mention} (`{user.id}`)",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        await self.send_mod_log(guild, embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        embed = discord.Embed(
            title="🗑️ Message Deleted",
            description=f"**Author:** {message.author.mention} in {message.channel.mention}\n**Content:**\n{message.content or '*[Attachment/Embed]*'}",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        await self.send_mod_log(message.guild, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild or before.content == after.content:
            return
        embed = discord.Embed(
            title="✏️ Message Edited",
            description=f"**Author:** {before.author.mention} in {before.channel.mention}",
            color=discord.Color.yellow(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="Before", value=(before.content or "*Empty*")[:1024], inline=False)
        embed.add_field(name="After", value=(after.content or "*Empty*")[:1024], inline=False)
        await self.send_mod_log(before.guild, embed)

    # ==========================================
    # 4. STAFF SLASH COMMANDS
    # ==========================================
    @app_commands.command(name="clear_chat", description="[Staff] Nuke the channel clean (0 = Clone & Wipe Entire History, or 1-500 messages)")
    @app_commands.describe(amount="Enter 0 to completely nuke/reset the entire channel, or a number (e.g. 100) to purge recent messages")
    @app_commands.default_permissions(manage_channels=True)
    async def clear_chat_cmd(self, interaction: discord.Interaction, amount: int = 0):
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return

        if amount <= 0:
            pos = channel.position
            new_ch = await channel.clone(reason=f"Channel Nuked by {interaction.user}")
            await new_ch.edit(position=pos)
            await channel.delete(reason=f"Channel Nuked by {interaction.user}")

            embed = discord.Embed(
                title="💥 CHANNEL NUKED & WIPED CLEAN",
                description=f"This channel was completely obliterated and reset by {interaction.user.mention}.",
                color=discord.Color.red()
            )
            embed.set_image(url="https://media1.tenor.com/m/n5_r2p0m0e8AAAAd/megumin-explosion.gif")
            await new_ch.send(embed=embed)
        else:
            deleted = await channel.purge(limit=min(amount, 500))
            await interaction.followup.send(f"🧹 Purged **{len(deleted)}** messages from {channel.mention}!", ephemeral=True)

    @app_commands.command(name="timeout", description="[Staff] Timeout a member for a specified duration in minutes")
    @app_commands.default_permissions(moderate_members=True)
    async def timeout_cmd(self, interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason provided"):
        await member.timeout(datetime.timedelta(minutes=minutes), reason=reason)
        embed = discord.Embed(
            title="⏳ Member Timed Out",
            description=f"**Target:** {member.mention}\n**Duration:** {minutes} minutes\n**Moderator:** {interaction.user.mention}\n**Reason:** {reason}",
            color=discord.Color.orange()
        )
        await self.send_mod_log(interaction.guild, embed)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="warn", description="[Staff] Issue a persistent warning to a member")
    @app_commands.default_permissions(moderate_members=True)
    async def warn_cmd(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        count = await db.add_warning(interaction.guild.id, member.id, interaction.user.id, reason)
        embed = discord.Embed(
            title="⚠️ Member Warned",
            description=f"**Target:** {member.mention} (Total Warnings: **{count}**)\n**Moderator:** {interaction.user.mention}\n**Reason:** {reason}",
            color=discord.Color.gold()
        )
        await self.send_mod_log(interaction.guild, embed)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="warnings", description="[Staff] Check a member's warning history")
    @app_commands.default_permissions(moderate_members=True)
    async def warnings_cmd(self, interaction: discord.Interaction, member: discord.Member):
        rows = await db.get_warnings(interaction.guild.id, member.id)
        if not rows:
            await interaction.response.send_message(f"✅ {member.mention} has a clean record (0 warnings).", ephemeral=True)
            return
        lines = [f"`#{wid}` • By <@{mod_id}>: **{reason}** ({ts})" for wid, mod_id, reason, ts in rows[:10]]
        embed = discord.Embed(
            title=f"📋 Warning History for {member.display_name}",
            description="\n".join(lines),
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="kick", description="[Staff] Kick a member from the server")
    @app_commands.default_permissions(kick_members=True)
    async def kick_cmd(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        await member.kick(reason=reason)
        embed = discord.Embed(
            title="👢 Member Kicked",
            description=f"**Target:** {member.mention}\n**Moderator:** {interaction.user.mention}\n**Reason:** {reason}",
            color=discord.Color.red()
        )
        await self.send_mod_log(interaction.guild, embed)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ban", description="[Staff] Ban a member from the server")
    @app_commands.default_permissions(ban_members=True)
    async def ban_cmd(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        await member.ban(reason=reason)
        await interaction.response.send_message(f"🔨 Banned **{member}** (`{reason}`).")

async def setup(bot: commands.Bot):
    await bot.add_cog(SecurityCog(bot))