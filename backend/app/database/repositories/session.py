"""Session (refresh token) repository."""

from datetime import datetime, timezone

from app.database.engine import DatabaseConnection


class SessionRepository:
    def __init__(self, db: DatabaseConnection):
        self._db = db

    async def create(self, user_id: int, refresh_token_hash: str, expires_at: datetime) -> None:
        await self._db.execute(
            "INSERT INTO sessions (user_id, refresh_token_hash, expires_at) VALUES (?, ?, ?)",
            (user_id, refresh_token_hash, expires_at.isoformat()),
        )
        await self._db.commit()

    async def get_by_hash(self, refresh_token_hash: str):
        return await self._db.fetchone(
            "SELECT id, user_id, expires_at FROM sessions WHERE refresh_token_hash = ?",
            (refresh_token_hash,),
        )

    async def delete(self, session_id: int) -> None:
        await self._db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        await self._db.commit()

    async def delete_expired(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self._db.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
        await self._db.commit()
