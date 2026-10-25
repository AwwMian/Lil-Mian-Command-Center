import random
import asyncio
import datetime
import discord
from discord import app_commands
from discord.ext import commands
import database as db

class GiveawayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.entrants = set()

    @discord.ui.button(label="Enter Giveaway (0)", emoji="🎉", style=discord.ButtonStyle.success, custom_id="giveaway:enter")
    async def enter_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.entrants:
            self.entrants.remove(interaction.user.id)
            button.label = f"Enter Giveaway ({len(self.entrants)})"
            await interaction.message.edit(view=self)
            await interaction.response.send_message("❌ You left the giveaway.", ephemeral=True)
        else:
            self.entrants.add(interaction.user.id)
            button.label = f"Enter Giveaway ({len(self.entrants)})"
            await interaction.message.edit(view=self)
            await interaction.response.send_message("✅ You are entered into the giveaway! Good luck!", ephemeral=True)

class CommunityCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="feedback", description="Suggest a new feature or report a bug for Lil Mian / AwwMian's server!")
    @app_commands.describe(category="Feature Request, Bug Report, or Stream Suggestion", suggestion="Describe your idea or bug in detail")
    @app_commands.choices(category=[
        app_commands.Choice(name="💡 Bot Feature Suggestion", value="💡 Feature Suggestion"),
        app_commands.Choice(name="🐛 Bug Report", value="🐛 Bug Report"),
        app_commands.Choice(name="🎥 Stream / Server Idea", value="🎥 Stream / Server Idea")
    ])
    async def feedback_cmd(self, interaction: discord.Interaction, category: str, suggestion: str):
        await interaction.response.defer(ephemeral=True)
        cfg = await db.get_guild_config(interaction.guild.id)
        ch = None
        if cfg and cfg.get("feedback_channel_id"):
            ch = interaction.guild.get_channel(cfg["feedback_channel_id"])
        if not ch:
            ch = discord.utils.find(lambda c: "feedback" in c.name.lower(), interaction.guild.text_channels) or interaction.channel

        embed = discord.Embed(
            title=f"{category}",
            description=f"**Submitted by:** {interaction.user.mention}\n\n> {suggestion}",
            color=discord.Color.from_rgb(58, 134, 255),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text="Vote with 👍 or 👎 below!")

        msg = await ch.send(embed=embed)
        await msg.add_reaction("👍")
        await msg.add_reaction("👎")
        await interaction.followup.send(f"✅ Your feedback has been posted in {ch.mention} for the community & `@awwmian` to review!", ephemeral=True)

    @app_commands.command(name="avatar", description="Display a member's full-resolution avatar")
    async def avatar_cmd(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        embed = discord.Embed(title=f"🖼️ {target.display_name}'s Avatar", color=discord.Color.purple())
        embed.set_image(url=target.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="serverinfo", description="View detailed stats about AwwMian's Discord server")
    async def serverinfo_cmd(self, interaction: discord.Interaction):
        g = interaction.guild
        if not g:
            return
        embed = discord.Embed(title=f"🏰 {g.name} — Server Info", color=discord.Color.purple())
        if g.icon:
            embed.set_thumbnail(url=g.icon.url)
        embed.add_field(name="👑 Owner", value=g.owner.mention if g.owner else "AwwMian", inline=True)
        embed.add_field(name="👥 Members", value=f"**{g.member_count}**", inline=True)
        embed.add_field(name="🚀 Boosts", value=f"Level {g.premium_tier} ({g.premium_subscription_count} boosts)", inline=True)
        embed.add_field(name="💬 Channels", value=f"{len(g.text_channels)} Text | {len(g.voice_channels)} Voice", inline=True)
        embed.add_field(name="🎭 Roles", value=str(len(g.roles)), inline=True)
        embed.add_field(name="📅 Created", value=discord.utils.format_dt(g.created_at, style="R"), inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="poll", description="Create an instant interactive community poll")
    async def poll_cmd(self, interaction: discord.Interaction, question: str, option_a: str, option_b: str):
        embed = discord.Embed(
            title=f"📊 Community Poll: {question}",
            description=f"🅰️ **{option_a}**\n\n🅱️ **{option_b}**",
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Poll started by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        await msg.add_reaction("🅰️")
        await msg.add_reaction("🅱️")

    @app_commands.command(name="8ball", description="Ask Lil Mian's Magic 8-Ball a question")
    async def eightball_cmd(self, interaction: discord.Interaction, question: str):
        answers = [
            "🎱 **100% Yes — Lock in and top frag!**",
            "🎱 **It is decidedly so (727 WYSI).**",
            "🎱 **Without a doubt!**",
            "🎱 **Ask again after Wednesday's 9:30 PM JST stream.**",
            "🎱 **My sources say whiff incoming... be careful.**",
            "🎱 **Outlook not so good (Skill Issue detected).**",
            "🎱 **Guaranteed FC / Radiant rank up energy!**"
        ]
        await interaction.response.send_message(f"> ❓ *{question}*\n{random.choice(answers)}")

    @app_commands.command(name="giveaway", description="[Staff] Start an interactive button giveaway!")
    @app_commands.default_permissions(manage_guild=True)
    async def giveaway_cmd(self, interaction: discord.Interaction, prize: str, minutes: int):
        end_dt = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=minutes)
        view = GiveawayView()
        embed = discord.Embed(
            title=f"🎁 GIVEAWAY: {prize}",
            description=(
                f"Click the **🎉 Enter Giveaway** button below to join!\n\n"
                f"⏰ **Ends:** {discord.utils.format_dt(end_dt, style='R')}\n"
                f"👑 **Hosted by:** {interaction.user.mention}"
            ),
            color=discord.Color.from_rgb(219, 70, 145)
        )
        await interaction.response.send_message(embed=embed, view=view)
        msg = await interaction.original_response()

        await asyncio.sleep(max(1, minutes) * 60)
        if not view.entrants:
            await msg.reply(f"😢 Giveaway for **{prize}** ended, but nobody entered!")
            return
        winner_id = random.choice(list(view.entrants))
        await msg.reply(f"🎊 **CONGRATULATIONS <@{winner_id}>!** You won the **{prize}** giveaway! 🎉")

async def setup(bot: commands.Bot):
    await bot.add_cog(CommunityCog(bot))