import os
import traceback
import discord
from discord.ext import commands
from dotenv import load_dotenv
import core_engine as engine
from cogs.roles import RoleAssignmentView, ValorantAgentsView
from cogs.security import VerificationView

load_dotenv(override=True)
TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip().strip('"').strip("'")

COGS = [
    "cogs.creator",
    "cogs.alerts",
    "cogs.roles",
    "cogs.security",
    "cogs.leveling",
    "cogs.welcome",
    "cogs.community",
    "cogs.tracker",
    "cogs.economy_fun"
]

class LilMianBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.presences = True
        super().__init__(command_prefix="!", intents=intents)
        self.synced_once = False

    async def setup_hook(self):
        # 1. Initialize SQLite Tables directly from core_engine
        await engine.init_async_db()
        
        # 2. Register Persistent Views
        self.add_view(VerificationView())
        self.add_view(RoleAssignmentView())
        self.add_view(ValorantAgentsView())
        
        # 3. Load all Cogs safely
        for cog in COGS:
            try:
                await self.load_extension(cog)
                print(f"🧩 Loaded Module: {cog}")
            except Exception as e:
                print(f"❌ Failed to load {cog}: {e}")
                traceback.print_exc()

    async def on_ready(self):
        if not self.synced_once:
            try:
                # Wipe guild-level duplicates first so only 1 clean set exists
                for guild in self.guilds:
                    self.tree.clear_commands(guild=guild)
                    await self.tree.sync(guild=guild)
                # Sync master command tree globally
                await self.tree.sync()
                print("✅ Slash Commands Deduplicated & Synced!")
            except Exception as e:
                print(f"⚠️ Sync note: {e}")
            self.synced_once = True

        await self.change_presence(
            activity=discord.Streaming(name="VALORANT & osu! | AwwMian", url="https://twitch.tv/AwwMian")
        )
        print(f"🚀 Lil Mian Command Engine is ONLINE as {self.user}!")

if __name__ == "__main__":
    if not TOKEN or len(TOKEN) < 50:
        print("❌ ERROR: DISCORD_BOT_TOKEN is missing or invalid in .env!")
        input("Press Enter to exit...")
    else:
        try:
            bot = LilMianBot()
            bot.run(TOKEN)
        except Exception as e:
            print(f"❌ Bot Crashed: {e}")
            traceback.print_exc()
            input("Press Enter to exit...")