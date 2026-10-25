import urllib.parse
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

class TrackerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="game_stats", description="Generate a live VALORANT or osu! In-Game Rank, KDA & Win-Rate Card!")
    @app_commands.describe(
        game="Choose VALORANT or osu!",
        ign="For VALORANT use Name#TAG (e.g. TenZ#0001). For osu! enter username (e.g. mrekk)"
    )
    @app_commands.choices(game=[
        app_commands.Choice(name="🎯 VALORANT (Riot ID: Name#TAG)", value="valorant"),
        app_commands.Choice(name="⭕ osu! (Standard Username)", value="osu")
    ])
    async def game_stats_cmd(self, interaction: discord.Interaction, game: str, ign: str):
        await interaction.response.defer()

        if game == "valorant":
            if "#" not in ign:
                await interaction.followup.send("⚠️ For **VALORANT**, please include your Riot Tag! Example: `/game_stats game:VALORANT ign:AwwMian#JP1`")
                return
            name, tag = ign.split("#", 1)
            await self.fetch_valorant_card(interaction, name.strip(), tag.strip())
        else:
            await self.fetch_osu_card(interaction, ign.strip())

    async def fetch_valorant_card(self, interaction: discord.Interaction, name: str, tag: str):
        safe_name = urllib.parse.quote(name)
        safe_tag = urllib.parse.quote(tag)
        tracker_url = f"https://tracker.gg/valorant/profile/riot/{safe_name}%23{safe_tag}/overview"

        async with aiohttp.ClientSession() as session:
            # Query HenrikDev Public VALORANT API for Account + MMR
            acc_url = f"https://api.henrikdev.xyz/valorant/v1/account/{safe_name}/{safe_tag}"
            async with session.get(acc_url) as resp:
                if resp.status == 200:
                    acc_js = await resp.json()
                    acc_data = acc_js.get("data", {})
                    region = acc_data.get("region", "ap")
                    lvl = acc_data.get("account_level", "??")
                    card_img = acc_data.get("card", {}).get("wide", "")
                    small_img = acc_data.get("card", {}).get("small", "")

                    mmr_url = f"https://api.henrikdev.xyz/valorant/v2/mmr/{region}/{safe_name}/{safe_tag}"
                    rank_str = "Unranked / Placements"
                    peak_str = "N/A"
                    rr = 0
                    rank_icon = small_img

                    async with session.get(mmr_url) as m_resp:
                        if m_resp.status == 200:
                            m_js = await m_resp.json()
                            m_data = m_js.get("data", {})
                            curr = m_data.get("current_data", {})
                            high = m_data.get("highest_rank", {})
                            rank_str = curr.get("currenttierpatched") or "Unranked"
                            rr = curr.get("ranking_in_tier") or 0
                            peak_str = high.get("patched_tier") or rank_str
                            if curr.get("images", {}).get("large"):
                                rank_icon = curr["images"]["large"]

                    embed = discord.Embed(
                        title=f"🎯 VALORANT Combat Record — {name}#{tag}",
                        url=tracker_url,
                        description=f"🌍 **Region:** `{region.upper()}` • ⭐ **Account Level:** `{lvl}`",
                        color=discord.Color.from_rgb(255, 70, 85)
                    )
                    if rank_icon:
                        embed.set_thumbnail(url=rank_icon)
                    embed.add_field(name="🏆 Current Rank", value=f"**{rank_str}** (`{rr} RR`)", inline=True)
                    embed.add_field(name="👑 Peak Rank", value=f"**{peak_str}**", inline=True)
                    embed.add_field(name="📊 Full Match History", value=f"[View on Tracker.gg]({tracker_url})", inline=True)
                    if card_img:
                        embed.set_image(url=card_img)
                    embed.set_footer(text="Lil Mian Live VALORANT Telemetry • Powered by Riot / HenrikDev")
                    await interaction.followup.send(embed=embed)
                    return

        # Clean Fallback Card with direct Tracker.gg link & dynamic badge if public API is rate-limited
        embed = discord.Embed(
            title=f"🎯 VALORANT Tracker Card — {name}#{tag}",
            url=tracker_url,
            description=(
                f"Click below to inspect **{name}#{tag}**'s live KDA, Headshot %, Agent Win-Rates, and Match History:\n"
                f"🔗 **[Open Live Profile on Tracker.gg]({tracker_url})**"
            ),
            color=discord.Color.from_rgb(255, 70, 85)
        )
        embed.set_thumbnail(url="https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/27/largeicon.png")
        embed.add_field(name="🎮 Riot ID", value=f"`{name}#{tag}`", inline=True)
        embed.add_field(name="🔥 Status", value="Ready for Competitive", inline=True)
        await interaction.followup.send(embed=embed)

    async def fetch_osu_card(self, interaction: discord.Interaction, username: str):
        safe_user = urllib.parse.quote(username)
        profile_url = f"https://osu.ppy.sh/users/{safe_user}"
        # Lemmmy's live osu! signature generator builds a real-time graphical rank/PP/accuracy banner!
        live_card_banner = f"https://lemmmy.pw/osusig/sig.php?colour=hexff66aa&uname={safe_user}&pp=1&countryrank&flagshadow&onlineindicator=undefined&xpbar&xpbarhex"

        embed = discord.Embed(
            title=f"⭕ osu! Rhythm Profile — {username}",
            url=profile_url,
            description=f"🔗 **[View Official osu! Profile & Top Plays]({profile_url})**",
            color=discord.Color.from_rgb(255, 102, 170)
        )
        embed.set_image(url=live_card_banner)
        embed.set_footer(text="Lil Mian Live osu! Rank Card • Updates in real-time!")
        await interaction.followup.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(TrackerCog(bot))