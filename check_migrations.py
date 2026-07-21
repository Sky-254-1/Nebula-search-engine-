#!/usr/bin/env python3
from pathlib import Path

# Check migration files
migrations_dir = Path('backend/app/database/migrations')
sql_files = sorted(migrations_dir.glob('*.sql'))

print(f"Migration files ({len(sql_files)}):")
for f in sql_files:
    if 'popular_queries' in f.name:
        print(f"  {f.name}")

print('\nCurrent file names that need to be updated:')
for f in sql_files:
    if f.name.startswith('011_popular_queries.'):
        print(f"  {f.name}")