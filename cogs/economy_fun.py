import random
import aiohttp
import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands
import database as db

# ==========================================
# EXPANDED SHOP: BOOSTERS, ITEMS & PRESTIGE ROLES
# ==========================================
SHOP_ITEMS = {
    # XP Boosters
    "boost_1h": ("⚡ 2x XP & Coin Booster (1 Hour)", 250, "booster_1h", "Doubles all chat XP & MianCoins for 1 Hour!"),
    "boost_5h": ("🔥 2x XP & Coin Booster (5 Hours)", 900, "booster_5h", "Doubles all chat XP & MianCoins for 5 Hours!"),
    "boost_24h": ("🌟 2x XP & Coin Booster (24 Hours)", 2200, "booster_24h", "Doubles all chat XP & MianCoins for a full Day!"),
    # Utility & Defense Items
    "padlock": ("🔒 Heavy Padlock (Anti-Rob Shield)", 400, "item_padlock", "Protects your wallet from 1 /rob attempt & fines the thief!"),
    "bank_note": ("🏦 Bank Expansion Note (+2,500 Cap)", 600, "item_bank", "Permanently increases your safe Bank storage by +2,500 Coins!"),
    "lootbox": ("🎲 Mystery Lootbox", 500, "item_lootbox", "Open for a chance at 100 to 2,000 MianCoins or a free Padlock!"),
    "nick_pass": ("🏷️ Custom Nickname Pass", 1500, "item_nick", "Unlocks permission to change your server nickname!"),
    # High-Prestige Roles (Hardcore Grind!)
    "vip": ("🌸 Mian VIP", 15000, discord.Color.from_rgb(255, 105, 180), "Prestige Role: Exclusive Pink VIP status in the server!"),
    "rich": ("💸 Rich Aim God", 40000, discord.Color.from_rgb(255, 215, 0), "Prestige Role: Flex serious wealth on the server!"),
    "king": ("👑 Economy Legend", 100000, discord.Color.from_rgb(138, 43, 226), "Mythic Role: Only the top 1% grinders will ever own this!")
}

ANIME_EMOTES = [
    ("🤗 Hug", "hug", "gave a warm hug to"),
    ("👋 Headpat", "pat", "gently headpatted"),
    ("🤚 Slap", "slap", "slapped the whiff out of"),
    ("💋 Kiss", "kiss", "gave a sweet kiss to"),
    ("👉 Poke", "poke", "poked"),
    ("🦷 Bite", "bite", "playfully bit"),
    ("😭 Cry", "cry", "started crying on"),
    ("💃 Dance", "dance", "started dancing with"),
    ("😏 Smug", "smug", "gave a smug look to"),
    ("🔨 Bonk", "bonk", "bonked"),
    ("🙌 Highfive", "highfive", "high-fived"),
    ("👋 Wave", "wave", "waved hello at"),
]

TRIVIA_QUESTIONS = [
    ("What number is the legendary osu! rhythm meme?", ["727", "420", "690", "999"], "727"),
    ("How many credits does an Operator cost in VALORANT?", ["4,700", "4,500", "5,000", "4,200"], "4,700"),
    ("Which VALORANT agent says 'Watch this!' before dashing?", ["Jett", "Reyna", "Neon", "Waylay"], "Jett"),
    ("What does 'FC' stand for in osu!?", ["Full Combo", "Fast Clicks", "First Clear", "Final Circle"], "Full Combo"),
    ("How many seconds does it take to defuse the Spike in VALORANT?", ["7 seconds", "5 seconds", "10 seconds", "6 seconds"], "7 seconds"),
]

def format_cooldown(seconds: int) -> str:
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 and days == 0:
        parts.append(f"{secs}s")
    return " ".join(parts) if parts else "a few seconds"

class TriviaView(discord.ui.View):
    def __init__(self, author_id: int, options: list[str], correct: str):
        super().__init__(timeout=20)
        self.author_id = author_id
        self.correct = correct
        for opt in options:
            btn = discord.ui.Button(label=opt, style=discord.ButtonStyle.secondary)
            btn.callback = self.make_callback(opt)
            self.add_item(btn)

    def make_callback(self, choice: str):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.author_id:
                await interaction.response.send_message("Start your own `/trivia` game!", ephemeral=True)
                return
            for item in self.children:
                item.disabled = True
            if choice == self.correct:
                new_bal = await db.update_balance(interaction.guild.id, interaction.user.id, 35)
                await interaction.response.edit_message(
                    content=f"✅ **CORRECT!** (`{self.correct}`) You won **+35 🌸 MianCoins**! (Wallet: `{new_bal:,}`)",
                    view=self
                )
            else:
                await interaction.response.edit_message(
                    content=f"❌ **Wrong!** You picked `{choice}`, but the answer was **`{self.correct}`**.",
                    view=self
                )
        return callback

class EconomyFunCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ==========================================
    # 1. ANIME EMOTES & GAMING MEMES
    # ==========================================
    @app_commands.command(name="emote", description="Send an animated Anime GIF reaction to a member")
    @app_commands.describe(emotion="Pick an anime emotion/action", target="Who are you doing this to?")
    @app_commands.choices(emotion=[
        app_commands.Choice(name=label, value=f"{endpoint}|{verb}")
        for label, endpoint, verb in ANIME_EMOTES
    ])
    async def emote_cmd(self, interaction: discord.Interaction, emotion: str, target: discord.Member = None):
        await interaction.response.defer()
        endpoint, verb = emotion.split("|", 1)
        target_member = target or interaction.user

        gif_url = "https://media1.tenor.com/m/wU6C2-kK2vUAAAAd/marin-kitagawa-anime-wave.gif"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://nekos.best/api/v2/{endpoint}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        gif_url = data["results"][0]["url"]
        except Exception:
            pass

        if target_member.id == interaction.user.id:
            desc = f"🌸 **{interaction.user.mention}** {verb} themselves!"
        else:
            desc = f"🌸 **{interaction.user.mention}** {verb} **{target_member.mention}**!"

        embed = discord.Embed(description=desc, color=discord.Color.from_rgb(255, 105, 180))
        embed.set_image(url=gif_url)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="memes", description="Fetch a random SFW VALORANT, osu! or gaming meme")
    async def memes_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer()
        subreddits = ["VALORANTMemes", "osugame", "gamingmemes", "animemes"]
        chosen_sub = random.choice(subreddits)

        async with aiohttp.ClientSession() as session:
            url = f"https://meme-api.com/gimme/{chosen_sub}"
            try:
                async with session.get(url, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if not data.get("nsfw", False):
                            embed = discord.Embed(
                                title=data.get("title", "Gaming Meme")[:250],
                                url=data.get("postLink", "https://reddit.com"),
                                color=discord.Color.from_rgb(255, 70, 85)
                            )
                            embed.set_image(url=data.get("url"))
                            embed.set_footer(text=f"👍 {data.get('ups', 0)} upvotes • r/{data.get('subreddit', chosen_sub)}")
                            await interaction.followup.send(embed=embed)
                            return
            except Exception:
                pass
        await interaction.followup.send("⚡ Meme radar is refreshing—run `/memes` again in a second!")

    # ==========================================
    # 2. WALLET, BANK, INVENTORY & TIMED REWARDS
    # ==========================================
    @app_commands.command(name="balance", description="Check your 🌸 MianCoins Wallet, safe Bank balance & active Boosters")
    async def balance_cmd(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        data = await db.ensure_economy_user(interaction.guild.id, target.id)
        mult, rem_sec = await db.get_active_xp_multiplier(interaction.guild.id, target.id)
        boost_txt = f"⚡ `{mult}x Active` ({format_cooldown(rem_sec)} left)" if rem_sec > 0 else "`None (1.0x)`"

        embed = discord.Embed(
            title=f"👛 {target.display_name}'s MianCoin Vault",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="🌸 Wallet (Robbable)", value=f"**`{data['balance']:,}`** Coins", inline=True)
        embed.add_field(name="🏦 Safe Bank", value=f"**`{data['bank']:,} / {data['bank_max']:,}`** Coins", inline=True)
        embed.add_field(name="💎 Net Worth", value=f"**`{data['balance'] + data['bank']:,}`** Coins", inline=True)
        embed.add_field(name="🔒 Active Padlocks", value=f"`{data.get('padlocks', 0)}` Shield(s)", inline=True)
        embed.add_field(name="🚀 XP & Coin Booster", value=boost_txt, inline=True)
        embed.set_footer(text="Tip: Chat actively to earn Coins & XP! Use /deposit to protect coins from /rob.")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="deposit", description="Deposit wallet MianCoins into your safe Bank so nobody can /rob you")
    @app_commands.describe(amount="Amount to deposit (or type 0 to deposit Max)")
    async def deposit_cmd(self, interaction: discord.Interaction, amount: int = 0):
        data = await db.ensure_economy_user(interaction.guild.id, interaction.user.id)
        space = max(0, data["bank_max"] - data["bank"])
        if space <= 0:
            await interaction.response.send_message("🏦 Your Bank is full! Buy a **Bank Expansion Note** in `/shop` to hold more.", ephemeral=True)
            return
        to_dep = min(data["balance"], space) if amount <= 0 else min(amount, data["balance"], space)
        if to_dep <= 0:
            await interaction.response.send_message("❌ You don't have enough wallet coins to deposit!", ephemeral=True)
            return

        async with aiosqlite.connect(db.DB_PATH) as conn:
            await conn.execute(
                "UPDATE economy SET balance = balance - ?, bank = bank + ? WHERE guild_id = ? AND user_id = ?",
                (to_dep, to_dep, interaction.guild.id, interaction.user.id)
            )
            await conn.commit()
        await interaction.response.send_message(f"🏦 Deposited **`{to_dep:,}` 🌸 MianCoins** into your safe Bank!")

    @app_commands.command(name="withdraw", description="Withdraw MianCoins from your Bank back into your Wallet")
    async def withdraw_cmd(self, interaction: discord.Interaction, amount: int):
        data = await db.ensure_economy_user(interaction.guild.id, interaction.user.id)
        to_with = min(max(0, amount), data["bank"])
        if to_with <= 0:
            await interaction.response.send_message("❌ You don't have that many coins in your Bank!", ephemeral=True)
            return
        async with aiosqlite.connect(db.DB_PATH) as conn:
            await conn.execute(
                "UPDATE economy SET balance = balance + ?, bank = bank - ? WHERE guild_id = ? AND user_id = ?",
                (to_with, to_with, interaction.guild.id, interaction.user.id)
            )
            await conn.commit()
        await interaction.response.send_message(f"👛 Withdrew **`{to_with:,}` 🌸 MianCoins** to your Wallet!")

    @app_commands.command(name="daily", description="Claim your daily +50 🌸 MianCoins supply drop (24h cooldown)")
    async def daily_cmd(self, interaction: discord.Interaction):
        ok, val, reward = await db.claim_timed_reward(interaction.guild.id, interaction.user.id, "last_daily", 50, 86400)
        if not ok:
            await interaction.response.send_message(
                f"⏳ **Daily Cooldown!** Come back in **`{format_cooldown(val)}`** (Meanwhile, chat in the server to earn coins!).",
                ephemeral=True
            )
            return
        await interaction.response.send_message(f"🎁 **Daily Supply Drop!** You received **+{reward:,} 🌸 MianCoins**! (Wallet: `{val:,}`)")

    @app_commands.command(name="weekly", description="Claim your weekly +200 🌸 MianCoins bonus (Requires Level 2+ • 7d cooldown)")
    async def weekly_cmd(self, interaction: discord.Interaction):
        lvl = await db.get_user_level(interaction.guild.id, interaction.user.id)
        if lvl < 2:
            await interaction.response.send_message("🔒 **Level Locked!** You must reach **Level 2** by chatting in the server before claiming `/weekly`!", ephemeral=True)
            return
        ok, val, reward = await db.claim_timed_reward(interaction.guild.id, interaction.user.id, "last_weekly", 200, 604800)
        if not ok:
            await interaction.response.send_message(f"⏳ **Weekly Cooldown!** Come back in **`{format_cooldown(val)}`**!", ephemeral=True)
            return
        await interaction.response.send_message(f"💎 **Weekly Bonus Claimed!** You received **+{reward:,} 🌸 MianCoins**! (Wallet: `{val:,}`)")

    @app_commands.command(name="monthly", description="Claim your monthly +750 🌸 MianCoins crate (Requires Level 5+ • 30d cooldown)")
    async def monthly_cmd(self, interaction: discord.Interaction):
        lvl = await db.get_user_level(interaction.guild.id, interaction.user.id)
        if lvl < 5:
            await interaction.response.send_message("🔒 **Level Locked!** You must reach **Level 5** by chatting in the server before claiming `/monthly`!", ephemeral=True)
            return
        ok, val, reward = await db.claim_timed_reward(interaction.guild.id, interaction.user.id, "last_monthly", 750, 2592000)
        if not ok:
            await interaction.response.send_message(f"⏳ **Monthly Cooldown!** Come back in **`{format_cooldown(val)}`**!", ephemeral=True)
            return
        await interaction.response.send_message(f"👑 **Monthly Crate Claimed!** You received **+{reward:,} 🌸 MianCoins**! (Wallet: `{val:,}`)")

    # ==========================================
    # 3. GRIND & PVP COMMANDS (/beg, /hunt, /crime, /rob)
    # ==========================================
    @app_commands.command(name="beg", description="Ask pros for spare change (45s cooldown)")
    @app_commands.checks.cooldown(1, 45.0, key=lambda i: (i.guild_id, i.user.id))
    async def beg_cmd(self, interaction: discord.Interaction):
        donors = ["TenZ", "mrekk", "Cookiezi", "Boaster", "AwwMian", "Kyedae", "Faker"]
        donor = random.choice(donors)
        if random.random() < 0.70:
            reward = random.randint(5, 25)
            new_bal = await db.update_balance(interaction.guild.id, interaction.user.id, reward)
            await interaction.response.send_message(f"🥺 **{donor}** tossed you **+{reward} 🌸 MianCoins**! (Wallet: `{new_bal:,}`)")
        else:
            await interaction.response.send_message(f"💀 **{donor}** told you to go grind DM and walked away. (`+0 coins`)")

    @app_commands.command(name="hunt", description="Hunt for creatures & gun buddies (60s cooldown)")
    @app_commands.checks.cooldown(1, 60.0, key=lambda i: (i.guild_id, i.user.id))
    async def hunt_cmd(self, interaction: discord.Interaction):
        loot = [
            ("🐛 Common Slime", 10),
            ("🦊 Kitsune Spirit", 25),
            ("🦎 Gekko's Wingman", 45),
            ("🐻 Evori Dreamwings", 75),
            ("🐉 Elderflame Dragon (MYTHIC!)", 150)
        ]
        found_name, coins = random.choices(loot, weights=[50, 25, 14, 8, 3], k=1)[0]
        new_bal = await db.update_balance(interaction.guild.id, interaction.user.id, coins)
        await interaction.response.send_message(f"🏹 **Hunt Complete!** You caught a **{found_name}** worth **+{coins} 🌸 MianCoins**! (Wallet: `{new_bal:,}`)")

    @app_commands.command(name="crime", description="High-risk heist! Win 40-100 coins or pay a fine (90s cooldown)")
    @app_commands.checks.cooldown(1, 90.0, key=lambda i: (i.guild_id, i.user.id))
    async def crime_cmd(self, interaction: discord.Interaction):
        crimes = ["hacked Riot Vanguard servers", "borrowed Peppy's private jet", "smuggled Radiant gun buddies", "rigged a VCT bracket"]
        act = random.choice(crimes)
        if random.random() < 0.48:
            win = random.randint(40, 100)
            new_bal = await db.update_balance(interaction.guild.id, interaction.user.id, win)
            await interaction.response.send_message(f"🕵️ **HEIST SUCCESS!** You {act} and escaped with **+{win} 🌸 MianCoins**! (Wallet: `{new_bal:,}`)")
        else:
            loss = random.randint(30, 75)
            new_bal = await db.update_balance(interaction.guild.id, interaction.user.id, -loss)
            await interaction.response.send_message(f"🚓 **BUSTED!** Security caught you trying to {act}! You paid a **-{loss} 🌸 MianCoins** fine. (Wallet: `{new_bal:,}`)")

    @app_commands.command(name="rob", description="Attempt to steal MianCoins from another member's unprotected Wallet! (2m cooldown)")
    @app_commands.checks.cooldown(1, 120.0, key=lambda i: (i.guild_id, i.user.id))
    async def rob_cmd(self, interaction: discord.Interaction, victim: discord.Member):
        if victim.bot or victim.id == interaction.user.id:
            await interaction.response.send_message("❌ You can't rob bots or yourself!", ephemeral=True)
            return

        robber_data = await db.ensure_economy_user(interaction.guild.id, interaction.user.id)
        victim_data = await db.ensure_economy_user(interaction.guild.id, victim.id)

        if robber_data["balance"] < 50:
            await interaction.response.send_message("❌ You need at least **`50 🌸 MianCoins`** in your wallet to attempt a robbery!", ephemeral=True)
            return
        if victim_data["balance"] < 50:
            await interaction.response.send_message(f"💀 {victim.display_name} has less than 50 coins in their wallet—not worth robbing!", ephemeral=True)
            return

        # Check if Victim has an active Padlock from /shop!
        if victim_data.get("padlocks", 0) > 0:
            async with aiosqlite.connect(db.DB_PATH) as conn:
                await conn.execute("UPDATE economy SET padlocks = padlocks - 1 WHERE guild_id = ? AND user_id = ?", (interaction.guild.id, victim.id))
                await conn.commit()
            await db.update_balance(interaction.guild.id, interaction.user.id, -50)
            await db.update_balance(interaction.guild.id, victim.id, 50)
            await interaction.response.send_message(
                f"🔒 **PADLOCK SHATTERED!** {interaction.user.mention} tried to rob {victim.mention}, "
                f"but hit a **Heavy Padlock** and paid a **`50 🌸` fine** directly to {victim.mention}!"
            )
            return

        if random.random() < 0.42:
            stolen = random.randint(15, max(20, int(victim_data["balance"] * 0.30)))
            await db.update_balance(interaction.guild.id, victim.id, -stolen)
            await db.update_balance(interaction.guild.id, interaction.user.id, stolen)
            await interaction.response.send_message(
                f"🥷 **ROBBERY SUCCESS!** {interaction.user.mention} pickpocketed **`{stolen:,}` 🌸 MianCoins** from {victim.mention}'s wallet! "
                f"*(Use `/deposit` or buy a `🔒 Padlock` in `/shop` to protect your coins!)*"
            )
        else:
            fine = 45
            await db.update_balance(interaction.guild.id, interaction.user.id, -fine)
            await db.update_balance(interaction.guild.id, victim.id, fine)
            await interaction.response.send_message(
                f"🚨 **CAUGHT RED-HANDED!** {interaction.user.mention} failed to rob {victim.mention} and paid them **`{fine}` 🌸 MianCoins** in damages!"
            )

    @beg_cmd.error
    @hunt_cmd.error
    @crime_cmd.error
    @rob_cmd.error
    async def action_cooldown_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"⏳ Cooldown active! Wait **`{int(error.retry_after)}s`** before using this again.", ephemeral=True)

    # ==========================================
    # 4. EXPANDED SERVER SHOP (/shop & /buy)
    # ==========================================
    @app_commands.command(name="shop", description="Browse XP Boosters, Padlocks, Bank Notes & Prestige Roles")
    async def shop_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🏪 AwwMian Black Market & Prestige Shop",
            description="Grind coins by **chatting in the server**! Use `/buy` to purchase items, boosters & roles:",
            color=discord.Color.from_rgb(219, 70, 145)
        )
        embed.add_field(
            name="🚀 XP & Coin Boosters (Stacks Duration!)",
            value=(
                "• **⚡ 2x Booster (1 Hour)** — `250 🌸`\n"
                "• **🔥 2x Booster (5 Hours)** — `900 🌸`\n"
                "• **🌟 2x Booster (24 Hours / 1 Day)** — `2,200 🌸`"
            ),
            inline=False
        )
        embed.add_field(
            name="🧰 Tactical Items & Upgrades",
            value=(
                "• **🔒 Heavy Padlock (Blocks `/rob`)** — `400 🌸`\n"
                "• **🏦 Bank Expansion Note (`+2,500` Safe Cap)** — `600 🌸`\n"
                "• **🎲 Mystery Lootbox (`100–2,000` Coins)** — `500 🌸`\n"
                "• **🏷️ Custom Nickname Pass** — `1,500 🌸`"
            ),
            inline=False
        )
        embed.add_field(
            name="👑 High-Prestige Server Roles",
            value=(
                "• **🌸 Mian VIP Role** — `15,000 🌸`\n"
                "• **💸 Rich Aim God Role** — `40,000 🌸`\n"
                "• **👑 Economy Legend Role** — `100,000 🌸`"
            ),
            inline=False
        )
        embed.set_footer(text="Check your wallet & active boosters anytime with /balance")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="buy", description="Buy an XP Booster, Padlock, Upgrade or Prestige Role from the Shop")
    @app_commands.choices(item=[
        app_commands.Choice(name=f"{name} ({price:,} Coins)", value=key)
        for key, (name, price, _, _) in SHOP_ITEMS.items()
    ])
    async def buy_cmd(self, interaction: discord.Interaction, item: str):
        await interaction.response.defer()
        name, price, meta, _ = SHOP_ITEMS[item]
        bal = await db.get_balance(interaction.guild.id, interaction.user.id)

        if bal < price:
            await interaction.followup.send(f"❌ You need **`{price:,}` 🌸 MianCoins** in your wallet to buy **{name}**, but you only have **`{bal:,}`**! *(Withdraw from `/bank` or chat more to earn!)*")
            return

        await db.update_balance(interaction.guild.id, interaction.user.id, -price)

        # Handle XP Boosters
        if meta == "booster_1h":
            rem = await db.activate_xp_booster(interaction.guild.id, interaction.user.id, 2.0, 3600)
            await interaction.followup.send(f"⚡ **2x BOOSTER ACTIVATED!** You now earn **Double XP & Chat Coins**! (Total active time: `{format_cooldown(rem)}`)")
            return
        if meta == "booster_5h":
            rem = await db.activate_xp_booster(interaction.guild.id, interaction.user.id, 2.0, 18000)
            await interaction.followup.send(f"🔥 **5-HOUR 2x BOOSTER ACTIVATED!** You now earn **Double XP & Chat Coins**! (Total active time: `{format_cooldown(rem)}`)")
            return
        if meta == "booster_24h":
            rem = await db.activate_xp_booster(interaction.guild.id, interaction.user.id, 2.0, 86400)
            await interaction.followup.send(f"🌟 **24-HOUR 2x BOOSTER ACTIVATED!** You now earn **Double XP & Chat Coins** for a full day! (Total active time: `{format_cooldown(rem)}`)")
            return

        # Handle Utility Items
        if meta == "item_padlock":
            async with aiosqlite.connect(db.DB_PATH) as conn:
                await conn.execute("UPDATE economy SET padlocks = padlocks + 1 WHERE guild_id = ? AND user_id = ?", (interaction.guild.id, interaction.user.id))
                await conn.commit()
            await interaction.followup.send("🔒 **Padlock Equipped!** Your wallet is now protected against the next `/rob` attempt!")
            return

        if meta == "item_bank":
            async with aiosqlite.connect(db.DB_PATH) as conn:
                await conn.execute("UPDATE economy SET bank_max = bank_max + 2500 WHERE guild_id = ? AND user_id = ?", (interaction.guild.id, interaction.user.id))
                await conn.commit()
            await interaction.followup.send("🏦 **Bank Upgraded!** Your safe Bank capacity increased by **`+2,500 🌸 MianCoins`**!")
            return

        if meta == "item_lootbox":
            prize = random.choices([100, 250, 450, 800, 2000], weights=[40, 30, 18, 9, 3], k=1)[0]
            final_bal = await db.update_balance(interaction.guild.id, interaction.user.id, prize)
            await interaction.followup.send(f"🎲 You cracked open a **Mystery Lootbox** and found **`+{prize:,}` 🌸 MianCoins**! (Wallet: `{final_bal:,}`)")
            return

        if meta == "item_nick":
            await interaction.followup.send("🏷️ **Nickname Pass Unlocked!** Ping staff or use `/nick` to set your custom title!")
            return

        # Handle Prestige Roles
        role = discord.utils.get(interaction.guild.roles, name=name)
        if not role:
            role = await interaction.guild.create_role(name=name, color=meta, hoist=True, reason="Lil Mian Prestige Shop Role")
        await interaction.user.add_roles(role)
        await interaction.followup.send(f"👑 **PRESTIGE UNLOCKED!** Congratulations {interaction.user.mention}, you claimed the **{role.mention}** role!")

    # ==========================================
    # 5. MINIGAMES (/slots, /coinflip, /trivia)
    # ==========================================
    @app_commands.command(name="slots", description="Spin the MianCoin Slot Machine (Max Bet: 500)")
    @app_commands.describe(bet="Amount of MianCoins to bet (1 - 500)")
    async def slots_cmd(self, interaction: discord.Interaction, bet: int):
        if bet <= 0 or bet > 500:
            await interaction.response.send_message("⚠️ Bet must be between **1 and 500 🌸 MianCoins**!", ephemeral=True)
            return
        bal = await db.get_balance(interaction.guild.id, interaction.user.id)
        if bal < bet:
            await interaction.response.send_message(f"❌ You don't have enough wallet coins! (Wallet: `{bal:,}`)", ephemeral=True)
            return

        emojis = ["🌸", "🎯", "⭕", "💎", "🍒", "7️⃣"]
        r1, r2, r3 = random.choices(emojis, k=3)

        if r1 == r2 == r3:
            winnings = bet * 4
            new_bal = await db.update_balance(interaction.guild.id, interaction.user.id, winnings)
            result = f"🎰 **JACKPOT (4x)!!** You won **+{winnings:,} 🌸 MianCoins**!"
        elif r1 == r2 or r2 == r3 or r1 == r3:
            winnings = int(bet * 1.3)
            new_bal = await db.update_balance(interaction.guild.id, interaction.user.id, winnings)
            result = f"✨ **DOUBLE MATCH (1.3x)!** You won **+{winnings:,} 🌸 MianCoins**!"
        else:
            new_bal = await db.update_balance(interaction.guild.id, interaction.user.id, -bet)
            result = f"💀 **No match!** You lost **-{bet:,} 🌸 MianCoins**."

        await interaction.response.send_message(f"### 🎰 `[ {r1} | {r2} | {r3} ]`\n{result}\n👛 **Wallet:** `{new_bal:,} 🌸`")

    @app_commands.command(name="coinflip", description="Bet MianCoins on Heads or Tails (Max Bet: 500)")
    @app_commands.choices(call=[
        app_commands.Choice(name="Heads", value="Heads"),
        app_commands.Choice(name="Tails", value="Tails")
    ])
    async def coinflip_cmd(self, interaction: discord.Interaction, call: str, bet: int):
        if bet <= 0 or bet > 500:
            await interaction.response.send_message("⚠️ Bet must be between **1 and 500 🌸 MianCoins**!", ephemeral=True)
            return
        bal = await db.get_balance(interaction.guild.id, interaction.user.id)
        if bal < bet:
            await interaction.response.send_message(f"❌ Not enough wallet coins! (Wallet: `{bal:,}`)", ephemeral=True)
            return

        flip = random.choice(["Heads", "Tails"])
        if flip == call:
            new_bal = await db.update_balance(interaction.guild.id, interaction.user.id, bet)
            await interaction.response.send_message(f"🪙 The coin landed on **{flip}**! You won **+{bet:,} 🌸 MianCoins**! (Wallet: `{new_bal:,}`)")
        else:
            new_bal = await db.update_balance(interaction.guild.id, interaction.user.id, -bet)
            await interaction.response.send_message(f"🪙 The coin landed on **{flip}**... You lost **-{bet:,} 🌸 MianCoins**. (Wallet: `{new_bal:,}`)")

    @app_commands.command(name="trivia", description="Answer a VALORANT or osu! trivia question for +35 MianCoins")
    @app_commands.checks.cooldown(1, 30.0, key=lambda i: (i.guild_id, i.user.id))
    async def trivia_cmd(self, interaction: discord.Interaction):
        q, opts, ans = random.choice(TRIVIA_QUESTIONS)
        shuffled = opts.copy()
        random.shuffle(shuffled)
        view = TriviaView(interaction.user.id, shuffled, ans)
        await interaction.response.send_message(f"🧠 **Gaming Trivia (+35 🌸 MianCoins):**\n> **{q}**", view=view)

async def setup(bot: commands.Bot):
    await bot.add_cog(EconomyFunCog(bot))