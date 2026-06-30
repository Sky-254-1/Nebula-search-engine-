"""Pytest configuration and shared fixtures."""

import json
import os
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Use isolated test database before importing the app.
os.environ["DATABASE_URL"] = "test_nebula.db"
os.environ["JWT_SECRET"] = "test-secret-key-for-nebula-tests-only"
os.environ["APP_ENV"] = "testing"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["RATE_LIMIT_PER_MINUTE"] = "1000"
os.environ["SIGNUP_RATE_LIMIT"] = "1000"
os.environ["LOGIN_RATE_LIMIT"] = "1000"
os.environ["REFRESH_RATE_LIMIT"] = "1000"
os.environ["CACHE_TTL_SECONDS"] = "60"
os.environ["GOOGLE_OAUTH2_CLIENT_ID"] = "test-google-client-id"
os.environ["GOOGLE_OAUTH2_CLIENT_SECRET"] = "test-google-client-secret"
os.environ["GITHUB_OAUTH2_CLIENT_ID"] = "test-github-client-id"
os.environ["GITHUB_OAUTH2_CLIENT_SECRET"] = "test-github-client-secret"
os.environ["OAUTH2_REDIRECT_BASE_URI"] = "http://test/api/v1/auth/oauth2"
os.environ["OAUTH2_FRONTEND_REDIRECT_URI"] = "http://test/oauth/callback"

from app.config import get_settings
from app.database import init_db
from app.main import app

get_settings.cache_clear()


@pytest_asyncio.fixture(autouse=True)
async def setup_db() -> AsyncGenerator[None, None]:
    db_path = get_settings().db_path
    if os.path.exists(db_path):
        os.remove(db_path)
    await init_db()
    yield
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/signup",
        json={"email": "test@example.com", "password": "Password1!"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "Password1!"},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def mock_httpx() -> AsyncIterator[MagicMock]:
    """Patches httpx.AsyncClient so no real HTTP calls are made."""
    mock_client = MagicMock(spec=AsyncClient)
    mock_client.get = AsyncMock()
    mock_client.post = AsyncMock()
    mock_client.stream = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock()

    with patch("httpx.AsyncClient", return_value=mock_client):
        yield mock_client


@pytest_asyncio.fixture
async def sample_user(client: AsyncClient) -> dict[str, str]:
    """Creates a user and returns email + tokens."""
    email = "sample@example.com"
    password = "SamplePass1!"
    await client.post("/api/v1/auth/signup", json={"email": email, "password": password})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    data = login.json()
    return {
        "email": email,
        "password": password,
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token", ""),
    }


@pytest_asyncio.fixture
async def sample_document(client: AsyncClient, auth_headers: dict) -> int:
    """Uploads a sample document and returns its id."""
    content = b"Sample document content for testing."
    files = {"file": ("sample.txt", content, "text/plain")}
    upload = await client.post("/api/v1/storage/documents", headers=auth_headers, files=files)
    return upload.json()["id"]


@pytest_asyncio.fixture
def mock_redis() -> MagicMock:
    """Returns a mocked Redis async client."""
    mock = AsyncMock()
    mock.ping.return_value = True
    mock.get.return_value = None
    mock.setex.return_value = True
    mock.delete.return_value = 1

    async def mock_scan_iter(match=None):
        return
        yield

    mock.scan_iter = MagicMock(return_value=mock_scan_iter())
    mock.close = AsyncMock()
    return mock


@pytest_asyncio.fixture
def mock_openai() -> Generator[MagicMock, None, None]:
    """Patches settings.openai_api_key for tests that need OpenAI."""
    from app.config import get_settings as gs
    orig_key = gs().openai_api_key
    with patch.object(gs(), "openai_api_key", "sk-test-key"):
        yield MagicMock()
    with patch.object(gs(), "openai_api_key", orig_key):
        pass


@pytest_asyncio.fixture
def test_settings_override() -> Generator[dict, None, None]:
    """Context manager fixture to temporarily override settings.

    Usage:
        with test_settings_override() as s:
            s.rate_limit_per_minute = 999
    """
    overrides = {}

    class _Override:
        def __setattr__(self, name, value):
            overrides[name] = value

        def __getattr__(self, name):
            return object.__getattribute__(self, name)

    yield _Override()
    if overrides:
        from app.config import get_settings as gs
        for key, val in overrides.items():
            object.__setattr__(gs(), key, val)
