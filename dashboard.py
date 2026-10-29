import os
import sys
import hmac
import hashlib
import sqlite3
import subprocess
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv(override=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(
    page_title="AwwMian // Command Center",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="expanded"
)

def safe_get_secret(key: str, default: str = "") -> str:
    """Safely reads from .env or st.secrets without EVER throwing a Streamlit crash!"""
    val = os.getenv(key, "")
    if val:
        return val.strip().strip('"').strip("'")
    try:
        val = st.secrets.get(key, default)
        if val:
            os.environ[key] = str(val)
            return str(val).strip().strip('"').strip("'")
    except Exception:
        pass
    return default

# Pre-load cloud secrets into os.environ BEFORE importing core_engine
for _k in [
    "DISCORD_BOT_TOKEN", "GEMINI_API_KEY", "TWITCH_CLIENT_ID",
    "TWITCH_CLIENT_SECRET", "TWITCH_CHANNEL", "YOUTUBE_API_KEY",
    "YOUTUBE_CHANNEL_ID", "DASHBOARD_PASSKEY", "TWITTER_USERNAME"
]:
    safe_get_secret(_k)

import core_engine as engine
sys.modules["database"] = engine

@st.cache_resource
def ensure_cloud_bot_running():
    if sys.platform != "win32":
        try:
            return subprocess.Popen([sys.executable, "bot.py"], env=os.environ.copy())
        except Exception:
            return None
    return None

ensure_cloud_bot_running()

def verify_passkey(entered_password: str) -> bool:
    secret_target = safe_get_secret("DASHBOARD_PASSKEY", "IRIS@*6769@AwwMian2007#59255925")
    clean_input = entered_password.strip()
    input_hash = hashlib.sha256(clean_input.encode("utf-8")).hexdigest()
    target_hash = hashlib.sha256(secret_target.encode("utf-8")).hexdigest()
    return hmac.compare_digest(input_hash, target_hash)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono:wght@500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp {
        background: radial-gradient(circle at 10% 10%, #161124 0%, #0b0914 45%, #07060c 100%);
        color: #f8f9fa;
    }
    .hero-banner {
        background: linear-gradient(135deg, rgba(255, 70, 85, 0.16) 0%, rgba(157, 78, 221, 0.18) 50%, rgba(255, 102, 170, 0.15) 100%);
        border: 1px solid rgba(255, 102, 170, 0.35);
        border-radius: 18px;
        padding: 24px 30px;
        margin-bottom: 24px;
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.45);
    }
    .hero-title {
        font-size: 2.0rem;
        font-weight: 800;
        background: linear-gradient(90deg, #ff4655, #ff66aa, #c77dff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    .glass-card {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 18px 20px;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
    }
    .metric-label {
        color: #9d94b5;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 1.1px;
        font-weight: 600;
    }
    .metric-value {
        font-size: 1.65rem;
        font-weight: 800;
        color: #ffffff;
        margin: 4px 0;
        font-family: 'JetBrains Mono', monospace;
    }
    .metric-badge {
        display: inline-block;
        padding: 3px 9px;
        border-radius: 99px;
        font-size: 0.75rem;
        font-weight: 600;
        background: rgba(255, 102, 170, 0.15);
        color: #ff85bb;
    }
    .tag-pill {
        display: inline-block;
        background: rgba(157, 78, 221, 0.18);
        border: 1px solid rgba(157, 78, 221, 0.4);
        color: #e0aaff;
        padding: 4px 11px;
        border-radius: 999px;
        font-size: 0.78rem;
        margin: 3px 4px 3px 0;
        font-family: 'JetBrains Mono', monospace;
    }
</style>
""", unsafe_allow_html=True)

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    _, center_col, _ = st.columns([1, 1.4, 1])
    with center_col:
        st.write("")
        st.write("")
        st.markdown("""
        <div class="hero-banner" style="text-align:center;">
            <p class="hero-title">🔒 LIL MIAN // SECURITY GATE</p>
            <p style="color:#b8b2c8; margin-top:8px;">Encrypted Creator Command Center • Authorized Access Only (@awwmian)</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.container(border=True):
            pwd_input = st.text_input("🔑 Enter Master Passkey:", type="password", placeholder="••••••••••••••••••••••••")
            unlock_btn = st.button("🔓 Unlock Command Center", type="primary", use_container_width=True)
            
            if unlock_btn or pwd_input:
                if verify_passkey(pwd_input):
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("⛔ Invalid Master Passkey. Access Denied.")
    st.stop()

@st.cache_data(ttl=90, show_spinner=False)
def cached_social_stats():
    return engine.get_social_stats()

@st.cache_data(ttl=180, show_spinner=False)
def cached_trends():
    return engine.get_sns_trends_and_keywords()

def get_db_table(query: str, params=()):
    try:
        conn = sqlite3.connect(engine.DB_PATH)
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

sched = engine.get_next_stream_info()
stats = cached_social_stats()

st.markdown(f"""
<div class="hero-banner">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;">
        <div>
            <p class="hero-title">🌸 AWWMIAN // COMMAND CENTER v5.0</p>
            <p style="color:#b8b2c8; margin-top:6px;">VALORANT & osu! Content Intelligence • Discord Server Engine • Real-Time Telemetry (JST / GMT+9)</p>
        </div>
        <div style="text-align:right;">
            <span class="metric-badge">⏰ NEXT STREAM (JST): {sched['countdown']}</span>
            <div style="color:#e2d9f3; font-size:0.88rem; margin-top:6px;"><b>{sched['label']}</b><br>{sched['next_date']}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

df_xp = get_db_table("SELECT user_id, level, xp FROM user_xp ORDER BY level DESC, xp DESC")
df_econ = get_db_table("SELECT user_id, balance, bank, padlocks FROM economy ORDER BY (balance + bank) DESC")
total_miancoins = int((df_econ["balance"] + df_econ["bank"]).sum()) if not df_econ.empty else 0

c1, c2, c3, c4, c5 = st.columns(5)
cards = [
    (c1, "🟣 TWITCH STATUS", stats["twitch_status"], f"Playing: {stats['twitch_game']}"),
    (c2, "👥 TWITCH FOLLOWERS", f"{stats['twitch_followers']:,}", "twitch.tv/AwwMian"),
    (c3, "🔴 YOUTUBE (@NotAwwMian)", f"{stats['yt_subscribers']:,} Subs", f"{stats['yt_total_views']:,} Views • {stats['yt_video_count']} Vids"),
    (c4, "📸 INSTAGRAM & TWITTER", f"{stats['ig_handle']} • @{engine.TWITTER_USERNAME}", "Auto-Feeds Active"),
    (c5, "🌸 SERVER ECONOMY", f"{total_miancoins:,} Coins", f"{len(df_xp)} Ranked Discord Members")
]

for col, label, val, sub in cards:
    with col:
        st.markdown(f"""
        <div class="glass-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{val}</div>
            <span class="metric-badge">{sub}</span>
        </div>
        """, unsafe_allow_html=True)

st.write("")

tab_trends, tab_ai, tab_discord, tab_vault = st.tabs([
    "🔥 Viral Radar & SNS Keywords",
    "🧠 Gemini AI Producer & Predictor",
    "🏰 Lil Mian Discord Server Live DB",
    "💾 Synced Idea Vault"
])

with tab_trends:
    trends = cached_trends()
    st.markdown("**🌐 Live Japan / Global Search Surges:** " + " ".join([f"`{x}`" for x in trends["Live Web & Gaming Surges"]]))
    st.write("")
    col_a, col_b = st.columns(2)
    platforms = [
        ("▶️ YouTube Long-Form (@NotAwwMian)", trends["YouTube Long-Form (@NotAwwMian)"], col_a),
        ("⚡ YouTube Shorts (@NotAwwMian)", trends["YouTube Shorts (@NotAwwMian)"], col_a),
        ("📸 Instagram Reels (@awwmianlive)", trends["Instagram Reels (@awwmianlive)"], col_b),
        ("🟣 Twitch Broadcasts (Twitch.tv/AwwMian)", trends["Twitch Streams (Twitch.tv/AwwMian)"], col_b),
    ]
    for title, data, target_col in platforms:
        with target_col:
            with st.container(border=True):
                st.subheader(title)
                for topic in data["viral_topics"]:
                    st.markdown(f"- {topic}")
                pills_html = "".join([f'<span class="tag-pill">{k}</span>' for k in data["keywords"]])
                st.markdown(f"<div style='margin-top:10px;'>{pills_html}</div>", unsafe_allow_html=True)

with tab_ai:
    st.subheader("🔮 AI Viral Scriptwriter & 14-Day Meta Predictor")
    focus_col1, focus_col2 = st.columns([3, 1])
    with focus_col1:
        focus_input = st.text_input(
            "What VALORANT Agent, Challenge, or osu! Beatmap are you filming today?",
            value="VALORANT Ranked Clutches & osu! High-BPM Handcam"
        )
    with focus_col2:
        st.write("")
        st.write("")
        gen_btn = st.button("✨ Generate Viral Blueprint", type="primary", use_container_width=True)

    if gen_btn:
        with st.spinner("Analyzing live VALORANT & osu! meta velocity..."):
            report = engine.generate_ideas_and_predictions(focus_input)
            with st.container(border=True):
                st.markdown(report)

with tab_discord:
    d_col1, d_col2, d_col3 = st.columns(3)
    with d_col1:
        with st.container(border=True):
            st.subheader("🏆 XP Leaderboard")
            if df_xp.empty:
                st.caption("No XP logged yet. Chat in Discord to populate!")
            else:
                st.dataframe(df_xp, use_container_width=True, hide_index=True)
    with d_col2:
        with st.container(border=True):
            st.subheader("🌸 Richest MianCoin Holders")
            if df_econ.empty:
                st.caption("No MianCoins claimed yet. Chat or run `/daily` in Discord!")
            else:
                st.dataframe(df_econ, use_container_width=True, hide_index=True)
    with d_col3:
        with st.container(border=True):
            st.subheader("🛡️ Moderation Warnings")
            df_warn = get_db_table("SELECT id, user_id, reason, timestamp FROM warnings ORDER BY id DESC LIMIT 15")
            if df_warn.empty:
                st.success("✅ Zero active warnings in server!")
            else:
                st.dataframe(df_warn, use_container_width=True, hide_index=True)

with tab_vault:
    v_col1, v_col2 = st.columns([1, 2])
    with v_col1:
        with st.container(border=True):
            st.subheader("➕ Add New Content Idea")
            with st.form("dashboard_idea_form", clear_on_submit=True):
                new_idea = st.text_area("Video title, hook, or stream segment idea:")
                if st.form_submit_button("💾 Save to Vault", type="primary", use_container_width=True) and new_idea:
                    engine.save_clip_idea(new_idea, source="Web Dashboard")
                    st.rerun()
    with v_col2:
        st.subheader("📂 Saved Ideas (Synced with `/clip_idea`)")
        saved_ideas = engine.get_saved_ideas(limit=20)
        if not saved_ideas:
            st.info("No ideas saved yet! Use `/clip_idea` on Discord or add one on the left.")
        else:
            for idea_id, ts, src, text in saved_ideas:
                with st.container(border=True):
                    ic1, ic2 = st.columns([6, 1])
                    ic1.markdown(f"**{text}**")
                    ic1.caption(f"🕒 {ts} • Source: `{src}`")
                    if ic2.button("🗑️", key=f"del_{idea_id}"):
                        engine.delete_idea(idea_id)
                        st.rerun()

with st.sidebar:
    st.markdown("### 🌸 Lil Mian Control Deck")
    st.caption("🇯🇵 All schedules locked to **Japan Time (JST / GMT+9)**")
    st.markdown("""
    - **Wed Night:** `9:30 PM – 12:15 AM JST`
    - **Fri Late:** `12:15 AM – 2:45 AM JST`
    - **Sun Eve:** `5:30 PM – 8:00 PM JST`
    """)
    st.divider()
    if st.button("🔄 Refresh Live Telemetry", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    if st.button("🔒 Lock Dashboard", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()