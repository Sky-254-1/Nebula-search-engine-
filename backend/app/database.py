"""SQLite database connection and schema initialization."""

import aiosqlite

from app.config import get_settings

settings = get_settings()


async def get_db():
    """Yield an aiosqlite connection."""
    async with aiosqlite.connect(settings.db_path) as conn:
        conn.row_factory = aiosqlite.Row
        yield conn


async def init_db() -> None:
    """Create tables if they don't exist."""
    async with aiosqlite.connect(settings.db_path) as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS search_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                query TEXT NOT NULL,
                backend TEXT,
                results_count INTEGER DEFAULT 0,
                searched_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        await conn.commit()
