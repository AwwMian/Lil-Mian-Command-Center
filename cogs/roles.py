import discord
from discord import app_commands
from discord.ext import commands
from typing import List, Tuple

# ==========================================
# MASTER ROLE DEFINITIONS (DARK & LIGHT MODE SAFE)
# ==========================================
PING_ROLES = [
    ("🔴 Stream Ping", discord.Color.from_rgb(230, 57, 70)),
    ("📺 YouTube Ping", discord.Color.from_rgb(214, 40, 40)),
    ("📱 Shorts Ping", discord.Color.from_rgb(247, 127, 0)),
]

IDENTITY_ROLES = [
    ("💙 He/Him", discord.Color.from_rgb(58, 134, 255)),
    ("🩷 She/Her", discord.Color.from_rgb(255, 71, 126)),
    ("💜 They/Them", discord.Color.from_rgb(157, 78, 221)),
    ("🔞 Adult (18+)", discord.Color.from_rgb(42, 157, 143)),
    ("🌱 Minor (<18)", discord.Color.from_rgb(82, 183, 136)),
]

GAME_ROLES = [
    ("🎯 VALORANT", discord.Color.from_rgb(255, 70, 85)),
    ("⭕ osu!", discord.Color.from_rgb(255, 102, 170)),
]

# Mid-luminance colors guaranteed to pop on BOTH Discord Dark & Light themes!
COLOR_ROLES: List[Tuple[str, str, discord.Color]] = [
    ("🎨 Crimson Rose", "🔴", discord.Color.from_rgb(217, 4, 82)),
    ("🎨 Electric Violet", "🟣", discord.Color.from_rgb(138, 43, 226)),
    ("🎨 Ocean Azure", "🔵", discord.Color.from_rgb(0, 119, 182)),
    ("🎨 Emerald Mint", "🟢", discord.Color.from_rgb(16, 148, 96)),
    ("🎨 Amber Gold", "🟡", discord.Color.from_rgb(217, 119, 6)),
    ("🎨 Coral Sunset", "🟠", discord.Color.from_rgb(231, 84, 43)),
    ("🎨 Sakura Pink", "🌸", discord.Color.from_rgb(219, 70, 145)),
    ("🎨 Berry Indigo", "🫐", discord.Color.from_rgb(90, 24, 154)),
]

HOBBY_AND_FUN_ROLES = [
    # Hobbies
    ("💻 Tech & PC Building", "💻", "Hobby: Custom PCs, Keyboards, IEMs & Mice"),
    ("🎨 Anime & Manga", "🍥", "Hobby: Seasonal Anime & Manga Reader"),
    ("🎵 Music & Rhythm", "🎧", "Hobby: J-Pop, Phonk, Vocaloid & Beats"),
    ("🎬 Content Creation", "🎥", "Hobby: Streaming, Editing & Thumbnails"),
    ("🖌️ Art & Design", "🎨", "Hobby: Illustration, 3D & GFX"),
    # Fun / Zero-Purpose Roles
    ("⌨️ Rapid Trigger Abuser", "⚡", "Fun Role: Movement & tap-strafe crutches"),
    ("💀 Bottom Fragger", "💀", "Fun Role: Moral support for the team"),
    ("🎯 Certified Whiffer", "🎯", "Fun Role: Outline drawing specialist"),
    ("🍪 Cookiezi Disciple", "🍪", "Fun Role: 727 WYSI rhythm gamer"),
    ("🛋️ Professional Lurker", "👀", "Fun Role: Watching chat from the shadows"),
    ("🔥 Edgy Duelist Ego", "🔥", "Fun Role: Instalock first, ask questions never"),
    ("🌱 Touching Grass (AFK)", "🌱", "Fun Role: Mythical outdoor explorer"),
]

# All 29 VALORANT Agents (Clean single-codepoint emojis so Discord API never errors)
VAL_DUELISTS_INITIATORS = [
    # Duelists (8)
    ("⚔️ Jett Main", "💨", "Duelist • Agile Wind Knife Specialist"),
    ("⚔️ Reyna Main", "🟣", "Duelist • Soul Harvest Pubstomper"),
    ("⚔️ Raze Main", "💣", "Duelist • Explosive Satchel Entry"),
    ("⚔️ Phoenix Main", "🔥", "Duelist • Flash & Run It Back"),
    ("⚔️ Yoru Main", "🌀", "Duelist • Dimensional Fakeout Master"),
    ("⚔️ Neon Main", "⚡", "Duelist • High-Gear Slide & Lightning"),
    ("⚔️ Iso Main", "🔮", "Duelist • 1v1 Domain Expansion"),
    ("⚔️ Waylay Main", "✨", "Duelist • Lightspeed Dash & Refract"),
    # Initiators (7)
    ("⚡ Sova Main", "🏹", "Initiator • Recon Lineup Nerd"),
    ("⚡ Breach Main", "💥", "Initiator • Fault Line & Flash Stun"),
    ("⚡ Skye Main", "🦅", "Initiator • Guiding Light & Trailblazer"),
    ("⚡ KAY/O Main", "🤖", "Initiator • Suppression Blade & Pop Flash"),
    ("⚡ Fade Main", "🌑", "Initiator • Nightmare Haunt & Prowlers"),
    ("⚡ Gekko Main", "🦎", "Initiator • Wingman Plant & Dizzy"),
    ("⚡ Tejo Main", "🚀", "Initiator • Ballistic Salvo & Stealth Drone"),
]

VAL_CONTROLLERS_SENTINELS = [
    # Controllers (7)
    ("☁️ Omen Main", "👻", "Controller • Paranoia & Shrouded Step"),
    ("☁️ Clove Main", "🦋", "Controller • Post-Mortem Smokes & Pick-Me-Up"),
    ("☁️ Brimstone Main", "🟠", "Controller • Sky Smokes & Orbital Strike"),
    ("☁️ Viper Main", "🧪", "Controller • Toxic Screen & Viper's Pit"),
    ("☁️ Astra Main", "🌌", "Controller • Cosmic Divide & Gravity Well"),
    ("☁️ Harbor Main", "🌊", "Controller • High Tide & Reckoning"),
    ("☁️ Miks Main", "🎵", "Controller • Waveform Cover & Bassquake"),
    # Sentinels (7)
    ("🛡️ Sage Main", "🧊", "Sentinel • Barrier Orb & Resurrection"),
    ("🛡️ Cypher Main", "📷", "Sentinel • One-Way Cage & Tripwire"),
    ("🛡️ Killjoy Main", "🐝", "Sentinel • Turret & Lockdown Anchor"),
    ("🛡️ Chamber Main", "🎩", "Sentinel • Headhunter & Tour De Force"),
    ("🛡️ Deadlock Main", "🕸", "Sentinel • Sonic Sensor & Annihilation"),
    ("🛡️ Vyse Main", "🌹", "Sentinel • Arc Rose & Steel Garden"),
    ("🛡️ Veto Main", "🚫", "Sentinel • Site Denial Specialist"),
]

async def ensure_role_exists(guild: discord.Guild, role_name: str, color: discord.Color = discord.Color.default()) -> discord.Role:
    role = discord.utils.get(guild.roles, name=role_name)
    if not role:
        role = await guild.create_role(name=role_name, color=color, reason="Lil Mian Auto Self-Role")
    return role

async def toggle_member_role(interaction: discord.Interaction, role_name: str, color: discord.Color = discord.Color.default()):
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        return
    await interaction.response.defer(ephemeral=True)
    role = await ensure_role_exists(interaction.guild, role_name, color)
    if role in interaction.user.roles:
        await interaction.user.remove_roles(role)
        await interaction.followup.send(f"➖ Removed **{role.name}** from your profile.", ephemeral=True)
    else:
        await interaction.user.add_roles(role)
        await interaction.followup.send(f"➕ Added **{role.name}** to your profile!", ephemeral=True)

# ==========================================
# VIEW 1: PINGS, PRONOUNS, AGE & CORE GAMES
# ==========================================
class RoleAssignmentView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    # ROW 0: Notification Pings
    @discord.ui.button(label="Stream Ping", emoji="🔴", style=discord.ButtonStyle.primary, row=0, custom_id="persistent:stream_ping")
    async def btn_stream(self, interaction: discord.Interaction, button: discord.ui.Button):
        await toggle_member_role(interaction, "🔴 Stream Ping", discord.Color.from_rgb(230, 57, 70))

    @discord.ui.button(label="YouTube Ping", emoji="📺", style=discord.ButtonStyle.danger, row=0, custom_id="persistent:yt_ping")
    async def btn_yt(self, interaction: discord.Interaction, button: discord.ui.Button):
        await toggle_member_role(interaction, "📺 YouTube Ping", discord.Color.from_rgb(214, 40, 40))

    @discord.ui.button(label="Shorts Ping", emoji="📱", style=discord.ButtonStyle.secondary, row=0, custom_id="persistent:shorts_ping")
    async def btn_shorts(self, interaction: discord.Interaction, button: discord.ui.Button):
        await toggle_member_role(interaction, "📱 Shorts Ping", discord.Color.from_rgb(247, 127, 0))

    # ROW 1: Pronouns & Age
    @discord.ui.button(label="He/Him", emoji="💙", style=discord.ButtonStyle.secondary, row=1, custom_id="persistent:he_him")
    async def btn_he(self, interaction: discord.Interaction, button: discord.ui.Button):
        await toggle_member_role(interaction, "💙 He/Him", discord.Color.from_rgb(58, 134, 255))

    @discord.ui.button(label="She/Her", emoji="🩷", style=discord.ButtonStyle.secondary, row=1, custom_id="persistent:she_her")
    async def btn_she(self, interaction: discord.Interaction, button: discord.ui.Button):
        await toggle_member_role(interaction, "🩷 She/Her", discord.Color.from_rgb(255, 71, 126))

    @discord.ui.button(label="They/Them", emoji="💜", style=discord.ButtonStyle.secondary, row=1, custom_id="persistent:they_them")
    async def btn_they(self, interaction: discord.Interaction, button: discord.ui.Button):
        await toggle_member_role(interaction, "💜 They/Them", discord.Color.from_rgb(157, 78, 221))

    @discord.ui.button(label="Adult (18+)", emoji="🔞", style=discord.ButtonStyle.secondary, row=1, custom_id="persistent:adult")
    async def btn_adult(self, interaction: discord.Interaction, button: discord.ui.Button):
        await toggle_member_role(interaction, "🔞 Adult (18+)", discord.Color.from_rgb(42, 157, 143))

    @discord.ui.button(label="Minor (<18)", emoji="🌱", style=discord.ButtonStyle.secondary, row=1, custom_id="persistent:minor")
    async def btn_minor(self, interaction: discord.Interaction, button: discord.ui.Button):
        await toggle_member_role(interaction, "🌱 Minor (<18)", discord.Color.from_rgb(82, 183, 136))

    # ROW 2: Core Games
    @discord.ui.button(label="VALORANT", emoji="🎯", style=discord.ButtonStyle.danger, row=2, custom_id="persistent:game_val")
    async def btn_val(self, interaction: discord.Interaction, button: discord.ui.Button):
        await toggle_member_role(interaction, "🎯 VALORANT", discord.Color.from_rgb(255, 70, 85))

    @discord.ui.button(label="osu!", emoji="⭕", style=discord.ButtonStyle.primary, row=2, custom_id="persistent:game_osu")
    async def btn_osu(self, interaction: discord.Interaction, button: discord.ui.Button):
        await toggle_member_role(interaction, "⭕ osu!", discord.Color.from_rgb(255, 102, 170))

    # ROW 3: Name Color Picker Dropdown
    @discord.ui.select(
        placeholder="🎨 Pick a Name Color (Works in Dark & Light Mode!)",
        min_values=1,
        max_values=1,
        row=3,
        custom_id="persistent:color_select",
        options=[
            discord.SelectOption(label=name, value=name, emoji=emoji, description="Sets your display name color!")
            for name, emoji, _ in COLOR_ROLES
        ] + [discord.SelectOption(label="Remove Color Role", value="NONE", emoji="❌", description="Reset your name color")]
    )
    async def color_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.defer(ephemeral=True)
        member = interaction.user
        guild = interaction.guild
        if not guild or not isinstance(member, discord.Member):
            return

        choice = select.values[0]
        color_names = [c[0] for c in COLOR_ROLES]
        to_remove = [r for r in member.roles if r.name in color_names]
        if to_remove:
            await member.remove_roles(*to_remove)

        if choice == "NONE":
            await interaction.followup.send("🗑️ Cleared your custom color role!", ephemeral=True)
            return

        color_obj = next((c[2] for c in COLOR_ROLES if c[0] == choice), discord.Color.default())
        role = await ensure_role_exists(guild, choice, color_obj)
        await member.add_roles(role)
        await interaction.followup.send(f"🎨 Switched your name color to **{role.name}**!", ephemeral=True)

    # ROW 4: Hobbies & Fun Zero-Purpose Roles Dropdown
    @discord.ui.select(
        placeholder="✨ Toggle Hobbies & Fun Personality Roles (Multi-Select)",
        min_values=1,
        max_values=len(HOBBY_AND_FUN_ROLES),
        row=4,
        custom_id="persistent:hobby_fun_select",
        options=[
            discord.SelectOption(label=name, value=name, emoji=emoji, description=desc)
            for name, emoji, desc in HOBBY_AND_FUN_ROLES
        ]
    )
    async def hobby_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.defer(ephemeral=True)
        member = interaction.user
        guild = interaction.guild
        if not guild or not isinstance(member, discord.Member):
            return
        added, removed = [], []
        for role_name in select.values:
            role = await ensure_role_exists(guild, role_name, discord.Color.from_rgb(114, 137, 218))
            if role in member.roles:
                await member.remove_roles(role)
                removed.append(role.name)
            else:
                await member.add_roles(role)
                added.append(role.name)
        msg = []
        if added:
            msg.append(f"➕ **Added:** {', '.join(added)}")
        if removed:
            msg.append(f"➖ **Removed:** {', '.join(removed)}")
        await interaction.followup.send("\n".join(msg), ephemeral=True)

# ==========================================
# VIEW 2: ALL 29 VALORANT MAIN AGENT ROLES
# ==========================================
class ValorantAgentsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="⚔️ Duelists & ⚡ Initiators — Select Your Main Agent(s)",
        min_values=1,
        max_values=3,
        row=0,
        custom_id="persistent:val_duel_init",
        options=[
            discord.SelectOption(label=name, value=name, emoji=emoji, description=desc)
            for name, emoji, desc in VAL_DUELISTS_INITIATORS
        ]
    )
    async def val_group_1(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.defer(ephemeral=True)
        member = interaction.user
        guild = interaction.guild
        if not guild or not isinstance(member, discord.Member):
            return
        added, removed = [], []
        for r_name in select.values:
            role = await ensure_role_exists(guild, r_name, discord.Color.from_rgb(255, 70, 85))
            if role in member.roles:
                await member.remove_roles(role)
                removed.append(role.name)
            else:
                await member.add_roles(role)
                added.append(role.name)
        lines = []
        if added:
            lines.append(f"🎯 **Equipped Main:** {', '.join(added)}")
        if removed:
            lines.append(f"➖ **Unequipped:** {', '.join(removed)}")
        await interaction.followup.send("\n".join(lines), ephemeral=True)

    @discord.ui.select(
        placeholder="☁️ Controllers & 🛡️ Sentinels — Select Your Main Agent(s)",
        min_values=1,
        max_values=3,
        row=1,
        custom_id="persistent:val_ctrl_sent",
        options=[
            discord.SelectOption(label=name, value=name, emoji=emoji, description=desc)
            for name, emoji, desc in VAL_CONTROLLERS_SENTINELS
        ]
    )
    async def val_group_2(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.defer(ephemeral=True)
        member = interaction.user
        guild = interaction.guild
        if not guild or not isinstance(member, discord.Member):
            return
        added, removed = [], []
        for r_name in select.values:
            role = await ensure_role_exists(guild, r_name, discord.Color.from_rgb(46, 196, 182))
            if role in member.roles:
                await member.remove_roles(role)
                removed.append(role.name)
            else:
                await member.add_roles(role)
                added.append(role.name)
        lines = []
        if added:
            lines.append(f"🛡️ **Equipped Main:** {', '.join(added)}")
        if removed:
            lines.append(f"➖ **Unequipped:** {', '.join(removed)}")
        await interaction.followup.send("\n".join(lines), ephemeral=True)

async def deploy_all_role_panels(channel: discord.TextChannel):
    embed1 = discord.Embed(
        title="🎭 AwwMian Identity, Colors, Games & Notification Roles",
        description=(
            "**Customize your server profile below!**\n\n"
            "🔔 **Row 1:** Stream, YouTube & Shorts Notification Pings\n"
            "💜 **Row 2:** Pronouns (`He/Him`, `She/Her`, `They/Them`) & Age (`Adult 18+`, `Minor <18`)\n"
            "🎮 **Row 3:** Core Games (`🎯 VALORANT`, `⭕ osu!`)\n"
            "🎨 **Menu 1:** Dark & Light Mode Friendly **Name Colors**\n"
            "✨ **Menu 2:** **Hobbies** (`Tech`, `Anime`, `Music`) & **Fun Zero-Purpose Roles** (`Rapid Trigger Abuser`, `Certified Whiffer`, `727 WYSI`)"
        ),
        color=discord.Color.from_rgb(138, 43, 226)
    )
    embed1.set_image(url="https://media1.tenor.com/m/wU6C2-kK2vUAAAAd/marin-kitagawa-anime-wave.gif")
    await channel.send(embed=embed1, view=RoleAssignmentView())

    embed2 = discord.Embed(
        title="🎯 VALORANT Agent Main Roster (All 29 Agents)",
        description=(
            "Rep your VALORANT Main in chat! Select up to 3 agents per menu (select again anytime to unequip):\n"
            "• **Menu 1:** ⚔️ **Duelists** (*Jett, Reyna, Raze, Phoenix, Yoru, Neon, Iso, Waylay*) & ⚡ **Initiators** (*Sova, Breach, Skye, KAY/O, Fade, Gekko, Tejo*)\n"
            "• **Menu 2:** ☁️ **Controllers** (*Omen, Clove, Brimstone, Viper, Astra, Harbor, Miks*) & 🛡️ **Sentinels** (*Sage, Cypher, Killjoy, Chamber, Deadlock, Vyse, Veto*)"
        ),
        color=discord.Color.from_rgb(255, 70, 85)
    )
    await channel.send(embed=embed2, view=ValorantAgentsView())

class RolesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="setup_roles", description="[Staff] Deploy the complete Self-Roles & VALORANT Agent panels here")
    @app_commands.default_permissions(manage_roles=True)
    async def setup_roles(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if isinstance(interaction.channel, discord.TextChannel):
            await deploy_all_role_panels(interaction.channel)
            await interaction.followup.send("✅ Deployed both Self-Role & VALORANT Agent Roster panels!", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(RolesCog(bot))