"""Audit log repository."""

import json
from typing import Any

from app.database.engine import DatabaseConnection


class AuditRepository:
    def __init__(self, db: DatabaseConnection):
        self._db = db

    async def create(
        self,
        user_id: int | None,
        action: str,
        resource: str | None = None,
        metadata: dict[str, Any] | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        await self._db.execute(
            """INSERT INTO audit_logs
            (user_id, action, resource, metadata_json, ip, user_agent)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                action,
                resource,
                json.dumps(metadata or {}),
                ip,
                user_agent,
            ),
        )
        await self._db.commit()

    async def get_recent(self, limit: int = 100):
        return await self._db.fetchall(
            "SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )

    async def get_for_user(self, user_id: int, limit: int = 100):
        return await self._db.fetchall(
            "SELECT * FROM audit_logs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        )

    async def delete_old_logs(self, days: int = 90) -> None:
        """Delete audit logs older than N days."""
        # SQLite uses datetime('now', '-N days')
        # Postgres uses CURRENT_TIMESTAMP - INTERVAL 'N days'
        from app.config import get_settings
        settings = get_settings()
        if settings.uses_postgres:
            sql = "DELETE FROM audit_logs WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '? days'"
        else:
            sql = "DELETE FROM audit_logs WHERE created_at < datetime('now', '-? days')"
        await self._db.execute(sql, (days,))
        await self._db.commit()
