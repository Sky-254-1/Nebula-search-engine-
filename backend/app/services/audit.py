"""Audit logging service for security events."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.config import get_settings
from app.database.repositories.audit import AuditRepository
from app.services.secrets import secrets_manager

settings = get_settings()
logger = logging.getLogger("nebula.audit")


class AuditService:
    """Service for auditing security-relevant events."""

    SECURITY_ACTIONS = {
        "login", "logout", "failed_login", "password_reset",
        "email_verification", "mfa_enabled", "mfa_disabled",
        "mfa_backup_code_used", "security_alert", "account_lockout",
        "session_termination", "permission_change", "role_change",
        "user_created", "user_deleted", "password_changed"
    }

    def __init__(self, db_connection=None):
        self._db_connection = db_connection
        self._audit_repo: Optional[AuditRepository] = None

    @property
    def audit_repo(self) -> AuditRepository:
        """Get audit repository instance."""
        if self._audit_repo is None:
            if self._db_connection is None:
                raise RuntimeError("Database connection not provided")
            self._audit_repo = AuditRepository(self._db_connection)
        return self._audit_repo

    async def log_event(
        self,
        action: str,
        user_id: Optional[int] = None,
        resource: Optional[str] = None,
        resource_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Log a security event to audit log."""
        if not settings.enable_audit_logs:
            return

        # Mask sensitive metadata
        masked_metadata = self._mask_metadata(metadata or {})

        await self.audit_repo.create_audit_event(
            user_id=user_id,
            session_id=session_id,
            action=action,
            resource_type=resource,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            error_message=error_message,
            metadata=masked_metadata,
        )

    async def log_security_event(
        self,
        action: str,
        user_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Log a security-relevant event with validation."""
        if action not in self.SECURITY_ACTIONS:
            logger.warning(f"Non-security action logged: {action}")

        await self.log_event(
            action=action,
            user_id=user_id,
            metadata=metadata,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            error_message=error_message,
            session_id=session_id,
        )

    async def log_auth_event(
        self,
        action: str,
        user_id: Optional[int] = None,
        email: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = "success",
        mfa_used: bool = False,
        login_method: str = "password",
        session_id: Optional[str] = None,
    ) -> None:
        """Log an authentication event."""
        metadata = {
            "login_method": login_method,
            "mfa_used": mfa_used,
        }
        if email:
            metadata["email"] = secrets_manager.mask(email)

        await self.log_security_event(
            action=action,
            user_id=user_id,
            metadata=metadata,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            session_id=session_id,
        )

    async def log_permission_change(
        self,
        user_id: int,
        changed_by: int,
        permission: str,
        new_value: bool,
        old_value: bool,
        resource: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """Log a permission change event."""
        metadata = {
            "permission": permission,
            "new_value": new_value,
            "old_value": old_value,
            "changed_by": changed_by,
        }

        await self.log_security_event(
            action="permission_change",
            user_id=user_id,
            resource=resource,
            metadata=metadata,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def _mask_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive fields in metadata."""
        sensitive_keys = {
            "password", "token", "secret", "key", "api_key", "api-key",
            "authorization", "bearer", "credential", "secret_key",
            "private_key", "encryption_key"
        }

        masked = {}
        for key, value in metadata.items():
            if isinstance(value, str):
                if any(sensitive in key.lower() for sensitive in sensitive_keys):
                    masked[key] = secrets_manager.mask(value)
                else:
                    masked[key] = value
            else:
                masked[key] = value

        return masked

    async def get_security_events(
        self,
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[int] = None,
        actions: Optional[list[str]] = None,
    ) -> list[Dict[str, Any]]:
        """Get recent security events."""
        from app.database.repositories.audit import AuditRepository
        # TODO: Implement actual database query with filters
        audit = AuditRepository(self._db_connection)
        return await audit.get_recent(limit=limit)


# Global instance
audit_service = AuditService()