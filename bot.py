import os
import sys
import socket
import traceback
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import core_engine as engine

# Force all Cogs importing 'database' to use 'core_engine' directly
sys.modules["database"] = engine

from cogs.roles import RoleAssignmentView, ValorantAgentsView
from cogs.security import VerificationView

load_dotenv(override=True)
TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip().strip('"').strip("'")

# ==========================================
# SINGLETON SOCKET LOCK (PREVENTS DUPLICATE BOT INSTANCES!)
# Ensures Streamlit Cloud never spawns 2 bots fighting over 1 token
# ==========================================
_lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    _lock_socket.bind(("127.0.0.1", 49152))
except socket.error:
    print("⚠️ Lil Mian Bot is ALREADY running on this machine! Exiting duplicate process cleanly.")
    sys.exit(0)

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
        await engine.init_async_db()
        self.add_view(VerificationView())
        self.add_view(RoleAssignmentView())
        self.add_view(ValorantAgentsView())
        for cog in COGS:
            try:
                await self.load_extension(cog)
                print(f"🧩 Loaded Module: {cog}")
            except Exception as e:
                print(f"❌ Failed to load {cog}: {e}")
                traceback.print_exc()

        # Global Slash Command Error Handler (Prevents 'The application did not respond')
        self.tree.on_error = self.on_tree_error

    async def on_tree_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        original = getattr(error, "original", error)
        if isinstance(error, app_commands.CommandOnCooldown):
            msg = f"⏳ Cooldown active! Try again in **`{int(error.retry_after)}s`**."
        elif isinstance(error, app_commands.CheckFailure):
            return  # Handled by custom check
        else:
            msg = f"⚠️ **Command Error:** `{type(original).__name__}: {original}`"
            traceback.print_exc()

        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except Exception:
            pass

    async def on_ready(self):
        if not self.synced_once:
            try:
                # Sync immediately to every server the bot is in for instant 0-delay response!
                for guild in self.guilds:
                    self.tree.copy_global_to(guild=guild)
                    await self.tree.sync(guild=guild)
                    print(f"✅ Synced commands instantly to server: {guild.name}")
                await self.tree.sync()
            except Exception as e:
                print(f"⚠️ Sync note: {e}")
            self.synced_once = True

        await self.change_presence(
            activity=discord.Streaming(name="VALORANT & osu! | AwwMian", url="https://twitch.tv/AwwMian")
        )
        print(f"🚀 Lil Mian Command Engine is ONLINE as {self.user}!")

if __name__ == "__main__":
    if not TOKEN or len(TOKEN) < 50:
        print("❌ ERROR: DISCORD_BOT_TOKEN is missing or invalid!")
    else:
        bot = LilMianBot()
        bot.run(TOKEN)