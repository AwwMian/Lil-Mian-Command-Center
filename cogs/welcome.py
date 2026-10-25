import random
import datetime
import discord
from discord import app_commands
from discord.ext import commands
import database as db

# Curated High-Res Anime Welcome & Goodbye GIFs
ANIME_WELCOME_GIFS = [
    "https://media1.tenor.com/m/m4t5k7D2B1AAAAAd/anime-welcome.gif",
    "https://media1.tenor.com/m/ce9I2j28pI4AAAAd/anime-wave.gif",
    "https://media1.tenor.com/m/wU6C2-kK2vUAAAAd/marin-kitagawa-anime-wave.gif",
    "https://media1.tenor.com/m/15Y1p1N1hFAAAAAd/bocchi-the-rock-kita-ikuyo.gif",
]

ANIME_LEAVE_GIFS = [
    "https://media1.tenor.com/m/9z2v1g1t0VAAAAAd/anime-bye-anime-wave.gif",
    "https://media1.tenor.com/m/7a5Y1k1x2CAAAAAd/frieren-beyond-journeys-end-frieren.gif",
    "https://media1.tenor.com/m/4x8K9w2v1LAAAAAd/cowboy-bebop-see-you-space-cowboy.gif",
]

class WelcomeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def build_welcome_embed(self, member: discord.Member, cfg: dict) -> discord.Embed:
        guild = member.guild
        rules_id = cfg.get("rules_channel_id") if cfg else None
        roles_id = cfg.get("roles_channel_id") if cfg else None

        rules_mention = f"<#{rules_id}>" if rules_id else "`#📜・rules`"
        roles_mention = f"<#{roles_id}>" if roles_id else "`#🎭・self-roles`"

        created_ago = discord.utils.format_dt(member.created_at, style="R")

        embed = discord.Embed(
            title=f"🌸 Welcome to {guild.name}, {member.display_name}!",
            description=(
                f"Yahallo {member.mention}! Welcome to **AwwMian's Official Community** 🎯⭕\n\n"
                f"╭・📜 **Read the Rules:** {rules_mention}\n"
                f"├・🎭 **Claim Agents, Colors & Pronouns:** {roles_mention}\n"
                f"├・🟣 **Live Streams:** [Twitch.tv/AwwMian](https://twitch.tv/AwwMian)\n"
                f"╰・✨ **Member Count:** You are member **#{guild.member_count}**!"
            ),
            color=discord.Color.from_rgb(219, 70, 145),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="🪪 Account Created", value=created_ago, inline=True)
        embed.add_field(name="🎮 Vibe Check", value="VALORANT • osu! • Anime", inline=True)
        embed.set_image(url=random.choice(ANIME_WELCOME_GIFS))
        embed.set_footer(text=f"User ID: {member.id} • Lil Mian Welcome Engine", icon_url=guild.icon.url if guild.icon else None)
        return embed

    async def build_leave_embed(self, member: discord.Member) -> discord.Embed:
        guild = member.guild
        roles = [r.mention for r in member.roles if r != guild.default_role]
        roles_str = ", ".join(roles[:6]) if roles else "*No roles*"

        embed = discord.Embed(
            title=f"💔 Sayonara, {member.display_name}...",
            description=(
                f"**{member}** (`{member.name}`) just left the server.\n"
                f"We now have **{guild.member_count}** members remaining."
            ),
            color=discord.Color.from_rgb(90, 24, 154),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="🎭 Roles They Had", value=roles_str, inline=False)
        embed.set_image(url=random.choice(ANIME_LEAVE_GIFS))
        embed.set_footer(text=f"User ID: {member.id} • See you next time!")
        return embed

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        cfg = await db.get_guild_config(member.guild.id)
        ch = None
        if cfg and cfg.get("joins_channel_id"):
            ch = member.guild.get_channel(cfg["joins_channel_id"])
        if not ch:
            ch = discord.utils.find(lambda c: "joins" in c.name.lower(), member.guild.text_channels)
        if ch:
            embed = await self.build_welcome_embed(member, cfg or {})
            await ch.send(content=f"🎉 **Everyone welcome {member.mention} to the server!**", embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        cfg = await db.get_guild_config(member.guild.id)
        ch = None
        if cfg and cfg.get("leaves_channel_id"):
            ch = member.guild.get_channel(cfg["leaves_channel_id"])
        if not ch:
            ch = discord.utils.find(lambda c: "leaves" in c.name.lower(), member.guild.text_channels)
        if ch:
            embed = await self.build_leave_embed(member)
            await ch.send(embed=embed)

    @app_commands.command(name="test_welcome", description="[Staff] Preview the Anime Welcome Card in #joins (or current channel)")
    @app_commands.default_permissions(manage_guild=True)
    async def test_welcome(self, interaction: discord.Interaction):
        cfg = await db.get_guild_config(interaction.guild.id)
        embed = await self.build_welcome_embed(interaction.user, cfg or {})
        await interaction.response.send_message(content=f"🎉 **Everyone welcome {interaction.user.mention} to the server!**", embed=embed)

    @app_commands.command(name="test_leave", description="[Staff] Preview the Anime Goodbye Card in #leaves (or current channel)")
    @app_commands.default_permissions(manage_guild=True)
    async def test_leave(self, interaction: discord.Interaction):
        embed = await self.build_leave_embed(interaction.user)
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeCog(bot))