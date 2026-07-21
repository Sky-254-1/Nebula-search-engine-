import asyncio
import os
import sys
sys.path.insert(0, ".")
os.environ["DATABASE_URL"] = "test_verify.db"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["APP_ENV"] = "testing"
from app.database import init_db
from app.config import get_settings
print("DB path:", get_settings().db_path)
asyncio.run(init_db())
import aiosqlite
async def check():
    conn = await aiosqlite.connect("test_verify.db")
    cursor = await conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
    rows = await cursor.fetchall()
    print("Tables:", [row[0] for row in rows])
    await conn.close()
asyncio.run(check())
os.remove("test_verify.db")
