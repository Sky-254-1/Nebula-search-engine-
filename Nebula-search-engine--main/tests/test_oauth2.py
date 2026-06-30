"""OAuth2 authentication tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.services.cache import cache_service
from app.services.oauth2 import generate_oauth_state


@pytest.mark.asyncio
async def test_oauth2_login_redirect(client: AsyncClient):
    """GET /oauth2/{provider}/login should redirect to the provider."""
    resp = await client.get("/api/v1/auth/oauth2/google/login", follow_redirects=False)
    assert resp.status_code == 302
    location = resp.headers.get("location", "")
    assert location.startswith("https://accounts.google.com/")
    assert "client_id=" in location
    assert "response_type=code" in location


@pytest.mark.asyncio
async def test_oauth2_login_unsupported_provider(client: AsyncClient):
    resp = await client.get("/api/v1/auth/oauth2/twitter/login")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_oauth2_callback_missing_code(client: AsyncClient):
    resp = await client.get("/api/v1/auth/oauth2/google/callback?state=abc")
    assert resp.status_code == 302
    assert "error=" in resp.headers.get("location", "")


@pytest.mark.asyncio
async def test_oauth2_callback_invalid_state(client: AsyncClient):
    resp = await client.get(
        "/api/v1/auth/oauth2/google/callback?code=abc&state=invalid_state"
    )
    assert resp.status_code == 302
    assert "error=" in resp.headers.get("location", "")


@pytest.mark.asyncio
async def test_oauth2_callback_full_flow(
    client: AsyncClient, mock_httpx: MagicMock
):
    state = generate_oauth_state()
    await cache_service.set(f"oauth2_state:{state}", "google", ttl=600)

    token_resp = MagicMock()
    token_resp.status_code = 200
    token_resp.raise_for_status = MagicMock()
    token_resp.json.return_value = {
        "access_token": "mock-google-token",
        "expires_in": 3600,
    }

    user_resp = MagicMock()
    user_resp.status_code = 200
    user_resp.raise_for_status = MagicMock()
    user_resp.json.return_value = {
        "id": "google-123",
        "email": "googleuser@example.com",
        "name": "Google User",
        "picture": "https://example.com/avatar.png",
    }

    mock_httpx.post.return_value = token_resp
    mock_httpx.get.return_value = user_resp

    resp = await client.get(
        f"/api/v1/auth/oauth2/google/callback?code=mock-code&state={state}",
        follow_redirects=False,
    )

    assert resp.status_code == 302
    location = resp.headers.get("location", "")
    assert "access_token=" in location
    assert "refresh_token=" in location


@pytest.mark.asyncio
async def test_oauth2_callback_existing_user_linked(
    client: AsyncClient, mock_httpx: MagicMock
):
    """OAuth2 callback should link to existing user with same email."""
    signup_resp = await client.post(
        "/api/v1/auth/signup",
        json={"email": "existing@example.com", "password": "Password1!"},
    )
    assert signup_resp.status_code == 201

    state = generate_oauth_state()
    await cache_service.set(f"oauth2_state:{state}", "google", ttl=600)

    token_resp = MagicMock()
    token_resp.status_code = 200
    token_resp.raise_for_status = MagicMock()
    token_resp.json.return_value = {"access_token": "mock-token", "expires_in": 3600}

    user_resp = MagicMock()
    user_resp.status_code = 200
    user_resp.raise_for_status = MagicMock()
    user_resp.json.return_value = {
        "id": "google-existing",
        "email": "existing@example.com",
        "name": "Existing User",
    }

    mock_httpx.post.return_value = token_resp
    mock_httpx.get.return_value = user_resp

    resp = await client.get(
        f"/api/v1/auth/oauth2/google/callback?code=mock-code&state={state}",
        follow_redirects=False,
    )

    assert resp.status_code == 302
    location = resp.headers.get("location", "")
    assert "access_token=" in location


@pytest.mark.asyncio
async def test_oauth2_callback_github(
    client: AsyncClient, mock_httpx: MagicMock
):
    """GitHub OAuth2 flow should work and fetch emails."""
    state = generate_oauth_state()
    await cache_service.set(f"oauth2_state:{state}", "github", ttl=600)

    token_resp = MagicMock()
    token_resp.status_code = 200
    token_resp.raise_for_status = MagicMock()
    token_resp.json.return_value = {"access_token": "mock-gh-token", "expires_in": 3600}

    user_resp = MagicMock()
    user_resp.status_code = 200
    user_resp.raise_for_status = MagicMock()
    user_resp.json.return_value = {
        "id": "github-456",
        "login": "ghuser",
        "name": "GitHub User",
        "avatar_url": "https://avatars.githubusercontent.com/u/456",
    }

    emails_resp = MagicMock()
    emails_resp.status_code = 200
    emails_resp.raise_for_status = MagicMock()
    emails_resp.json.return_value = [
        {"email": "ghuser@example.com", "primary": True, "verified": True},
    ]

    mock_httpx.post.return_value = token_resp
    # First GET for user info, second GET for emails
    mock_httpx.get.side_effect = [user_resp, emails_resp]

    resp = await client.get(
        f"/api/v1/auth/oauth2/github/callback?code=mock-code&state={state}",
        follow_redirects=False,
    )

    assert resp.status_code == 302
    location = resp.headers.get("location", "")
    assert "access_token=" in location
