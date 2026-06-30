"""Search log repository."""

from app.database.engine import DatabaseConnection


class SearchRepository:
    def __init__(self, db: DatabaseConnection):
        self._db = db

    async def log_search(
        self,
        user_id: int | None,
        query: str,
        backend: str,
        results_count: int,
    ) -> None:
        await self._db.execute(
            "INSERT INTO search_logs (user_id, query, backend, results_count) VALUES (?, ?, ?, ?)",
            (user_id, query, backend, results_count),
        )
        await self._db.commit()

    async def recent_for_user(self, user_id: int, limit: int = 20) -> list[dict]:
        rows = await self._db.fetchall(
            "SELECT query, backend, results_count, searched_at FROM search_logs "
            "WHERE user_id = ? ORDER BY searched_at DESC LIMIT ?",
            (user_id, limit),
        )
        return [dict(row) for row in rows]
