import os
import sys
import asyncio
sys.path.insert(0, ".")
os.environ["DATABASE_URL"] = "test_debug.db"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["APP_ENV"] = "testing"
from app.database import init_db
from app.config import get_settings
print("DB path:", get_settings().db_path)
asyncio.run(init_db())
import aiosqlite
async def check():
    conn = await aiosqlite.connect("test_debug.db")
    cursor = await conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
    rows = await cursor.fetchall()
    tables = [row[0] for row in rows]
    print("Tables after init_db:", tables)
    print("recent_searches exists:", "recent_searches" in tables)
    await conn.close()
asyncio.run(check())
os.remove("test_debug.db")
