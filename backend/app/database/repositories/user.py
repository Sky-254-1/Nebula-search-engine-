"""User repository."""

from app.database.engine import DatabaseConnection


class UserRepository:
    def __init__(self, db: DatabaseConnection):
        self._db = db

    async def get_by_email(self, email: str):
        return await self._db.fetchone(
            "SELECT id, email, hashed_password FROM users WHERE email = ?",
            (email,),
        )

    async def create(self, email: str, hashed_password: str) -> None:
        await self._db.execute(
            "INSERT INTO users (email, hashed_password) VALUES (?, ?)",
            (email, hashed_password),
        )
        await self._db.commit()

    async def get_id_by_email(self, email: str) -> int | None:
        row = await self._db.fetchone("SELECT id FROM users WHERE email = ?", (email,))
        return row["id"] if row else None

    async def get_by_id(self, user_id: int):
        return await self._db.fetchone(
            "SELECT id, email, hashed_password FROM users WHERE id = ?",
            (user_id,),
        )
