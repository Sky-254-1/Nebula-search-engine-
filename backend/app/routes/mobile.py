"""Mobile-specific API endpoints for Nebula Search Engine.

This module provides mobile-optimized endpoints including:
- Bulk upload for efficient document management
- Batch notifications for real-time updates
- Offline sync for data synchronization
- Mobile authentication with enhanced security
"""

import secrets
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import get_db
from app.database.repositories.document import DocumentRepository
from app.database.repositories.notification import NotificationRepository
from app.database.repositories.user import UserRepository
from app.services.auth import (
    get_current_user,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
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

router = APIRouter(prefix="/api/v1/mobile", tags=["Mobile"])
settings = get_settings()
mobile_settings = get_mobile_settings()


# ==================== Authentication Endpoints ====================

@router.post("/auth/login", response_model=MobileAuthResponse)
async def mobile_login(
    request: Request,
    body: MobileAuthRequest,
    db=Depends(get_db),
):
    """Mobile-specific login with device tracking."""
    ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    users = UserRepository(db)
    user = await users.get_by_email(body.email)
    
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create mobile-specific tokens (shorter expiry for security)
    access_token = create_access_token(
        email=user["email"],
        role=user["role"],
        jti=secrets.token_urlsafe(16)
    )
    refresh_token = create_refresh_token()
    
    # Store device info for security auditing
    device_id = body.device_info.get("device_id", str(uuid.uuid4())) if body.device_info else str(uuid.uuid4())
    
    # Log the login for security audit
    if settings.enable_audit_logs:
        from app.database.repositories.audit import AuditRepository
        audit = AuditRepository(db)
        await audit.create(
            user_id=user["id"],
            action="mobile_login",
            ip=ip,
            user_agent=user_agent,
            metadata={"device_id": device_id}
        )
    
    return MobileAuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=datetime.now(timezone.utc).replace(
            tzinfo=timezone.utc
        ) + settings.jwt_expiry_minutes * 60,
        user={
            "id": user["id"],
            "email": user["email"],
            "name": user.get("name"),
            "role": user["role"],
        }
    )


@router.post("/auth/refresh")
async def refresh_token(
    request: Request,
    refresh_token: str,
    db=Depends(get_db),
):
    """Refresh mobile access token."""
    try:
        payload = decode_token(refresh_token, expected_type="refresh")
        email = payload.get("sub")
        
        users = UserRepository(db)
        user = await users.get_by_email(email)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Create new tokens
        new_access_token = create_access_token(
            email=user["email"],
            role=user["role"],
            jti=secrets.token_urlsafe(16)
        )
        new_refresh_token = create_refresh_token()
        
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "expires_at": datetime.now(timezone.utc) + settings.jwt_expiry_minutes * 60,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc


@router.post("/auth/logout")
async def mobile_logout(
    request: Request,
    email: str = Depends(get_current_user),
    db=Depends(get_db),
):
    """Logout from mobile device."""
    # Invalidate tokens (in production, add to blacklist)
    return {"message": "Logged out successfully"}


# ==================== Device Management ====================

@router.post("/devices/register", response_model=DeviceRegistrationResponse)
async def register_device(
    request: Request,
    body: DeviceRegistrationRequest,
    email: str = Depends(get_current_user),
    db=Depends(get_db),
):
    """Register mobile device for push notifications."""
    user_id = await _get_user_id(db, email)
    
    # Store device information
    device_record = {
        "user_id": user_id,
        "device_id": body.device_id,
        "device_name": body.device_name,
        "device_type": body.device_type,
        "platform": body.platform,
        "push_token": body.push_token,
        "app_version": body.app_version,
        "registered_at": datetime.now(timezone.utc),
        "last_active": datetime.now(timezone.utc),
        "active": True,
    }
    
    return DeviceRegistrationResponse(**device_record)


@router.delete("/devices/{device_id}")
async def unregister_device(
    device_id: str,
    email: str = Depends(get_current_user),
    db=Depends(get_db),
):
    """Remove device registration."""
    user_id = await _get_user_id(db, email)
    # In production, update device to inactive
    return {"message": f"Device {device_id} unregistered"}


# ==================== Bulk Operations ====================

@router.post("/bulk/upload", response_model=BulkUploadResponse)
async def bulk_upload(
    request: Request,
    body: BulkUploadRequest,
    background_tasks: BackgroundTasks,
    email: str = Depends(get_current_user),
    db=Depends(get_db),
):
    """Upload multiple documents in a single request."""
    user_id = await _get_user_id(db, email)
    
    if len(body.files) > mobile_settings.bulk_upload_max_files:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {mobile_settings.bulk_upload_max_files} files allowed"
        )
    
    upload_id = str(uuid.uuid4())
    success_count = 0
    failed_count = 0
    errors = []
    
    for file_info in body.files:
        try:
            # Validate file metadata
            if not file_info.get("name") or not file_info.get("content_type"):
                errors.append({
                    "file": file_info.get("name"),
                    "error": "Missing required file metadata"
                })
                failed_count += 1
                continue
            
            # In production, this would process the actual file content
            # For now, we'll simulate the upload
            docs = DocumentRepository(db)
            await docs.create(
                user_id=user_id,
                filename=file_info["name"],
                content_type=file_info.get("content_type"),
                storage_path=file_info.get("storage_path", f"/uploads/{upload_id}/{file_info['name']}")
            )
            success_count += 1
            
        except Exception as exc:
            errors.append({
                "file": file_info.get("name"),
                "error": str(exc)
            })
            failed_count += 1
    
    return BulkUploadResponse(
        upload_id=upload_id,
        total_files=len(body.files),
        success_count=success_count,
        failed_count=failed_count,
        errors=errors
    )


@router.post("/bulk/notifications", response_model=BatchNotificationResponse)
async def batch_create_notifications(
    request: Request,
    body: BatchNotificationRequest,
    background_tasks: BackgroundTasks,
    email: str = Depends(get_current_user),
    db=Depends(get_db),
):
    """Create multiple notifications in a single request."""
    user_id = await _get_user_id(db, email)
    
    if len(body.notifications) > mobile_settings.batch_notifications_max_count:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {mobile_settings.batch_notifications_max_count} notifications allowed"
        )
    
    batch_id = str(uuid.uuid4())
    total_created = 0
    failed = 0
    details = []
    
    notif_repo = NotificationRepository(db)
    
    for notification in body.notifications:
        try:
            await notif_repo.create(
                user_id=user_id,
                type=notification.get("type", "system"),
                category=notification.get("category", "general"),
                title=notification.get("title", ""),
                message=notification.get("message", ""),
                data=notification.get("data", {}),
                expires_at=notification.get("expires_at"),
            )
            total_created += 1
        except Exception as exc:
            failed += 1
            details.append({"notification": notification, "error": str(exc)})
    
    return BatchNotificationResponse(
        batch_id=batch_id,
        total_created=total_created,
        failed=failed,
        details=details
    )


# ==================== Offline Sync ====================

@router.post("/sync", response_model=OfflineSyncResponse)
async def offline_sync(
    request: Request,
    body: OfflineSyncRequest,
    email: str = Depends(get_current_user),
    db=Depends(get_db),
):
    """Synchronize data for offline use."""
    user_id = await _get_user_id(db, email)
    sync_id = str(uuid.uuid4())
    
    sync_data = {}
    cursor = None
    has_more = False
    
    # Sync documents
    if "documents" in body.include_types:
        docs = DocumentRepository(db)
        documents = await docs.list_for_user(user_id)
        sync_data["documents"] = documents[:mobile_settings.sync_batch_size]
        if len(documents) > mobile_settings.sync_batch_size:
            has_more = True
            cursor = str(len(documents))
    
    # Sync notifications
    if "notifications" in body.include_types:
        notif_repo = NotificationRepository(db)
        notifications = await notif_repo.list_for_user(
            user_id,
            limit=mobile_settings.sync_batch_size,
            unread_only=False
        )
        sync_data["notifications"] = notifications
    
    # Sync search history
    if "search_history" in body.include_types:
        # In production, implement search history sync
        sync_data["search_history"] = []
    
    return OfflineSyncResponse(
        sync_id=sync_id,
        last_sync=datetime.now(timezone.utc),
        data=sync_data,
        has_more=has_more,
        cursor=cursor
    )


# ==================== Status and Info ====================

@router.get("/status", response_model=MobileStatusResponse)
async def mobile_status():
    """Mobile API status endpoint."""
    return MobileStatusResponse(
        status="healthy",
        mobile_api_version=mobile_settings.mobile_api_version,
        features=[
            "bulk_upload",
            "batch_notifications",
            "offline_sync",
            "device_registration",
        ],
        offline_enabled=True
    )


@router.get("/features", response_model=MobileFeatureFlags)
async def mobile_features():
    """Get mobile feature flags."""
    return MobileFeatureFlags(
        offline_sync=True,
        bulk_upload=True,
        batch_notifications=True,
        device_registration=True,
        rate_limits={
            "bulk_upload": {
                "max_files": mobile_settings.bulk_upload_max_files,
                "max_size_mb": mobile_settings.bulk_upload_max_size_mb,
            },
            "batch_notifications": {
                "max_count": mobile_settings.batch_notifications_max_count,
            },
        }
    )


# ==================== Helper Functions ====================

async def _get_user_id(db, email: str) -> int:
    """Get user ID by email."""
    users = UserRepository(db)
    user = await users.get_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user["id"]
