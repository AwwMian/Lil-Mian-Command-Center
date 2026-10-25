import os
import time
import sqlite3
import datetime
import subprocess
import webbrowser
import xml.etree.ElementTree as ET
from typing import Optional, Dict, Any, List, Tuple
import requests
import pytz
import aiosqlite
from dotenv import load_dotenv
from google import genai

load_dotenv(override=True)

def clean_env(key: str, default: str = "") -> str:
    val = os.getenv(key, default)
    return val.strip().strip('"').strip("'") if val else default

TWITCH_CHANNEL = clean_env("TWITCH_CHANNEL", "AwwMian")
TWITCH_CLIENT_ID = clean_env("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = clean_env("TWITCH_CLIENT_SECRET")
YOUTUBE_API_KEY = clean_env("YOUTUBE_API_KEY")
YOUTUBE_HANDLE = "@NotAwwMian"
IG_HANDLE = "@awwmianlive"
GEMINI_KEY = clean_env("GEMINI_API_KEY")

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "awwmian_vault.db")

# ==========================================
# 0. UNIFIED SYNC & ASYNC SQLITE ENGINE
# ==========================================
def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS idea_vault (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            source TEXT,
            idea TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS guild_config (
            guild_id INTEGER PRIMARY KEY,
            twitch_channel_id INTEGER,
            yt_channel_id INTEGER,
            shorts_channel_id INTEGER,
            mod_log_channel_id INTEGER,
            roles_channel_id INTEGER,
            rules_channel_id INTEGER,
            announcements_channel_id INTEGER,
            joins_channel_id INTEGER,
            leaves_channel_id INTEGER,
            verify_channel_id INTEGER,
            feedback_channel_id INTEGER,
            memes_channel_id INTEGER,
            clips_channel_id INTEGER,
            verified_role_id INTEGER,
            stream_ping_role_id INTEGER,
            yt_ping_role_id INTEGER,
            shorts_ping_role_id INTEGER,
            live_streamer_role_id INTEGER,
            lvl5_role_id INTEGER,
            lvl10_role_id INTEGER,
            lvl25_role_id INTEGER,
            lvl50_role_id INTEGER,
            is_currently_live INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS posted_videos (
            video_id TEXT PRIMARY KEY,
            published_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            user_id INTEGER,
            moderator_id INTEGER,
            reason TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_xp (
            guild_id INTEGER,
            user_id INTEGER,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 0,
            PRIMARY KEY (guild_id, user_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS economy (
            guild_id INTEGER,
            user_id INTEGER,
            balance INTEGER DEFAULT 100,
            bank INTEGER DEFAULT 0,
            last_daily REAL DEFAULT 0,
            last_weekly REAL DEFAULT 0,
            last_monthly REAL DEFAULT 0,
            inventory TEXT DEFAULT '',
            PRIMARY KEY (guild_id, user_id)
        )
    """)
    conn.commit()
    conn.close()

init_db()

async def init_async_db() -> None:
    init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        new_cols = [
            "rules_channel_id", "announcements_channel_id",
            "joins_channel_id", "leaves_channel_id",
            "verify_channel_id", "feedback_channel_id",
            "memes_channel_id", "clips_channel_id", "verified_role_id"
        ]
        for col in new_cols:
            try:
                await db.execute(f"ALTER TABLE guild_config ADD COLUMN {col} INTEGER")
            except Exception:
                pass
        for econ_col in ["last_daily", "last_weekly", "last_monthly"]:
            try:
                await db.execute(f"ALTER TABLE economy ADD COLUMN {econ_col} REAL DEFAULT 0")
            except Exception:
                pass
        await db.commit()

def save_clip_idea(idea_text: str, source: str = "Discord Remote") -> None:
    init_db()
    jst = pytz.timezone("Asia/Tokyo")
    now_str = datetime.datetime.now(jst).strftime("%b %d, %I:%M %p JST")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO idea_vault (timestamp, source, idea) VALUES (?, ?, ?)", (now_str, source, idea_text))
    conn.commit()
    conn.close()

def get_saved_ideas(limit: int = 10):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, timestamp, source, idea FROM idea_vault ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

def delete_idea(idea_id: int) -> None:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM idea_vault WHERE id = ?", (idea_id,))
    conn.commit()
    conn.close()

# ==========================================
# 1. STREAM SCHEDULE ENGINE (JST / GMT+9 ONLY)
# ==========================================
def get_next_stream_info() -> dict:
    jst = pytz.timezone("Asia/Tokyo")
    now_jst = datetime.datetime.now(jst)
    schedule = [
        (2, 21, 30, 165, "Wednesday Night Stream (9:30 PM - 12:15 AM) JST"),
        (5, 0, 15, 150, "Friday Late Night Stream (12:15 AM - 2:45 AM) JST"),
        (6, 17, 30, 150, "Sunday Evening Stream (5:30 PM - 8:00 PM) JST")
    ]
    upcoming = []
    for weekday, sh, sm, duration_mins, label in schedule:
        days_ahead = weekday - now_jst.weekday()
        start_time = (now_jst + datetime.timedelta(days=days_ahead)).replace(
            hour=sh, minute=sm, second=0, microsecond=0
        )
        end_time = start_time + datetime.timedelta(minutes=duration_mins)
        if start_time <= now_jst <= end_time:
            remaining = end_time - now_jst
            rem_h, rem_m = divmod(remaining.seconds // 60, 60)
            return {
                "status": "🟢 LIVE WINDOW NOW",
                "label": label,
                "next_date": "LIVE NOW (JST / GMT+9)",
                "countdown": f"In Broadcast Window! ({rem_h}h {rem_m}m left)"
            }
        if start_time < now_jst:
            start_time += datetime.timedelta(days=7)
        upcoming.append((start_time, label))

    upcoming.sort(key=lambda x: x[0])
    next_stream_time, next_label = upcoming[0]
    diff = next_stream_time - now_jst
    days = diff.days
    hours, remainder = divmod(diff.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return {
        "status": "UPCOMING",
        "label": next_label,
        "next_date": next_stream_time.strftime("%A, %b %d at %I:%M %p JST (GMT+9)"),
        "countdown": f"{days}d {hours}h {minutes}m"
    }

# ==========================================
# 2. REAL-TIME SOCIAL STATS (FAST NON-BLOCKING)
# ==========================================
def get_social_stats() -> dict:
    stats = {
        "twitch_channel": f"twitch.tv/{TWITCH_CHANNEL}",
        "twitch_status": "Offline",
        "twitch_viewers": 0,
        "twitch_followers": 0,
        "twitch_game": "VALORANT / osu!",
        "yt_handle": YOUTUBE_HANDLE,
        "yt_subscribers": 0,
        "yt_total_views": 0,
        "yt_video_count": 0,
        "ig_handle": IG_HANDLE
    }
    try:
        uptime_resp = requests.get(f"https://decapi.me/twitch/uptime/{TWITCH_CHANNEL}", timeout=2.5).text
        if "offline" not in uptime_resp.lower() and "error" not in uptime_resp.lower():
            stats["twitch_status"] = f"🟢 LIVE ({uptime_resp})"
            viewers = requests.get(f"https://decapi.me/twitch/viewercount/{TWITCH_CHANNEL}", timeout=2.5).text
            stats["twitch_viewers"] = int(viewers) if viewers.isdigit() else 0
            game = requests.get(f"https://decapi.me/twitch/game/{TWITCH_CHANNEL}", timeout=2.5).text
            stats["twitch_game"] = game
        follow_count = requests.get(f"https://decapi.me/twitch/followcount/{TWITCH_CHANNEL}", timeout=2.5).text
        if follow_count.isdigit():
            stats["twitch_followers"] = int(follow_count)
    except Exception:
        pass

    if YOUTUBE_API_KEY and YOUTUBE_API_KEY != "your_youtube_api_key":
        try:
            yt_url = f"https://www.googleapis.com/youtube/v3/channels?part=statistics,snippet&forHandle={YOUTUBE_HANDLE}&key={YOUTUBE_API_KEY}"
            resp = requests.get(yt_url, timeout=3.0).json()
            if "items" in resp and len(resp["items"]) > 0:
                yt_stats = resp["items"][0]["statistics"]
                stats["yt_subscribers"] = int(yt_stats.get("subscriberCount", 0))
                stats["yt_total_views"] = int(yt_stats.get("viewCount", 0))
                stats["yt_video_count"] = int(yt_stats.get("videoCount", 0))
        except Exception:
            pass
    return stats

# ==========================================
# 3. FAST VALORANT & OSU! TREND MINER
# ==========================================
def get_reddit_hot_topics(subreddit: str, limit: int = 2) -> list:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        url = f"https://www.reddit.com/r/{subreddit}/hot.rss"
        resp = requests.get(url, headers=headers, timeout=2.5)
        if resp.status_code == 200:
            root = ET.fromstring(resp.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            titles = []
            for entry in root.findall("atom:entry", ns):
                title = entry.find("atom:title", ns).text
                if not any(pin in title.lower() for pin in ["megathread", "daily", "weekly", "faq"]):
                    titles.append(title[:80])
                if len(titles) >= limit:
                    break
            if titles:
                return titles
    except Exception:
        pass
    if subreddit.lower() == "valorant":
        return ["Current Agent Meta & Duelist Entry Spacing", "Crosshair Placement & Micro-Adjustment Routine"]
    return ["High-BPM Stream Stamina & Rapid Trigger Setup", "Top Player PP Farm Beatmap Pack"]

def get_sns_trends_and_keywords() -> dict:
    val_hot = get_reddit_hot_topics("VALORANT", 2)
    osu_hot = get_reddit_hot_topics("osugame", 2)
    google_trends = ["VALORANT VCT Meta", "osu! PP Record", "Hall Effect Rapid Trigger", "Aim Transfer Routine", "1v5 Radiant Clutch"]

    return {
        "YouTube Long-Form (@NotAwwMian)": {
            "viral_topics": [
                f"[VALORANT Hot] {val_hot[0]}",
                f"[osu! Hot] {osu_hot[0]}",
                "Ranked Climb Comms & Highlights / 'How osu! Changed My VALORANT Aim'"
            ],
            "keywords": ["valorant", "osugame", "valorant ranked", "osu highlights", "aim routine", "notawwmian", "valorant montage", "rapid trigger"]
        },
        "YouTube Shorts (@NotAwwMian)": {
            "viral_topics": [
                "1v5 Clutch w/ Raw Mic Reaction",
                "osu! Handcam + Mechanical Keyboard ASMR on Fast Streams/Jumps",
                "Guess the Rank (Viewer Clip Roast in 45 Seconds)"
            ],
            "keywords": ["#valorantclips", "#osugame", "#valorantshorts", "#aimbot", "#streamerclips", "#handcam", "#gaming"]
        },
        "Instagram Reels (@awwmianlive)": {
            "viral_topics": [
                "POV: Whiffing an easy shot vs hitting a 180 one-tap (J-Pop/Phonk Audio)",
                "Desk Setup / IEM & Peripheral Check before Going Live on Twitch",
                "osu! Speed Map Split-Screen (Screen + Handcam Overlay)"
            ],
            "keywords": ["valorantclips", "osugame", "gamerpov", "awwmianlive", "twitchstreamer", "setupinspiration", "valorantgameplay"]
        },
        "Twitch Streams (Twitch.tv/AwwMian)": {
            "viral_topics": [
                f"[Community Meta] {val_hot[1] if len(val_hot)>1 else 'Agent Tier List Debate'}",
                f"[osu! Meta] {osu_hot[1] if len(osu_hot)>1 else 'Viewer Beatmap Requests (!bsr)'}",
                "Viewer 1v1s / Sub Custom Lobbies / Agent Roulette Challenge"
            ],
            "keywords": ["!sens", "!skin", "!profile", "Viewer Maps", "Ranked Grind", "1v1 Viewers", "Chill Vibes"]
        },
        "Live Web & Gaming Surges": google_trends
    }

# ==========================================
# 4. AI CONTENT PREDICTOR (GEMINI SDK)
# ==========================================
def generate_ideas_and_predictions(custom_focus: str = "VALORANT & osu!") -> str:
    trends = get_sns_trends_and_keywords()
    val_context = trends["YouTube Long-Form (@NotAwwMian)"]["viral_topics"][:2]
    prompt = f"""
    You are the personal viral producer for 'AwwMian' (Twitch: Twitch.tv/AwwMian, YouTube: @NotAwwMian, Instagram: @awwmianlive).
    Stream Schedule (Japan Time / GMT+9):
    - Wednesday Night: 9:30 PM - 12:15 AM JST
    - Friday Late Night: 12:15 AM - 2:45 AM JST
    - Sunday Evening: 5:30 PM - 8:00 PM JST
    Main Games: VALORANT and osu!
    Today's Focus: {custom_focus}
    Live VALORANT & osu! Hot Topics right now: {val_context}
    
    Generate an actionable, hype, pro-level content plan with:
    1. 🔴 1 YouTube Video Blueprint for @NotAwwMian (Click-worthy Title, Thumbnail visual layout, and first 10-second hook).
    2. ⚡ 2 Short-Form Ideas for @awwmianlive (IG Reels) & YT Shorts (specify exact audio vibe, visual hook, and caption).
    3. 🟣 1 Interactive Twitch Stream Segment for Twitch.tv/AwwMian's next JST broadcast that gets chat spamming.
    4. 🔮 14-DAY META PREDICTION: Predict the next viral crossover trend between rhythm games (osu!) and tactical shooters (VALORANT) and how to film it today.
    """
    if GEMINI_KEY and GEMINI_KEY != "your_gemini_key_here":
        try:
            client = genai.Client(api_key=GEMINI_KEY)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            return response.text
        except Exception as e:
            return f"⚠️ Gemini API Error: {e}"
    return "⚠️ Please verify your GEMINI_API_KEY in `.env` or Streamlit Secrets!"

def trigger_windows_stream_prep() -> list:
    launched = []
    try:
        webbrowser.open("https://dashboard.twitch.tv/u/AwwMian/stream-manager")
        launched.append("Twitch Stream Manager (AwwMian)")
        webbrowser.open("https://studio.youtube.com")
        launched.append("YouTube Studio (@NotAwwMian)")
        obs_paths = [
            r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
            r"C:\Program Files (x86)\obs-studio\bin\64bit\obs64.exe"
        ]
        for path in obs_paths:
            if os.path.exists(path):
                subprocess.Popen([path], cwd=os.path.dirname(path))
                launched.append("OBS Studio (64-bit)")
                break
    except Exception as e:
        launched.append(f"Cloud Mode Note: {e}")
    return launched