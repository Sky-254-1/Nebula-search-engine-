"""Search click tracking repository."""

from app.database.engine import DatabaseConnection


class SearchClickRepository:
    def __init__(self, db: DatabaseConnection):
        self._db = db

    async def record_click(
        self,
        user_id: int | None,
        query: str,
        result_url: str,
        result_title: str | None = None,
        result_position: int | None = None,
        backend: str | None = None,
        search_log_id: int | None = None,
    ) -> int:
        cursor = await self._db.execute(
            "INSERT INTO search_clicks (user_id, search_log_id, query, result_url, result_title, result_position, backend) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, search_log_id, query, result_url, result_title, result_position, backend),
        )
        await self._db.commit()
        if hasattr(cursor, "lastrowid"):
            return cursor.lastrowid
        return 0
