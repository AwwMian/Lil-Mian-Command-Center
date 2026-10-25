import time
import aiosqlite
from typing import Optional, Dict, Any, List, Tuple
from core_engine import DB_PATH, init_async_db

async def get_guild_config(guild_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def save_guild_config(guild_id: int, **kwargs: Any) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        existing = await get_guild_config(guild_id)
        if not existing:
            await db.execute("INSERT INTO guild_config (guild_id) VALUES (?)", (guild_id,))
        for col, val in kwargs.items():
            await db.execute(f"UPDATE guild_config SET {col} = ? WHERE guild_id = ?", (val, guild_id))
        await db.commit()

async def is_video_posted(video_id: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM posted_videos WHERE video_id = ?", (video_id,)) as cursor:
            return await cursor.fetchone() is not None

async def mark_video_posted(video_id: str, published_at: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO posted_videos (video_id, published_at) VALUES (?, ?)", (video_id, published_at))
        await db.commit()

async def add_warning(guild_id: int, user_id: int, moderator_id: int, reason: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO warnings (guild_id, user_id, moderator_id, reason) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, moderator_id, reason)
        )
        await db.commit()
        async with db.execute("SELECT COUNT(*) FROM warnings WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)) as cur:
            row = await cur.fetchone()
            return row[0] if row else 1

async def get_warnings(guild_id: int, user_id: int) -> List[Tuple[Any, ...]]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, moderator_id, reason, timestamp FROM warnings WHERE guild_id = ? AND user_id = ? ORDER BY id DESC",
            (guild_id, user_id)
        ) as cur:
            return await cur.fetchall()

async def get_balance(guild_id: int, user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT balance FROM economy WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)) as cur:
            row = await cur.fetchone()
            if not row:
                await db.execute("INSERT INTO economy (guild_id, user_id, balance) VALUES (?, ?, 100)", (guild_id, user_id))
                await db.commit()
                return 100
            return row[0]

async def update_balance(guild_id: int, user_id: int, amount_delta: int) -> int:
    current = await get_balance(guild_id, user_id)
    new_bal = max(0, current + amount_delta)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE economy SET balance = ? WHERE guild_id = ? AND user_id = ?", (new_bal, guild_id, user_id))
        await db.commit()
    return new_bal

async def claim_timed_reward(guild_id: int, user_id: int, period: str, reward: int, cooldown_seconds: int) -> Tuple[bool, int, int]:
    await get_balance(guild_id, user_id)
    now = time.time()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(f"SELECT balance, {period} FROM economy WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)) as cur:
            row = await cur.fetchone()
            bal = row[0] if row else 100
            try:
                last_claim = float(row[1]) if row and row[1] else 0.0
            except (ValueError, TypeError):
                last_claim = 0.0

        elapsed = now - last_claim
        if elapsed < cooldown_seconds:
            return False, int(cooldown_seconds - elapsed), reward

        new_bal = bal + reward
        await db.execute(
            f"UPDATE economy SET balance = ?, {period} = ? WHERE guild_id = ? AND user_id = ?",
            (new_bal, now, guild_id, user_id)
        )
        await db.commit()
        return True, new_bal, reward