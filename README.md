# 🌸 Lil Mian — Creator Command Center & All-In-One Discord Engine

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge&logo=python)
![Discord.py](https://img.shields.io/badge/discord.py-v2.4%2B-5865F2?style=for-the-badge&logo=discord&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Cloud_Ready-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Gemini AI](https://img.shields.io/badge/Google_Gemini-2.5_Flash-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white)
![License](https://img.shields.io/badge/License-Proprietary_(All_Rights_Reserved)-crimson?style=for-the-badge)

An enterprise-grade **Creator Intelligence Suite** and **Modular Discord Server Engine** engineered for **AwwMian** ([Twitch.tv/AwwMian](https://twitch.tv/AwwMian) | [@NotAwwMian](https://youtube.com/@NotAwwMian) | [@awwmianlive](https://instagram.com/awwmianlive)). Built with an asynchronous multi-cog architecture to replace external bots and centralize real-time social telemetry, AI trend forecasting, community economy, and automated server security.

---

## ✨ System Architecture & Core Modules

### 1. 🖥️ Cyberpunk Glassmorphic Dashboard (`dashboard.py` & `core_engine.py`)
- **SHA-256 Cryptographic Authentication Gate:** Protected against unauthorized public access using `hmac.compare_digest` dynamic SHA-256 passkey verification.
- **Real-Time Multi-Platform Telemetry:** Tracks live broadcast status, viewer velocity, and channel growth across Twitch, YouTube Data API v3, and Instagram, normalized to **Japan Standard Time (`JST / GMT+9`)**.
- **Live Gaming Trend Radar:** Scrapes hot community velocity from `r/VALORANT` and `r/osugame` XML RSS feeds alongside global search surges.
- **Gemini 2.5 Flash Viral Strategist:** Generates tailored long-form blueprints, short-form retention hooks, interactive stream segments, and 14-day meta predictions.
- **Live SQLite Database Inspector & Idea Vault:** Real-time synchronization with Discord's `/clip_idea` command, server XP leaderboards, MianCoin wealth tables, and staff moderation logs.

### 2. 🔔 Automated Content Ingestion (`cogs/alerts.py`)
- **Twitch Helix Live Monitor:** Polls `/helix/streams` every 60 seconds, dispatches rich stream preview embeds, pings `@🔴 Stream Ping`, and dynamically assigns/removes the `@🟣 LIVE NOW` streamer role.
- **YouTube RSS Smart Router:** Differentiates YouTube Long-Form uploads from `#Shorts`, routing announcements and role pings to dedicated channels without duplicate alerts.

### 3. 🛡️ Multi-Layer Security, Verification & Anti-Nuke (`cogs/security.py`)
- **Human Verification Gatekeeper:** Locks server channels behind a persistent `✅ Verify Me` interaction view while flagging accounts created under 24 hours ago.
- **Anti-Raid Join Velocity Shield:** Detects mass-join spikes (5+ accounts within 10s) and automatically applies quarantine timeouts.
- **Anti-Spam & Invite Link Filter:** Purges unauthorized external Discord invites and applies automatic 10-minute timeouts for message velocity or mass-mention spam.
- **Audit-Log Anti-Nuke Protection:** Monitors destructive staff actions (`channel_delete`, `ban`) and immediately strips administrative permissions if rate thresholds are exceeded.

### 4. 🎭 Persistent Self-Role & Onboarding Hub (`cogs/roles.py` & `cogs/welcome.py`)
- **Interactive Role Panels:** Persistent buttons and select menus for Notification Pings, Pronouns (`He/Him`, `She/Her`, `They/Them`), Age brackets, Dark/Light-mode calibrated Name Colors, Hobbies, and all **29 VALORANT Agent Main Roles**.
- **Anime Join/Leave Cards:** Automated welcome and goodbye embeds featuring account age telemetry, member count tracking, and curated anime GIF banners.

### 5. 🌸 Community Economy, Minigames & Live Game Tracker (`cogs/economy_fun.py`, `cogs/tracker.py`, `cogs/leveling.py`)
- **MianCoins Economy & Role Shop:** Persistent wallet system with strict database cooldowns on `/daily` (24h), `/weekly` (7d), and `/monthly` (30d) rewards, plus `/shop`, `/buy`, `/hunt`, `/beg`, `/crime`, `/slots`, `/coinflip`, and `/trivia`.
- **In-Game Combat & Rhythm Cards (`/game_stats`):** Queries live public VALORANT MMR/Account APIs and osu! signature generators to render real-time rank, RR, and PP cards.
- **XP & Milestone Leveling Engine:** Awards randomized activity XP on a 60-second cooldown with automated role rewards at Levels 5, 10, 25, and 50.

---

## 📁 Repository Structure

```text
AwwMian_Command_Center/
├── bot.py                  # Master Discord Bot Loader & Command Tree Sync
├── dashboard.py            # SHA-256 Protected Streamlit Web Command Center
├── core_engine.py          # Unified Telemetry, AI Predictor & SQLite Init
├── database.py             # Async SQLite Data Access Layer (aiosqlite)
├── requirements.txt        # Cloud & Production Python Dependencies
├── LICENSE                 # Proprietary All Rights Reserved License
└── cogs/
    ├── creator.py          # @awwmian-Locked Admin Suite & 1-Click /server_setup
    ├── alerts.py           # Twitch Helix & YouTube XML RSS Background Tasks
    ├── roles.py            # Persistent Onboarding & 29 VALORANT Agent Menus
    ├── security.py         # Verification Gate, Anti-Raid, Anti-Nuke & Mod Logs
    ├── leveling.py         # XP Curve Engine, Rank Cards & Leaderboards
    ├── welcome.py          # Animated Anime Join/Leave Cards
    ├── community.py        # Feedback Voting, Giveaways, Polls & Server Utilities
    ├── tracker.py          # Live VALORANT & osu! Rank Card Generator
    └── economy_fun.py      # MianCoins Economy, Role Shop, Memes & Anime Emotes