import time
import random
import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands
import database as db

def xp_for_next_level(level: int) -> int:
    """XP needed to advance from `level` to `level + 1` (Level 1 -> 2 takes 100 XP)."""
    lvl = max(1, level)
    return 5 * ((lvl - 1) ** 2) + 50 * (lvl - 1) + 100

class LevelingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.xp_cooldowns = {}  # (guild_id, user_id): timestamp

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild or not isinstance(message.author, discord.Member):
            return
        # Ignore super short 1-character spam for coin/XP farming
        if len(message.content.strip()) < 3:
            return

        now = time.time()
        key = (message.guild.id, message.author.id)
        if now - self.xp_cooldowns.get(key, 0) < 55.0:
            return
        self.xp_cooldowns[key] = now

        # Check if user has an active XP Booster from /shop!
        mult, _ = await db.get_active_xp_multiplier(message.guild.id, message.author.id)
        base_xp = random.randint(15, 25)
        gained_xp = int(base_xp * mult)

        # Award MianCoins for active chatting (main way to grind economy!)
        chat_coins = int(random.randint(3, 8) * mult)
        await db.update_balance(message.guild.id, message.author.id, chat_coins)

        async with aiosqlite.connect(db.DB_PATH) as conn:
            async with conn.execute(
                "SELECT xp, level FROM user_xp WHERE guild_id = ? AND user_id = ?",
                (message.guild.id, message.author.id)
            ) as cur:
                row = await cur.fetchone()

            if not row:
                current_xp, current_lvl = gained_xp, 1
                await conn.execute(
                    "INSERT INTO user_xp (guild_id, user_id, xp, level) VALUES (?, ?, ?, ?)",
                    (message.guild.id, message.author.id, current_xp, current_lvl)
                )
            else:
                current_xp = row[0] + gained_xp
                current_lvl = max(1, row[1])

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
            # Bonus coin reward on Level Up!
            lvl_bonus = current_lvl * 35
            await db.update_balance(message.guild.id, message.author.id, lvl_bonus)

            cfg = await db.get_guild_config(message.guild.id)
            reward_text = f"\n🌸 **Level-Up Bonus:** `+{lvl_bonus} MianCoins`"
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
                                reward_text += f"\n🎁 **Milestone Role Unlocked:** {role.mention}!"
                            except Exception:
                                pass

            embed = discord.Embed(
                title="🎉 LEVEL UP!",
                description=f"GG {message.author.mention}! You advanced to **Level {current_lvl}**!{reward_text}",
                color=discord.Color.from_rgb(219, 70, 145)
            )
            await message.channel.send(embed=embed)

    @app_commands.command(name="rank", description="Check your or another member's server Level, XP progress bar & Active Boosters")
    async def rank_cmd(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        async with aiosqlite.connect(db.DB_PATH) as conn:
            async with conn.execute(
                "SELECT xp, level FROM user_xp WHERE guild_id = ? AND user_id = ?",
                (interaction.guild.id, target.id)
            ) as cur:
                row = await cur.fetchone()

            xp, level = (row[0], max(1, row[1])) if row else (0, 1)

            async with conn.execute(
                "SELECT user_id FROM user_xp WHERE guild_id = ? ORDER BY level DESC, xp DESC",
                (interaction.guild.id,)
            ) as cur:
                all_users = [r[0] for r in await cur.fetchall()]

        rank_pos = all_users.index(target.id) + 1 if target.id in all_users else len(all_users) + 1
        needed = xp_for_next_level(level)
        pct = min(100, int((xp / needed) * 100))
        filled = int((pct / 100) * 12)
        bar = "🟪" * filled + "⬛" * (12 - filled)

        mult, rem_sec = await db.get_active_xp_multiplier(interaction.guild.id, target.id)
        boost_str = f"⚡ **{mult}x Active** (`{rem_sec // 60}m` left)" if rem_sec > 0 else "None (`1.0x`)"

        embed = discord.Embed(
            title=f"🏆 Server Rank — {target.display_name}",
            color=discord.Color.purple()
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="🥇 Rank", value=f"**#{rank_pos}**", inline=True)
        embed.add_field(name="⭐ Level", value=f"**Level {level}**", inline=True)
        embed.add_field(name="✨ XP", value=f"`{xp:,} / {needed:,} XP`", inline=True)
        embed.add_field(name="🚀 XP Booster", value=boost_str, inline=False)
        embed.add_field(name=f"Progress to Level {level + 1}", value=f"{bar} **{pct}%**", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="View the Top 10 most active members in AwwMian's server")
    async def leaderboard_cmd(self, interaction: discord.Interaction):
        async with aiosqlite.connect(db.DB_PATH) as conn:
            await conn.execute("UPDATE user_xp SET level = 1 WHERE level < 1")
            await conn.commit()
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
            lvl = max(1, lvl)
            needed = xp_for_next_level(lvl)
            pct = min(100, int((xp / needed) * 100))
            badge = medals[idx] if idx < 3 else f"`#{idx+1}`"
            lines.append(f"{badge} <@{uid}> — **Level {lvl}** • `{xp:,}/{needed:,} XP` (**{pct}%**)")

        embed = discord.Embed(
            title=f"👑 {interaction.guild.name} — Top 10 XP Leaderboard",
            description="\n".join(lines),
            color=discord.Color.gold()
        )
        embed.set_footer(text="Chat actively to earn XP & 🌸 MianCoins! Buy 2x XP Boosters in /shop")
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(LevelingCog(bot))