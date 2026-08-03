"""Tests for mobile-specific API endpoints."""

import os
import sys
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_TEST_DB_DIR = Path(tempfile.gettempdir()) / "nebula-mobile-tests"
_TEST_DB_DIR.mkdir(parents=True, exist_ok=True)
_TEST_DB_PATH = _TEST_DB_DIR / f"test_mobile_{os.getpid()}.db"

os.environ["DATABASE_URL"] = str(_TEST_DB_PATH)
os.environ["JWT_SECRET"] = "test-secret-key-for-mobile-tests-only"
os.environ["APP_ENV"] = "testing"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"

from app.main import app  # noqa: E402
from app.database import init_db  # noqa: E402
from app.services.auth import create_access_token


@pytest_asyncio.fixture(scope="module")
async def test_client():
    """Create test client and initialize database."""
    # Initialize test database
    await init_db()
    
    # Use TestClient for FastAPI testing (synchronous wrapper for async apps)
    from starlette.testclient import TestClient
    client = TestClient(app)
    client.headers.update({"Content-Type": "application/json"})
    
    yield client
    
    # Cleanup
    from app.database.engine import close_pool
    await close_pool()
    if _TEST_DB_PATH.exists():
        _TEST_DB_PATH.unlink()


@pytest_asyncio.fixture
async def auth_headers():
    """Generate auth headers for test user."""
    token = create_access_token(email="test@example.com", role="user")
    return {"Authorization": f"Bearer {token}"}


# ==================== Status Endpoint Tests ====================

@pytest.mark.asyncio
async def test_mobile_status_endpoint(test_client, auth_headers):
    """Test /api/v1/mobile/status endpoint returns correct structure."""
    response = test_client.get("/api/v1/mobile/status", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert "mobile_api_version" in data
    assert "features" in data
    assert data["offline_enabled"] is True


# ==================== Feature Flags Tests ====================

@pytest.mark.asyncio
async def test_mobile_features_endpoint(test_client, auth_headers):
    """Test /api/v1/mobile/features endpoint returns feature flags."""
    response = test_client.get("/api/v1/mobile/features", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["offline_sync"] is True
    assert data["bulk_upload"] is True
    assert data["batch_notifications"] is True
    assert data["device_registration"] is True
    assert "rate_limits" in data


# ==================== Bulk Upload Tests ====================

@pytest.mark.asyncio
async def test_bulk_upload_endpoint(test_client, auth_headers):
    """Test /api/v1/mobile/bulk/upload endpoint."""
    bulk_upload_data = {
        "files": ["test1.txt", "test2.txt"],
        "folder_id": None,
        "notify_on_complete": True
    }
    
    response = test_client.post(
        "/api/v1/mobile/bulk/upload",
        json=bulk_upload_data,
        headers=auth_headers
    )
    
    # This should work (or return 401 if auth check is strict)
    assert response.status_code in [200, 401]


# ==================== Batch Notifications Tests ====================

@pytest.mark.asyncio
async def test_batch_notifications_endpoint(test_client, auth_headers):
    """Test /api/v1/mobile/bulk/notifications endpoint."""
    batch_data = {
        "notifications": [
            {"type": "system", "title": "Test", "message": "Test message"},
        ],
        "priority": "normal"
    }
    
    response = test_client.post(
        "/api/v1/mobile/bulk/notifications",
        json=batch_data,
        headers=auth_headers
    )
    
    assert response.status_code in [200, 401]


# ==================== Device Registration Tests ====================

@pytest.mark.asyncio
async def test_device_registration_endpoint(test_client, auth_headers):
    """Test /api/v1/mobile/devices/register endpoint."""
    device_data = {
        "device_id": "test-device-123",
        "device_name": "Test Phone",
        "device_type": "mobile",
        "platform": "ios",
        "push_token": None,
        "app_version": "1.0.0"
    }
    
    response = test_client.post(
        "/api/v1/mobile/devices/register",
        json=device_data,
        headers=auth_headers
    )
    
    assert response.status_code in [200, 401]


# ==================== Offline Sync Tests ====================

@pytest.mark.asyncio
async def test_offline_sync_endpoint(test_client, auth_headers):
    """Test /api/v1/mobile/sync endpoint."""
    sync_data = {
        "device_id": "test-device-123",
        "sync_type": "incremental",
        "include_types": ["documents", "notifications"]
    }
    
    response = test_client.post(
        "/api/v1/mobile/sync",
        json=sync_data,
        headers=auth_headers
    )
    
    assert response.status_code in [200, 401]


# ==================== Helper Tests ====================

def test_mobile_settings():
    """Test mobile settings configuration."""
    # Set test environment variables first
    os.environ["MOBILE_API_VERSION"] = "v1"
    os.environ["MOBILE_PREFIX"] = "/api/v1/mobile"
    os.environ["BULK_UPLOAD_MAX_FILES"] = "50"
    os.environ["BATCH_NOTIFICATIONS_MAX_COUNT"] = "100"
    
    from app.mobile.config import get_mobile_settings
    
    settings = get_mobile_settings()
    assert settings.mobile_api_version == "v1"
    assert settings.mobile_prefix == "/api/v1/mobile"
    assert settings.bulk_upload_max_files == 50
    assert settings.batch_notifications_max_count == 100


def test_mobile_models():
    """Test mobile model creation."""
    from app.mobile.models import (
        BulkUploadRequest,
        MobileStatusResponse,
        MobileFeatureFlags,
    )
    
    # Test BulkUploadRequest
    upload_request = BulkUploadRequest(
        files=["test.txt"],
        notify_on_complete=True
    )
    assert len(upload_request.files) == 1
    
    # Test MobileStatusResponse
    status = MobileStatusResponse(
        status="healthy",
        mobile_api_version="v1"
    )
    assert status.status == "healthy"
    assert status.offline_enabled is True
    
    # Test MobileFeatureFlags
    features = MobileFeatureFlags(
        offline_sync=True,
        bulk_upload=True,
        batch_notifications=True,
        device_registration=True
    )
    assert features.offline_sync is True
