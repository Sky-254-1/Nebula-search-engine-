"""Pytest configuration and shared fixtures for backend tests."""

import os
import sys
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["DATABASE_URL"] = "test_nebula.db"
os.environ["JWT_SECRET"] = "test-secret-key-for-nebula-tests-only"
os.environ["APP_ENV"] = "testing"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["RATE_LIMIT_PER_MINUTE"] = "1000"
os.environ["SIGNUP_RATE_LIMIT"] = "1000"
os.environ["LOGIN_RATE_LIMIT"] = "1000"
os.environ["REFRESH_RATE_LIMIT"] = "1000"

from app.config import get_settings
from app.database import init_db
from app.main import app

get_settings.cache_clear()


def pytest_sessionstart() -> None:
    get_settings.cache_clear()


@pytest_asyncio.fixture
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
