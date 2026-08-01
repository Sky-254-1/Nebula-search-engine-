"""Mobile-specific configuration for backend extensions."""

from app.config import get_settings


class MobileSettings:
    """Mobile-specific configuration settings."""
    
    def __init__(self):
        self.settings = get_settings()
    
    @property
    def mobile_api_version(self) -> str:
        """Mobile API version."""
        return "v1"
    
    @property
    def mobile_prefix(self) -> str:
        """Mobile endpoint prefix."""
        return f"/api/{self.mobile_api_version}/mobile"
    
    @property
    def bulk_upload_max_files(self) -> int:
        """Maximum number of files for bulk upload."""
        return 50
    
    @property
    def bulk_upload_max_size_mb(self) -> int:
        """Maximum total size for bulk upload in MB."""
        return 100
    
    @property
    def batch_notifications_max_count(self) -> int:
        """Maximum number of notifications in a batch."""
        return 100
    
    @property
    def sync_batch_size(self) -> int:
        """Default batch size for offline sync."""
        return 100
    
    @property
    def sync_max_history_days(self) -> int:
        """Maximum days of history to sync."""
        return 30
    
    @property
    def mobile_jwt_expiry_minutes(self) -> int:
        """JWT expiry time for mobile clients (shorter for security)."""
        return 30
    
    @property
    def mobile_refresh_token_days(self) -> int:
        """Refresh token expiry for mobile clients."""
        return 7
    
    @property
    def offline_cache_ttl_hours(self) -> int:
        """TTL for offline cached data in hours."""
        return 24
    
    @property
    def document_cache_ttl_days(self) -> int:
        """TTL for cached documents in days."""
        return 30


def get_mobile_settings() -> MobileSettings:
    """Get mobile settings instance."""
    return MobileSettings()
