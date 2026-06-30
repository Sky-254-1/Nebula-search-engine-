"""Apply database migrations."""

from pathlib import Path

from app.config import get_settings
from app.database.engine import connect

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


async def run_migrations() -> None:
    settings = get_settings()
    suffix = "postgres" if settings.uses_postgres else "sqlite"
    files = sorted(MIGRATIONS_DIR.glob(f"*_{suffix}.sql"))
    db = await connect()
    try:
        for path in files:
            sql = path.read_text(encoding="utf-8")
            for statement in _split_statements(sql):
                try:
                    await db.execute(statement)
                except Exception as exc:
                    # SQLite ALTER may fail if column already exists on re-run
                    if "duplicate column" in str(exc).lower():
                        continue
                    raise
        await db.commit()
    finally:
        await db.close()


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
