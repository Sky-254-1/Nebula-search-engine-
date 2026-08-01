"""Pydantic models for mobile-specific API requests and responses."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ==================== Request Models ====================

class BulkUploadRequest(BaseModel):
    """Request model for bulk document upload."""
    files: List[str] = Field(
        ...,
        description="List of file metadata including name, size, and content_type"
    )
    folder_id: Optional[int] = Field(None, description="Target folder ID")
    notify_on_complete: bool = Field(True, description="Send notification on completion")


class BulkUploadResponse(BaseModel):
    """Response model for bulk upload."""
    upload_id: str = Field(..., description="Unique upload session ID")
    total_files: int = Field(..., description="Total number of files")
    success_count: int = Field(..., description="Number of successfully uploaded files")
    failed_count: int = Field(..., description="Number of failed uploads")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Error details")


class BatchNotificationRequest(BaseModel):
    """Request model for batch notification creation."""
    notifications: List[Dict[str, Any]] = Field(
        ...,
        description="List of notification objects"
    )
    priority: str = Field("normal", description="Notification priority: normal, high, urgent")


class BatchNotificationResponse(BaseModel):
    """Response model for batch notification creation."""
    batch_id: str = Field(..., description="Batch ID")
    total_created: int = Field(..., description="Total notifications created")
    failed: int = Field(..., description="Number of failed creations")
    details: List[Dict[str, Any]] = Field(default_factory=list)


class OfflineSyncRequest(BaseModel):
    """Request model for offline sync."""
    last_sync: Optional[datetime] = Field(None, description="Last sync timestamp")
    device_id: str = Field(..., description="Device identifier")
    sync_type: str = Field("incremental", description="Sync type: full or incremental")
    include_types: List[str] = Field(
        default_factory=lambda: ["documents", "notifications", "search_history"],
        description="Types of data to sync"
    )


class OfflineSyncResponse(BaseModel):
    """Response model for offline sync."""
    sync_id: str = Field(..., description="Sync session ID")
    last_sync: datetime = Field(..., description="Current sync timestamp")
    data: Dict[str, Any] = Field(default_factory=dict, description="Synced data")
    has_more: bool = Field(..., description="Whether more data is available")
    cursor: Optional[str] = Field(None, description="Cursor for pagination")


class DeviceRegistrationRequest(BaseModel):
    """Request model for device registration."""
    device_id: str = Field(..., description="Unique device identifier")
    device_name: Optional[str] = Field(None, description="User-friendly device name")
    device_type: str = Field("mobile", description="Device type: mobile, tablet")
    platform: str = Field("ios", description="Platform: ios, android")
    push_token: Optional[str] = Field(None, description="Push notification token")
    app_version: str = Field("1.0.0", description="App version")


class DeviceRegistrationResponse(BaseModel):
    """Response model for device registration."""
    device_id: str = Field(..., description="Registered device ID")
    registered_at: datetime = Field(..., description="Registration timestamp")
    active: bool = Field(True, description="Device is active")


class MobileAuthRequest(BaseModel):
    """Request model for mobile authentication."""
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")
    device_info: Optional[Dict[str, str]] = Field(None, description="Device information")


class MobileAuthResponse(BaseModel):
    """Response model for mobile authentication."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    expires_at: datetime = Field(..., description="Token expiry time")
    user: Dict[str, Any] = Field(..., description="User profile data")


# ==================== Response Models ====================

class MobileStatusResponse(BaseModel):
    """Response model for mobile status check."""
    status: str = Field("healthy", description="Service status")
    mobile_api_version: str = Field(..., description="Mobile API version")
    features: List[str] = Field(default_factory=list, description="Enabled features")
    offline_enabled: bool = Field(True, description="Offline mode enabled")


class MobileFeatureFlags(BaseModel):
    """Response model for feature flags."""
    offline_sync: bool = Field(True, description="Offline sync enabled")
    bulk_upload: bool = Field(True, description="Bulk upload enabled")
    batch_notifications: bool = Field(True, description="Batch notifications enabled")
    device_registration: bool = Field(True, description="Device registration enabled")
    rate_limits: Dict[str, Any] = Field(default_factory=dict, description="Rate limit configuration")
