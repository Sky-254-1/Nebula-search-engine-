#!/usr/bin/env python3
from pathlib import Path
import re

def main():
    print("🔧 Fixing migration system for popular_queries...\n")
    
    # Paths
    backend_dir = Path(__file__).parent.parent
    migrate_dir = backend_dir / "app" / "database" / "migrations"
    migrate_py_path = backend_dir / "app" / "database" / "migrate.py"
    
    # Check current files
    print("📋 Current migration files with 'popular_queries':")
    sql_files = sorted(migrate_dir.glob('*.sql'))
    popular_files = [f for f in sql_files if 'popular_queries' in f.name]
    
    for f in popular_files:
        print(f"  {f.name}")
    
    # Rename the files
    print("\n🔄 Renaming files to match pattern...")
    rename_mapping = {
        '011_popular_queries.sqlite.sql': '011_sqlite_popular_queries.sql',
        '011_popular_queries_postgres.sql': '011_postgres_popular_queries.sql',
    }
    
    for old_name, new_name in rename_mapping.items():
        old_path = migrate_dir / old_name
        new_path = migrate_dir / new_name
        
        if old_path.exists():
            old_path.rename(new_path)
            print(f"  ✓ Renamed: {old_name} -> {new_name}")
        else:
            print(f"  ✗ File not found: {old_path}")
    
    # Update migrate.py
    print("\n📝 Updating migrate.py...")
    migrate_content = migrate_py_path.read_text(encoding='utf-8')
    
    # Create the helper function
    helper_function = '''
def get_migration_files(migrations_dir, suffix):
    """Get migration files, handling popular_queries specially."""
    # Primary pattern: *_{suffix}.sql
    primary = sorted(migrations_dir.glob(f"*_{{\"{\" + \"suffix\" + \"}\"}}.sql"))
    
    # Secondary pattern for popular_queries: 0[0-9][0-9]*popular_queries*.sql
    secondary = sorted(migrations_dir.glob("0[0-9][0-9]*popular_queries*.sql"))
    
    # Combine and filter out duplicates
    combined = list(primary) + [f for f in secondary if f not in primary]
    
    print(f"Found {len(combined)} migration files for {suffix}: {[f.name for f in combined]}")
    return combined
'''
    
    # Replace the old logic with new function calls
    lines = migrate_content.split('\\n')
    updated_lines = []
    
    for line in lines:
        # Skip the old implementation
        if 'def run_migrations() -> None:' in line:
            # Add new imports and helper function
            updated_lines.append(line)
            updated_lines.append('')
            updated_lines.append(helper_function)
            updated_lines.append('')
        elif 'suffixed = sorted(MIGRATIONS_DIR.glob(f"*_\\{" + "suffix\" + \\"}.sql\\"))' in line:
            # Skip the old implementation
            continue
        elif 'files = list(suffixed)' in line:
            # Use the new function
            updated_lines.append('    files = get_migration_files(MIGRATIONS_DIR, suffix)')
        else:
            # Keep other lines
            updated_lines.append(line)
    
    # Write back
    migrate_py_path.write_text('\\n'.join(updated_lines), encoding='utf-8')
    print("  ✓ Updated migrate.py")
    
    # List all migration files
    print("\n📋 All migration files after update:")
    all_files = sorted(migrate_dir.glob('*.sql'))
    for f in all_files:
        print(f"  {f.name}")
    
    print("\n✅ Migration system fixed successfully!")
    print("\n📋 Next steps:")
    print("   1. Run migrations: python -m app.database.migrate")
    print("   2. Test autocomplete: python -m pytest tests/test_autocomplete.py::TestPopularQueries")
    print("   3. Run validation: python scripts/validate_production.py")

if __name__ == "__main__":
    main()
