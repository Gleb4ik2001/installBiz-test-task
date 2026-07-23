import os
import aiosqlite
from app.config import settings

async def init_db():
    db_dir = os.path.dirname(settings.DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE NOT NULL,
                downloaded_at TEXT NOT NULL,
                stats_json TEXT NOT NULL
            )
        """)
        await db.commit()

async def get_db():
    async with aiosqlite.connect(settings.DB_PATH) as db:
        yield db
