"""Apply database migrations."""

from pathlib import Path

from app.config import get_settings
from app.database.engine import connect

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


async def run_migrations() -> None:
    settings = get_settings()
    filename = "001_postgres.sql" if settings.uses_postgres else "001_sqlite.sql"
    sql = (MIGRATIONS_DIR / filename).read_text(encoding="utf-8")
    db = await connect()
    try:
        for statement in _split_statements(sql):
            await db.execute(statement)
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
