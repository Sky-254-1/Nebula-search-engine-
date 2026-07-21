"""Apply database migrations."""

import re
from pathlib import Path

from app.config import get_settings
from app.database.engine import connect

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


async def run_migrations() -> None:
    settings = get_settings()
    suffix = "postgres" if settings.uses_postgres else "sqlite"
    # Collect all migration files: suffixed + generic ones
    suffixed = sorted(MIGRATIONS_DIR.glob(f"*_{suffix}.sql"))
    generic = sorted(MIGRATIONS_DIR.glob("0[0-9][0-9]_*.sql"))
    # De-duplicate: if a generic file exists and a suffixed version exists, prefer suffixed
    existing_generic_stems = {p.stem for p in suffixed}
    files = list(suffixed)
    for p in generic:
        stem = p.stem
        # Map generic names to suffixed names to check
        base_stem = stem.split("_", 1)[-1] if "_" in stem and not stem.split("_")[0].isdigit() else stem
        if stem not in existing_generic_stems:
            files.append(p)
    files.sort()
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


def _is_add_column_statement(statement: str) -> bool:
    """Check if statement is an ALTER TABLE ADD COLUMN statement."""
    return bool(re.match(r"^\s*ALTER\s+TABLE\s+\w+\s+ADD\s+COLUMN\s+", statement, re.IGNORECASE))


async def _make_add_column_idempotent(db, statement: str) -> str | None:
    """
    For SQLite: Check if column exists before adding it.
    Returns the statement if it should be executed, or None if column already exists.
    """
    # Parse table name and column name from ALTER TABLE statement
    match = re.match(r"^\s*ALTER\s+TABLE\s+(\w+)\s+ADD\s+COLUMN\s+(\w+)", statement, re.IGNORECASE)
    if not match:
        return statement
    
    table_name = match.group(1)
    column_name = match.group(2)
    
    # Check if column already exists using PRAGMA table_info
    cursor = await db.execute(f"PRAGMA table_info({table_name})")
    columns = await cursor.fetchall()
    
    # PRAGMA table_info returns rows with: cid, name, type, notnull, dflt_value, pk
    column_exists = any(col[1] == column_name for col in columns)
    
    if column_exists:
        return None  # Skip this statement
    
    return statement


def _split_statements(sql: str) -> list[str]:
    statements = []
    buffer: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        buffer.append(line)
        if stripped.endswith(";"):
            statements.append("\n".join(buffer))
            buffer = []
    return statements
