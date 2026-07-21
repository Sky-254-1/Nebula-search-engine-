#!/usr/bin/env python3
"""Script to fix migration file naming and update migration logic."""

import re
from pathlib import Path

def rename_migration_files(migrations_dir):
    """Rename popular_queries files to match pattern."""
    migrations_dir = Path(migrations_dir)
    
    # Files to rename
    old_to_new = {
        "011_popular_queries.sqlite.sql": "011_sqlite_popular_queries.sql",
        "011_popular_queries_postgres.sql": "011_postgres_popular_queries.sql",
    }
    
    for old_name, new_name in old_to_new.items():
        old_path = migrations_dir / old_name
        new_path = migrations_dir / new_name
        
        if old_path.exists():
            old_path.rename(new_path)
            print(f"✅ Renamed {old_name} -> {new_name}")
        else:
            print(f"⚠️  File not found: {old_path}")
    
    # List all migration files
    print("\n📋 Current migration files:")
    sql_files = sorted(migrations_dir.glob("*.sql"))
    for f in sql_files:
        print(f"  {f.name}")


def update_migrate_py(migrate_py_path):
    """Update migrate.py to handle popular_queries migrations."""
    migrate_py_path = Path(migrate_py_path)
    content = migrate_py_path.read_text(encoding='utf-8')
    
    # Check if the function already exists
    if "def get_migration_files" in content:
        print("✅ Migration logic already updated")
        return
    
    # Create the new functions
    new_functions = '''

def get_migration_files(migrations_dir, suffix):
    """Get migration files, handling popular_queries specially."""
    # Primary pattern: *_{suffix}.sql
    primary = sorted(migrations_dir.glob(f"*_{{{suffix}}}.sql"))
    # Secondary pattern for popular_queries: 0[0-9][0-9]*popular_queries*.sql
    secondary = sorted(migrations_dir.glob("0[0-9][0-9]*popular_queries*.sql"))
    # Combine and filter out duplicates
    combined = list(primary) + [f for f in secondary if f not in primary]
    print(f"Found {{len(combined)}} migration files for {{suffix}}: {{\n[type(f).__name__ for f in combined]}}")
    return combined

# Replace suffixed with custom function
def run_migrations():
    settings = get_settings()
    suffix = "postgres" if settings.uses_postgres else "sqlite"
    files = get_migration_files(MIGRATIONS_DIR, suffix)
    
    db = await connect()
    try:
        # Disable foreign key constraints for SQLite during migrations
        if not settings.uses_postgres:
            await db.execute("PRAGMA foreign_keys = OFF")
        
        for path in files:
            sql = path.read_text(encoding="utf-8")
            for statement in _split_statements(sql):
                # For SQLite, handle ALTER TABLE ADD COLUMN with idempotency check
                if not settings.uses_postgres and _is_add_column_statement(statement):
                    statement = await _make_add_column_idempotent(db, statement)
                    if statement is None:
                        # Column already exists, skip
                        continue
                try:
                    await db.execute(statement)
                except Exception as exc:
                    # Fallback: SQLite ALTER may fail if column already exists on re-run
                    error_msg = str(exc).lower()
                    if not settings.uses_postgres and ("duplicate column" in error_msg or "duplicate column name" in error_msg):
                        continue
                    raise
        
        # Re-enable foreign key constraints for SQLite after migrations
        if not settings.uses_postgres:
            await db.execute("PRAGMA foreign_keys = ON")
        
        await db.commit()
    finally:
        await db.close()
'''
    
    # Replace the main function
    lines = content.split('\n')
    updated_lines = []
    in_function = False
    replace_start = False
    replace_end = False
    
    for line in lines:
        if 'def run_migrations() -> None:' in line:
            in_function = True
            replace_start = True
            updated_lines.append(line)
        elif in_function and line.strip().startswith('    """Apply database migrations."""'):
            updated_lines.append(line)
        elif in_function and 'await run_migrations()' in line and 'self' in lines[lines.index(line) - 1]:
            continue
        elif in_function and replace_start and 'for path in files:' in line:
            # Replace the main function body with our new one
            updated_lines.append('    """Apply database migrations."""\n')
            updated_lines.append('    settings = get_settings()\n')
            updated_lines.append('    suffix = "postgres" if settings.uses_postgres else "sqlite"\n')
            updated_lines.append('    files = get_migration_files(MIGRATIONS_DIR, suffix)\n')
            updated_lines.append('\n')
            updated_lines.append('    db = await connect()\n')
            updated_lines.append('    try:\n')
            updated_lines.append('        # Disable foreign key constraints for SQLite during migrations\n')
            updated_lines.append('        if not settings.uses_postgres:\n')
            updated_lines.append('            await db.execute("PRAGMA foreign_keys = OFF")\n')
            updated_lines.append('\n')
            updated_lines.append('        for path in files:\n')
            updated_lines.append('            sql = path.read_text(encoding="utf-8")\n')
            updated_lines.append('            for statement in _split_statements(sql):\n')
            updated_lines.append('                # For SQLite, handle ALTER TABLE ADD COLUMN with idempotency check\n')
            updated_lines.append('                if not settings.uses_postgres and _is_add_column_statement(statement):\n')
            updated_lines.append('                    statement = await _make_add_column_idempotent(db, statement)\n')
            updated_lines.append('                    if statement is None:\n')
            updated_lines.append('                        # Column already exists, skip\n')
            updated_lines.append('                        continue\n')
            updated_lines.append('                try:\n')
            updated_lines.append('                    await db.execute(statement)\n')
            updated_lines.append('                except Exception as exc:\n')
            updated_lines.append('                    # Fallback: SQLite ALTER may fail if column already exists on re-run\n')
            updated_lines.append('                    error_msg = str(exc).lower()\n')
            updated_lines.append('                    if not settings.uses_postgres and ("duplicate column" in error_msg or "duplicate column name" in error_msg):\n')
            updated_lines.append('                        continue\n')
            updated_lines.append('                    raise\n')
            updated_lines.append('        \n')
            updated_lines.append('        # Re-enable foreign key constraints for SQLite after migrations\n')
            updated_lines.append('        if not settings.uses_postgres:\n')
            updated_lines.append('            await db.execute("PRAGMA foreign_keys = ON")\n')
            updated_lines.append('        \n')
            updated_lines.append('        await db.commit()\n')
            updated_lines.append('    finally:\n')
            updated_lines.append('        await db.close()\n')
            
            replace_start = False
            replace_end = True
        elif not in_function or replace_end:
            if replace_end and line.strip() == '':
                replace_end = False
            updated_lines.append(line)
        elif in_function and not replace_start and not replace_end:
            # Skip the original function body
            if line.strip().startswith(('try:', 'await run_migrations()', 'files = list(suffixed)')):
                continue
            elif line.strip() == 'db = await connect()' or line.strip().startswith('for path in files:'):
                continue
            elif line.strip() == 'await db.commit()' or line.strip() == 'finally:' or 'await db.close()' in line:
                continue
            updated_lines.append(line)
    
    # Add the new functions at the end
    updated_content = '\n'.join(updated_lines) + '\n\n' + new_functions
    
    # Write back to file
    migrate_py_path.write_text(updated_content, encoding='utf-8')
    print("✅ Updated backend/app/database/migrate.py")


def main():
    print("🔧 Fixing migration system for popular_queries support\n")
    
    # Paths
    backend_dir = Path(__file__).parent.parent
    migrate_dir = backend_dir / "app" / "database" / "migrations"
    migrate_py_path = backend_dir / "app" / "database" / "migrate.py"
    
    # Rename migration files
    rename_migration_files(migrate_dir)
    
    # Update migrate.py
    update_migrate_py(migrate_py_path)
    
    print("\n✅ Migration system fixed successfully!")
    print("\n📋 Next steps:")
    print("   1. Run migrations: python -m app.database.migrate")
    print("   2. Test autocomplete: python -m pytest tests/test_autocomplete.py::TestPopularQueries")
    print("   3. Run validation: python scripts/validate_production.py")


if __name__ == "__main__":
    main()
