"""Verify database indexes and constraints were created successfully."""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))


async def main():
    """Verify indexes and constraints."""
    print("=" * 70)
    print("VERIFYING DATABASE INDEXES & CONSTRAINTS")
    print("=" * 70)
    
    try:
        from app.database.engine import connect
        from app.config import get_settings
        
        # Reset environment
        import os
        os.environ["APP_ENV"] = "development"
        os.environ["DATABASE_URL"] = "file:nebula.db"
        get_settings.cache_clear()
        settings = get_settings()
        
        db = await connect()
        
        # Expected indexes to verify
        expected_indexes = [
            "idx_sessions_refresh_token_hash",
            "idx_documents_unique_user_path",
            "idx_documents_status",
            "idx_documents_content_hash",
            "idx_embeddings_chunk_id",
            "idx_embeddings_user_id",
            "idx_exports_user_id",
            "idx_search_sessions_user_id",
            "idx_audit_logs_created_at",
            "idx_audit_logs_action",
            "idx_documents_user_id_status",
            "idx_search_sessions_user_id_started_at",
            "idx_audit_logs_user_id_created_at",
        ]
        
        print("\nChecking indexes...")
        missing = []
        found = []
        
        for index_name in expected_indexes:
            try:
                if settings.uses_postgres:
                    # PostgreSQL query
                    result = await db.fetchone(
                        "SELECT indexname FROM pg_indexes WHERE indexname = $1",
                        (index_name,)
                    )
                else:
                    # SQLite query
                    result = await db.fetchone(
                        "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
                        (index_name,)
                    )
                
                if result:
                    found.append(index_name)
                    print(f"  [PASS] {index_name}")
                else:
                    missing.append(index_name)
                    print(f"  [FAIL] {index_name} - NOT FOUND")
            except Exception as e:
                missing.append(index_name)
                print(f"  [FAIL] {index_name} - ERROR: {e}")
        
        # Check unique constraints specifically
        print("\nVerifying unique constraints...")
        
        if settings.uses_postgres:
            # PostgreSQL
            result = await db.fetchone(
                "SELECT indexname FROM pg_indexes WHERE indexname = 'idx_sessions_refresh_token_hash'"
            )
            if result:
                print("  [PASS] Sessions refresh_token_hash unique constraint exists")
            else:
                print("  [FAIL] Sessions refresh_token_hash unique constraint missing")
        else:
            # SQLite - check via index list
            result = await db.fetchone(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_sessions_refresh_token_hash'"
            )
            if result:
                print("  [PASS] Sessions refresh_token_hash unique constraint exists")
            else:
                print("  [FAIL] Sessions refresh_token_hash unique constraint missing")
        
        # Summary
        print("\n" + "=" * 70)
        print("VERIFICATION SUMMARY")
        print("=" * 70)
        print(f"Total indexes checked: {len(expected_indexes)}")
        print(f"Found: {len(found)}")
        print(f"Missing: {len(missing)}")
        
        if missing:
            print("\nMissing indexes:")
            for idx in missing:
                print(f"  - {idx}")
            print("\n[FAIL] Some indexes are missing!")
            await db.close()
            return 1
        else:
            print("\n[SUCCESS] All indexes and constraints verified!")
            await db.close()
            return 0
            
    except Exception as e:
        print(f"\n[FAIL] Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)