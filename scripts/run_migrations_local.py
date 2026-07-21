#!/usr/bin/env python3
import asyncio
from pathlib import Path
import sys

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

async def main():
    try:
        from app.database.migrate import run_migrations
        await run_migrations()
        print("\n[SUCCESS] Migrations completed successfully!")
    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
