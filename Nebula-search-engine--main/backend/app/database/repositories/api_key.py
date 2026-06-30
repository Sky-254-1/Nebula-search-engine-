"""API key repository."""

from app.database.engine import DatabaseConnection


class APIKeyRepository:
    def __init__(self, db: DatabaseConnection):
        self._db = db

    async def create(self, user_id: int, hashed_key: str, key_prefix: str, name: str = "default") -> int:
        cursor = await self._db.execute(
            "INSERT INTO api_keys (user_id, hashed_key, key_prefix, name) VALUES (?, ?, ?, ?)",
            (user_id, hashed_key, key_prefix, name),
        )
        await self._db.commit()
        if hasattr(cursor, "lastrowid"):
            return cursor.lastrowid
        return 0

    async def list_for_user(self, user_id: int) -> list[dict]:
        rows = await self._db.fetchall(
            "SELECT id, key_prefix, name, last_used_at, expires_at, revoked, created_at "
            "FROM api_keys WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        return [dict(r) for r in rows]

    async def get_by_id(self, key_id: int, user_id: int):
        return await self._db.fetchone(
            "SELECT id, key_prefix, hashed_key, name, revoked FROM api_keys WHERE id = ? AND user_id = ?",
            (key_id, user_id),
        )

    async def get_by_hashed_key(self, hashed_key: str):
        return await self._db.fetchone(
            "SELECT id, user_id, key_prefix, name, revoked, expires_at FROM api_keys WHERE hashed_key = ?",
            (hashed_key,),
        )

    async def revoke(self, key_id: int, user_id: int) -> None:
        await self._db.execute(
            "UPDATE api_keys SET revoked = 1 WHERE id = ? AND user_id = ?",
            (key_id, user_id),
        )
        await self._db.commit()

    async def update_last_used(self, key_id: int) -> None:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        await self._db.execute(
            "UPDATE api_keys SET last_used_at = ? WHERE id = ?",
            (now, key_id),
        )
        await self._db.commit()
