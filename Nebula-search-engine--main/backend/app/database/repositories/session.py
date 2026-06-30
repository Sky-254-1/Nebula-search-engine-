"""Session (refresh token) repository."""

from datetime import datetime, timezone

from app.database.engine import DatabaseConnection


class SessionRepository:
    def __init__(self, db: DatabaseConnection):
        self._db = db

    async def create(
        self,
        user_id: int,
        refresh_token_hash: str,
        expires_at: datetime,
        session_id: str | None = None,
        device_name: str | None = None,
        parent_refresh_id: int | None = None,
    ) -> int:
        from app.config import get_settings
        settings = get_settings()

        params = (
            user_id,
            refresh_token_hash,
            expires_at.isoformat(),
            session_id,
            device_name,
            parent_refresh_id,
        )

        if settings.uses_postgres:
            sql = """INSERT INTO sessions
                (user_id, refresh_token_hash, expires_at, session_id, device_name, parent_refresh_id)
                VALUES (?, ?, ?, ?, ?, ?) RETURNING id"""
            row = await self._db.fetchone(sql, params)
            await self._db.commit()
            return row["id"] if row else 0

        sql = """INSERT INTO sessions
            (user_id, refresh_token_hash, expires_at, session_id, device_name, parent_refresh_id)
            VALUES (?, ?, ?, ?, ?, ?)"""
        cursor = await self._db.execute(sql, params)
        await self._db.commit()

        if hasattr(cursor, "lastrowid"):
            return cursor.lastrowid
        return 0

    async def get_by_hash(self, refresh_token_hash: str):
        return await self._db.fetchone(
            """SELECT id, user_id, expires_at, session_id, device_name,
            parent_refresh_id, rotated_at, revoked_reason
            FROM sessions WHERE refresh_token_hash = ?""",
            (refresh_token_hash,),
        )

    async def delete(self, session_id: int) -> None:
        await self._db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        await self._db.commit()

    async def delete_by_session_id(self, session_id: str) -> None:
        await self._db.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        await self._db.commit()

    async def delete_all_for_user(self, user_id: int) -> None:
        await self._db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        await self._db.commit()

    async def revoke_session_family(self, session_id: str, reason: str) -> None:
        await self._db.execute(
            "UPDATE sessions SET revoked_reason = ? WHERE session_id = ?",
            (reason, session_id),
        )
        await self._db.commit()

    async def update_rotation(self, session_id: int, rotated_at: datetime) -> None:
        await self._db.execute(
            "UPDATE sessions SET rotated_at = ? WHERE id = ?",
            (rotated_at.isoformat(), session_id),
        )
        await self._db.commit()

    async def update_last_seen(self, session_id: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self._db.execute(
            "UPDATE sessions SET last_seen = ? WHERE id = ?",
            (now, session_id),
        )
        await self._db.commit()

    async def list_for_user(self, user_id: int, limit: int = 50) -> list[dict]:
        rows = await self._db.fetchall(
            """SELECT id, session_id, device_name, expires_at, rotated_at, revoked_reason, created_at
            FROM sessions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?""",
            (user_id, limit),
        )
        return [dict(r) for r in rows]

    async def delete_expired(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self._db.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
        await self._db.commit()
