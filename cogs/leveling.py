import time
import random
import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands
import database as db

def xp_for_next_level(level: int) -> int:
    """Standard Arcane XP curve formula."""
    return 5 * (level ** 2) + (50 * level) + 100

class LevelingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.xp_cooldowns = {}  # (guild_id, user_id): timestamp

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild or not isinstance(message.author, discord.Member):
            return

        now = time.time()
        key = (message.guild.id, message.author.id)
        if now - self.xp_cooldowns.get(key, 0) < 60.0:
            return
        self.xp_cooldowns[key] = now

        gained_xp = random.randint(15, 25)

        async with aiosqlite.connect(db.DB_PATH) as conn:
            async with conn.execute(
                "SELECT xp, level FROM user_xp WHERE guild_id = ? AND user_id = ?",
                (message.guild.id, message.author.id)
            ) as cur:
                row = await cur.fetchone()

            if not row:
                current_xp, current_lvl = gained_xp, 0
                await conn.execute(
                    "INSERT INTO user_xp (guild_id, user_id, xp, level) VALUES (?, ?, ?, ?)",
                    (message.guild.id, message.author.id, current_xp, current_lvl)
                )
            else:
                current_xp, current_lvl = row[0] + gained_xp, row[1]

            needed = xp_for_next_level(current_lvl)
            leveled_up = False
            while current_xp >= needed:
                current_xp -= needed
                current_lvl += 1
                leveled_up = True
                needed = xp_for_next_level(current_lvl)

            await conn.execute(
                "UPDATE user_xp SET xp = ?, level = ? WHERE guild_id = ? AND user_id = ?",
                (current_xp, current_lvl, message.guild.id, message.author.id)
            )
            await conn.commit()

        if leveled_up:
            # Check Milestone Role Rewards (Levels 5, 10, 25, 50)
            cfg = await db.get_guild_config(message.guild.id)
            reward_text = ""
            if cfg:
                milestone_map = {
                    5: cfg.get("lvl5_role_id"),
                    10: cfg.get("lvl10_role_id"),
                    25: cfg.get("lvl25_role_id"),
                    50: cfg.get("lvl50_role_id")
                }
                for req_lvl, r_id in milestone_map.items():
                    if current_lvl >= req_lvl and r_id:
                        role = message.guild.get_role(r_id)
                        if role and role not in message.author.roles:
                            try:
                                await message.author.add_roles(role, reason=f"Reached Level {current_lvl}")
                                reward_text = f"\n🎁 **Milestone Unlocked:** {role.mention}!"
                            except Exception:
                                pass

            embed = discord.Embed(
                title="🎉 Level Up!",
                description=f"GG {message.author.mention}! You just advanced to **Level {current_lvl}**!{reward_text}",
                color=discord.Color.purple()
            )
            await message.channel.send(embed=embed)

    @app_commands.command(name="rank", description="Check your or another member's server Level, XP progress bar & Rank")
    async def rank_cmd(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        async with aiosqlite.connect(db.DB_PATH) as conn:
            async with conn.execute(
                "SELECT xp, level FROM user_xp WHERE guild_id = ? AND user_id = ?",
                (interaction.guild.id, target.id)
            ) as cur:
                row = await cur.fetchone()

            xp, level = (row[0], row[1]) if row else (0, 0)

            async with conn.execute(
                "SELECT user_id FROM user_xp WHERE guild_id = ? ORDER BY level DESC, xp DESC",
                (interaction.guild.id,)
            ) as cur:
                all_users = [r[0] for r in await cur.fetchall()]

        rank_pos = all_users.index(target.id) + 1 if target.id in all_users else len(all_users) + 1
        needed = xp_for_next_level(level)
        filled = int((xp / needed) * 12)
        bar = "🟪" * filled + "⬛" * (12 - filled)

        embed = discord.Embed(
            title=f"🏆 Server Rank — {target.display_name}",
            color=discord.Color.purple()
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="🥇 Rank", value=f"**#{rank_pos}**", inline=True)
        embed.add_field(name="⭐ Level", value=f"**{level}**", inline=True)
        embed.add_field(name="✨ XP", value=f"`{xp:,} / {needed:,} XP`", inline=True)
        embed.add_field(name="Progress to Next Level", value=f"{bar} ({int((xp/needed)*100)}%)", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="View the Top 10 most active members in AwwMian's server")
    async def leaderboard_cmd(self, interaction: discord.Interaction):
        async with aiosqlite.connect(db.DB_PATH) as conn:
            async with conn.execute(
                "SELECT user_id, level, xp FROM user_xp WHERE guild_id = ? ORDER BY level DESC, xp DESC LIMIT 10",
                (interaction.guild.id,)
            ) as cur:
                rows = await cur.fetchall()

        if not rows:
            await interaction.response.send_message("No XP recorded yet! Start chatting to climb the leaderboard.")
            return

        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for idx, (uid, lvl, xp) in enumerate(rows):
            badge = medals[idx] if idx < 3 else f"`#{idx+1}`"
            lines.append(f"{badge} <@{uid}> — **Level {lvl}** (`{xp:,} XP`)")

        embed = discord.Embed(
            title=f"👑 {interaction.guild.name} — Top 10 Leaderboard",
            description="\n".join(lines),
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(LevelingCog(bot))