"""Document repository."""

from datetime import datetime, timezone

from app.database.engine import DatabaseConnection


class DocumentRepository:
    def __init__(self, db: DatabaseConnection):
        self._db = db

    async def create(
        self,
        user_id: int,
        filename: str,
        content_type: str | None,
        storage_path: str,
    ) -> int:
        await self._db.execute(
            "INSERT INTO documents (user_id, filename, content_type, storage_path) VALUES (?, ?, ?, ?)",
            (user_id, filename, content_type, storage_path),
        )
        await self._db.commit()
        row = await self._db.fetchone(
            "SELECT id FROM documents WHERE user_id = ? AND storage_path = ? ORDER BY id DESC LIMIT 1",
            (user_id, storage_path),
        )
        return row["id"] if row else 0

    async def list_for_user(self, user_id: int, limit: int = 50) -> list[dict]:
        rows = await self._db.fetchall(
            "SELECT id, filename, content_type, storage_path, indexed_at, created_at "
            "FROM documents WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        )
        return [dict(row) for row in rows]

    async def get_by_id(self, doc_id: int, user_id: int):
        return await self._db.fetchone(
            "SELECT id, filename, content_type, storage_path, indexed_at, created_at "
            "FROM documents WHERE id = ? AND user_id = ?",
            (doc_id, user_id),
        )

    async def delete(self, doc_id: int, user_id: int) -> bool:
        row = await self.get_by_id(doc_id, user_id)
        if not row:
            return False
        await self._db.execute("DELETE FROM documents WHERE id = ? AND user_id = ?", (doc_id, user_id))
        await self._db.commit()
        return True

    async def mark_indexed(self, doc_id: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self._db.execute("UPDATE documents SET indexed_at = ? WHERE id = ?", (now, doc_id))
        await self._db.commit()
