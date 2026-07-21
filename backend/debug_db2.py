import os, sys, asyncio
sys.path.insert(0, ".")
os.environ["DATABASE_URL"] = "test_nebula.db"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["APP_ENV"] = "testing"
from app.config import get_settings
from app.database import init_db
print("DB path:", get_settings().db_path)
asyncio.run(init_db())
import aiosqlite
async def check():
    conn = await aiosqlite.connect("test_nebula.db")
    cursor = await conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
    rows = await cursor.fetchall()
    tables = [row[0] for row in rows]
    print("Tables:", tables)
    print("recent_searches:", "recent_searches" in tables)
    await conn.close()
asyncio.run(check())
