"""Mobile-specific backend extensions for Nebula Search Engine.

This package contains mobile-optimized API endpoints including:
- Bulk upload for efficient document management
- Batch notifications for real-time updates
- Offline sync for data synchronization
- Mobile authentication with JWT-based token management
"""

__version__ = "1.0.0"

from app.mobile.config import get_mobile_settings
from app.mobile.models import (
    BulkUploadRequest,
    BulkUploadResponse,
    BatchNotificationRequest,
    BatchNotificationResponse,
    OfflineSyncRequest,
    OfflineSyncResponse,
    DeviceRegistrationRequest,
    DeviceRegistrationResponse,
    MobileAuthRequest,
    MobileAuthResponse,
    MobileStatusResponse,
    MobileFeatureFlags,
)

__all__ = [
    "get_mobile_settings",
    "BulkUploadRequest",
    "BulkUploadResponse",
    "BatchNotificationRequest",
    "BatchNotificationResponse",
    "OfflineSyncRequest",
    "OfflineSyncResponse",
    "DeviceRegistrationRequest",
    "DeviceRegistrationResponse",
    "MobileAuthRequest",
    "MobileAuthResponse",
    "MobileStatusResponse",
    "MobileFeatureFlags",
]
