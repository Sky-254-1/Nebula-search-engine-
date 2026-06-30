from app.database.engine import DatabaseConnection

class NotificationRepository:
    def __init__(self, db: DatabaseConnection):
        self.db = db

    async def create(self, user_id: int, title: str, body: str, type: str = "system") -> int:
        row = await self.db.fetchone(
            "INSERT INTO notifications (user_id, title, body, type) VALUES (?, ?, ?, ?) RETURNING id",
            (user_id, title, body, type),
        )
        return row["id"] if row else None

    async def list_for_user(self, user_id: int, limit: int = 50) -> list[dict]:
        return await self.db.fetchall(
            "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        )

    async def unread_count(self, user_id: int) -> int:
        row = await self.db.fetchone(
            "SELECT COUNT(*) as cnt FROM notifications WHERE user_id = ? AND read = 0",
            (user_id,),
        )
        return row["cnt"] if row else 0

    async def mark_read(self, notification_id: int, user_id: int) -> None:
        await self.db.execute(
            "UPDATE notifications SET read = 1 WHERE id = ? AND user_id = ?",
            (notification_id, user_id),
        )
        await self.db.commit()

    async def mark_all_read(self, user_id: int) -> None:
        await self.db.execute(
            "UPDATE notifications SET read = 1 WHERE user_id = ? AND read = 0",
            (user_id,),
        )
        await self.db.commit()

    async def delete(self, notification_id: int, user_id: int) -> None:
        await self.db.execute(
            "DELETE FROM notifications WHERE id = ? AND user_id = ?",
            (notification_id, user_id),
        )
        await self.db.commit()
