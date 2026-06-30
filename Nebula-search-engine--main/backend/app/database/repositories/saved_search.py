from app.database.engine import DatabaseConnection

class SavedSearchRepository:
    def __init__(self, db: DatabaseConnection):
        self.db = db

    async def create(self, user_id: int, query: str, filters: dict, label: str | None = None) -> int:
        row = await self.db.fetchone(
            "INSERT INTO saved_searches (user_id, query, filters, label) VALUES (?, ?, ?, ?) RETURNING id",
            (user_id, query, str(filters) if filters else "{}", label),
        )
        return row["id"] if row else None

    async def list_for_user(self, user_id: int) -> list[dict]:
        return await self.db.fetchall(
            "SELECT * FROM saved_searches WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )

    async def get_by_id(self, search_id: int, user_id: int) -> dict | None:
        return await self.db.fetchone(
            "SELECT * FROM saved_searches WHERE id = ? AND user_id = ?",
            (search_id, user_id),
        )

    async def delete(self, search_id: int, user_id: int) -> None:
        await self.db.execute(
            "DELETE FROM saved_searches WHERE id = ? AND user_id = ?",
            (search_id, user_id),
        )
        await self.db.commit()
