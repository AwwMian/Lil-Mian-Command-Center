import random
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
import database as db

SHOP_ITEMS = {
    "vip": ("🌸 Mian VIP", 1000, discord.Color.from_rgb(255, 105, 180), "Exclusive Pink VIP Role in the server!"),
    "rich": ("💸 Rich Aim God", 2500, discord.Color.from_rgb(255, 215, 0), "Flex your wealth on the leaderboard!"),
    "king": ("👑 Economy Legend", 5000, discord.Color.from_rgb(138, 43, 226), "Ultimate high-roller status role!"),
    "lootbox": ("🎲 Mystery Lootbox", 300, discord.Color.teal(), "Win between 50 and 1,200 MianCoins instantly!")
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
                new_bal = await db.update_balance(interaction.guild.id, interaction.user.id, 150)
                await interaction.response.edit_message(
                    content=f"✅ **CORRECT!** (`{self.correct}`) You won **+150 🌸 MianCoins**! (Balance: `{new_bal:,}`)",
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
    # 1. ANIME EMOTE DROPDOWN (/emote)
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

    # ==========================================
    # 2. VALORANT & OSU! MEMES (/memes)
    # ==========================================
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
    # 3. ECONOMY: WALLET, DAILY, WEEKLY, MONTHLY
    # ==========================================
    @app_commands.command(name="balance", description="Check your 🌸 MianCoins wallet balance")
    async def balance_cmd(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        bal = await db.get_balance(interaction.guild.id, target.id)
        embed = discord.Embed(
            title=f"👛 {target.display_name}'s MianCoin Wallet",
            description=f"🌸 **Balance:** `{bal:,} MianCoins`\n*Spend your coins in `/shop` or test your luck in `/slots` & `/coinflip`!*",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="daily", description="Claim your daily +250 🌸 MianCoins reward (24h cooldown)")
    async def daily_cmd(self, interaction: discord.Interaction):
        ok, val, reward = await db.claim_timed_reward(interaction.guild.id, interaction.user.id, "last_daily", 250, 86400)
        if not ok:
            await interaction.response.send_message(
                f"⏳ **Daily Cooldown!** You already claimed your daily reward. Come back in **`{format_cooldown(val)}`**!",
                ephemeral=True
            )
            return
        await interaction.response.send_message(f"🎁 **Daily Reward Claimed!** You received **+{reward:,} 🌸 MianCoins**! (New Balance: `{val:,}`)")

    @app_commands.command(name="weekly", description="Claim your weekly +1,200 🌸 MianCoins bonus (7d cooldown)")
    async def weekly_cmd(self, interaction: discord.Interaction):
        ok, val, reward = await db.claim_timed_reward(interaction.guild.id, interaction.user.id, "last_weekly", 1200, 604800)
        if not ok:
            await interaction.response.send_message(
                f"⏳ **Weekly Cooldown!** You already claimed your weekly bonus. Come back in **`{format_cooldown(val)}`**!",
                ephemeral=True
            )
            return
        await interaction.response.send_message(f"💎 **Weekly Bonus Claimed!** You received **+{reward:,} 🌸 MianCoins**! (New Balance: `{val:,}`)")

    @app_commands.command(name="monthly", description="Claim your monthly +5,000 🌸 MianCoins jackpot (30d cooldown)")
    async def monthly_cmd(self, interaction: discord.Interaction):
        ok, val, reward = await db.claim_timed_reward(interaction.guild.id, interaction.user.id, "last_monthly", 5000, 2592000)
        if not ok:
            await interaction.response.send_message(
                f"⏳ **Monthly Cooldown!** You already claimed your monthly jackpot. Come back in **`{format_cooldown(val)}`**!",
                ephemeral=True
            )
            return
        await interaction.response.send_message(f"👑 **Monthly Jackpot Claimed!** You received **+{reward:,} 🌸 MianCoins**! (New Balance: `{val:,}`)")

    # ==========================================
    # 4. ACTION COMMANDS (/beg, /hunt, /crime)
    # ==========================================
    @app_commands.command(name="beg", description="Ask VALORANT pros & osu! legends for spare MianCoins")
    @app_commands.checks.cooldown(1, 30.0, key=lambda i: (i.guild_id, i.user.id))
    async def beg_cmd(self, interaction: discord.Interaction):
        donors = ["TenZ", "mrekk", "Cookiezi", "Boaster", "AwwMian", "Kyedae", "Faker"]
        donor = random.choice(donors)
        if random.random() < 0.78:
            reward = random.randint(35, 140)
            new_bal = await db.update_balance(interaction.guild.id, interaction.user.id, reward)
            await interaction.response.send_message(
                f"🥺 **{donor}** felt bad for your bottom-fragging and tossed you **+{reward} 🌸 MianCoins**! (Balance: `{new_bal:,}`)"
            )
        else:
            await interaction.response.send_message(f"💀 **{donor}** looked at your crosshair placement and walked away. (`+0 coins`)")

    @app_commands.command(name="hunt", description="Go hunting for rare creatures & gun buddies to sell for MianCoins")
    @app_commands.checks.cooldown(1, 30.0, key=lambda i: (i.guild_id, i.user.id))
    async def hunt_cmd(self, interaction: discord.Interaction):
        loot = [
            ("🐛 Common Slime", 40),
            ("🦊 Kitsune Spirit", 95),
            ("🦎 Gekko's Wingman", 160),
            ("🐻 Evori Dreamwings", 240),
            ("🐉 Elderflame Vandal Dragon (MYTHIC!)", 500)
        ]
        found_name, coins = random.choices(loot, weights=[45, 28, 15, 9, 3], k=1)[0]
        new_bal = await db.update_balance(interaction.guild.id, interaction.user.id, coins)
        await interaction.response.send_message(
            f"🏹 **Hunt Complete!** You caught a **{found_name}** worth **+{coins} 🌸 MianCoins**! (Balance: `{new_bal:,}`)"
        )

    @app_commands.command(name="crime", description="High-risk heist! Win big MianCoins or pay a fine")
    @app_commands.checks.cooldown(1, 45.0, key=lambda i: (i.guild_id, i.user.id))
    async def crime_cmd(self, interaction: discord.Interaction):
        crimes = [
            "hacked Riot Vanguard servers",
            "borrowed Peppy's private osu! jet",
            "smuggled Radiant Rank gun buddies",
            "rigged a VCT Finals bracket"
        ]
        act = random.choice(crimes)
        if random.random() < 0.55:
            win = random.randint(200, 450)
            new_bal = await db.update_balance(interaction.guild.id, interaction.user.id, win)
            await interaction.response.send_message(f"🕵️ **HEIST SUCCESS!** You {act} and escaped with **+{win} 🌸 MianCoins**! (Balance: `{new_bal:,}`)")
        else:
            loss = random.randint(80, 180)
            new_bal = await db.update_balance(interaction.guild.id, interaction.user.id, -loss)
            await interaction.response.send_message(f"🚓 **BUSTED!** Security caught you trying to {act}! You paid a **-{loss} 🌸 MianCoins** fine. (Balance: `{new_bal:,}`)")

    @beg_cmd.error
    @hunt_cmd.error
    @crime_cmd.error
    async def action_cooldown_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"⏳ Slow down! Wait **`{int(error.retry_after)}s`** before using this again.", ephemeral=True)

    # ==========================================
    # 5. SERVER SHOP (/shop & /buy)
    # ==========================================
    @app_commands.command(name="shop", description="Browse roles & lootboxes you can buy with 🌸 MianCoins")
    async def shop_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🏪 AwwMian Server Shop",
            description="Use `/buy` to unlock server roles and mystery lootboxes with your **🌸 MianCoins**!",
            color=discord.Color.from_rgb(219, 70, 145)
        )
        for key, (name, price, _, desc) in SHOP_ITEMS.items():
            embed.add_field(
                name=f"{name} — `{price:,} 🌸`",
                value=f"{desc}",
                inline=False
            )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="buy", description="Buy a Role or Mystery Lootbox from the Server Shop")
    @app_commands.choices(item=[
        app_commands.Choice(name=f"{name} ({price} Coins)", value=key)
        for key, (name, price, _, _) in SHOP_ITEMS.items()
    ])
    async def buy_cmd(self, interaction: discord.Interaction, item: str):
        await interaction.response.defer()
        name, price, color, _ = SHOP_ITEMS[item]
        bal = await db.get_balance(interaction.guild.id, interaction.user.id)

        if bal < price:
            await interaction.followup.send(f"❌ You need **`{price:,}` 🌸 MianCoins** to buy **{name}**, but you only have **`{bal:,}`**!")
            return

        await db.update_balance(interaction.guild.id, interaction.user.id, -price)

        if item == "lootbox":
            prize = random.randint(50, 1200)
            final_bal = await db.update_balance(interaction.guild.id, interaction.user.id, prize)
            await interaction.followup.send(f"🎲 You opened a **Mystery Lootbox** and won **`+{prize:,}` 🌸 MianCoins**! (New Balance: `{final_bal:,}`)")
            return

        role = discord.utils.get(interaction.guild.roles, name=name)
        if not role:
            role = await interaction.guild.create_role(name=name, color=color, hoist=True, reason="Lil Mian Shop Role")
        await interaction.user.add_roles(role)
        await interaction.followup.send(f"🎉 **PURCHASE COMPLETE!** You unlocked the **{role.mention}** role!")

    # ==========================================
    # 6. MINIGAMES (/slots, /coinflip, /trivia)
    # ==========================================
    @app_commands.command(name="slots", description="Spin the MianCoin Slot Machine")
    @app_commands.describe(bet="Amount of MianCoins to bet")
    async def slots_cmd(self, interaction: discord.Interaction, bet: int):
        if bet <= 0:
            await interaction.response.send_message("Bet must be greater than 0!", ephemeral=True)
            return
        bal = await db.get_balance(interaction.guild.id, interaction.user.id)
        if bal < bet:
            await interaction.response.send_message(f"❌ You don't have enough MianCoins! (Balance: `{bal:,}`)", ephemeral=True)
            return

        emojis = ["🌸", "🎯", "⭕", "💎", "🍒", "7️⃣"]
        r1, r2, r3 = random.choices(emojis, k=3)

        if r1 == r2 == r3:
            winnings = bet * 5
            new_bal = await db.update_balance(interaction.guild.id, interaction.user.id, winnings)
            result = f"🎰 **JACKPOT (5x)!!** You won **+{winnings:,} 🌸 MianCoins**!"
        elif r1 == r2 or r2 == r3 or r1 == r3:
            winnings = int(bet * 1.5)
            new_bal = await db.update_balance(interaction.guild.id, interaction.user.id, winnings)
            result = f"✨ **DOUBLE MATCH (1.5x)!** You won **+{winnings:,} 🌸 MianCoins**!"
        else:
            new_bal = await db.update_balance(interaction.guild.id, interaction.user.id, -bet)
            result = f"💀 **No match!** You lost **-{bet:,} 🌸 MianCoins**."

        await interaction.response.send_message(f"### 🎰 `[ {r1} | {r2} | {r3} ]`\n{result}\n👛 **Balance:** `{new_bal:,} 🌸`")

    @app_commands.command(name="coinflip", description="Bet MianCoins on Heads or Tails (Double or Nothing)")
    @app_commands.choices(call=[
        app_commands.Choice(name="Heads", value="Heads"),
        app_commands.Choice(name="Tails", value="Tails")
    ])
    async def coinflip_cmd(self, interaction: discord.Interaction, call: str, bet: int):
        if bet <= 0:
            await interaction.response.send_message("Bet must be > 0!", ephemeral=True)
            return
        bal = await db.get_balance(interaction.guild.id, interaction.user.id)
        if bal < bet:
            await interaction.response.send_message(f"❌ Not enough coins! (Balance: `{bal:,}`)", ephemeral=True)
            return

        flip = random.choice(["Heads", "Tails"])
        if flip == call:
            new_bal = await db.update_balance(interaction.guild.id, interaction.user.id, bet)
            await interaction.response.send_message(f"🪙 The coin landed on **{flip}**! You won **+{bet:,} 🌸 MianCoins**! (Balance: `{new_bal:,}`)")
        else:
            new_bal = await db.update_balance(interaction.guild.id, interaction.user.id, -bet)
            await interaction.response.send_message(f"🪙 The coin landed on **{flip}**... You lost **-{bet:,} 🌸 MianCoins**. (Balance: `{new_bal:,}`)")

    @app_commands.command(name="trivia", description="Answer a VALORANT or osu! trivia question for +150 MianCoins")
    async def trivia_cmd(self, interaction: discord.Interaction):
        q, opts, ans = random.choice(TRIVIA_QUESTIONS)
        shuffled = opts.copy()
        random.shuffle(shuffled)
        view = TriviaView(interaction.user.id, shuffled, ans)
        await interaction.response.send_message(f"🧠 **Gaming Trivia (+150 🌸 MianCoins):**\n> **{q}**", view=view)

async def setup(bot: commands.Bot):
    await bot.add_cog(EconomyFunCog(bot))