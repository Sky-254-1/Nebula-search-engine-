"""Saved search repository."""

from datetime import datetime, timezone

from app.config import get_settings
from app.database.engine import DatabaseConnection

settings = get_settings()
_TABLE = "search.saved_searches" if settings.uses_postgres else "saved_searches"


class SavedSearchRepository:
    def __init__(self, db: DatabaseConnection):
        self._db = db

    async def create(self, user_id: int, query: str, mode: str = "hybrid",
                     filters: dict | None = None, is_alert: bool = False) -> int:
        await self._db.execute(
            f"INSERT INTO {_TABLE} "
            "(user_id, query, mode, filters, is_alert) VALUES (?, ?, ?, ?, ?)",
            (user_id, query, mode, filters or {}, is_alert),
        )
        await self._db.commit()
        row = await self._db.fetchone(
            f"SELECT id FROM {_TABLE} WHERE user_id = ? AND query = ? "
            "AND is_deleted = FALSE ORDER BY id DESC LIMIT 1",
            (user_id, query),
        )
        return row["id"] if row else 0

    async def list_for_user(self, user_id: int, limit: int = 50) -> list[dict]:
        rows = await self._db.fetchall(
            f"SELECT id, query, mode, filters, is_alert, created_at, updated_at "
            f"FROM {_TABLE} WHERE user_id = ? AND is_deleted = FALSE "
            "ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        )
        return [dict(row) for row in rows]

    async def get_by_id(self, saved_id: int, user_id: int) -> dict | None:
        row = await self._db.fetchone(
            f"SELECT id, user_id, query, mode, filters, is_alert, created_at, updated_at "
            f"FROM {_TABLE} WHERE id = ? AND user_id = ? AND is_deleted = FALSE",
            (saved_id, user_id),
        )
        return dict(row) if row else None

    async def delete(self, saved_id: int, user_id: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self._db.execute(
            f"UPDATE {_TABLE} SET is_deleted = TRUE, deleted_at = ? "
            "WHERE id = ? AND user_id = ? AND is_deleted = FALSE",
            (now, saved_id, user_id),
        )
        await self._db.commit()
