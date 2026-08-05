"""Run database migrations."""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))


async def main():
    """Run database migrations."""
    print("=" * 60)
    print("RUNNING DATABASE MIGRATIONS")
    print("=" * 60)
    
    try:
        from app.database.migrate import run_migrations
        await run_migrations()
        print("\n[SUCCESS] Migrations completed successfully!")
        return 0
    except Exception as e:
        print(f"\n[FAIL] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)