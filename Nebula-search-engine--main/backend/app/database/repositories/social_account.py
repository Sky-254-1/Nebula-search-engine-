"""Social account repository for OAuth2-linked accounts."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from app.database.engine import DatabaseConnection


class SocialAccountRepository:
    def __init__(self, db: DatabaseConnection):
        self._db = db

    async def get_by_provider_and_user_id(self, provider: str, provider_user_id: str):
        return await self._db.fetchone(
            "SELECT id, user_id, provider, provider_user_id, provider_email, "
            "display_name, avatar_url, access_token, refresh_token, token_expires_at "
            "FROM social_accounts WHERE provider = ? AND provider_user_id = ?",
            (provider, provider_user_id),
        )

    async def get_by_user_id(self, user_id: int):
        return await self._db.fetchall(
            "SELECT id, provider, provider_user_id, provider_email, display_name, "
            "avatar_url, created_at FROM social_accounts WHERE user_id = ? "
            "ORDER BY created_at DESC",
            (user_id,),
        )

    async def get_by_provider_and_email(self, provider: str, email: str):
        return await self._db.fetchone(
            "SELECT id, user_id, provider, provider_user_id FROM social_accounts "
            "WHERE provider = ? AND provider_email = ?",
            (provider, email),
        )

    async def create(
        self,
        user_id: int,
        provider: str,
        provider_user_id: str,
        provider_email: Optional[str] = None,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        expires_in: Optional[int] = None,
    ) -> None:
        token_expires_at = None
        if expires_in:
            token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        await self._db.execute(
            "INSERT INTO social_accounts "
            "(user_id, provider, provider_user_id, provider_email, display_name, "
            " avatar_url, access_token, refresh_token, token_expires_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                user_id, provider, provider_user_id, provider_email,
                display_name, avatar_url, access_token, refresh_token,
                token_expires_at.isoformat() if token_expires_at else None,
            ),
        )
        await self._db.commit()

    async def update_tokens(
        self,
        social_account_id: int,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_in: Optional[int] = None,
    ) -> None:
        token_expires_at = None
        if expires_in:
            token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        await self._db.execute(
            "UPDATE social_accounts SET access_token = ?, refresh_token = ?, "
            "token_expires_at = ?, updated_at = ? WHERE id = ?",
            (
                access_token,
                refresh_token,
                token_expires_at.isoformat() if token_expires_at else None,
                datetime.now(timezone.utc).isoformat(),
                social_account_id,
            ),
        )
        await self._db.commit()

    async def delete(self, social_account_id: int) -> None:
        await self._db.execute(
            "DELETE FROM social_accounts WHERE id = ?",
            (social_account_id,),
        )
        await self._db.commit()

    async def get_linked_email_by_provider(self, user_id: int, provider: str) -> Optional[str]:
        row = await self._db.fetchone(
            "SELECT provider_email FROM social_accounts WHERE user_id = ? AND provider = ?",
            (user_id, provider),
        )
        return row["provider_email"] if row else None
