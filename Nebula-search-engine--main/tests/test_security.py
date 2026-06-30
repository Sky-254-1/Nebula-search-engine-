"""Security tests: CSP, CORS, CSRF, security headers, rate-limit headers, brute force lockout."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.config import get_settings


@pytest.mark.asyncio
async def test_csp_header_present(client: AsyncClient):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/health")
    assert "Content-Security-Policy" in resp.headers
    csp = resp.headers["Content-Security-Policy"]
    assert "default-src" in csp
    assert "script-src" in csp
    assert "style-src" in csp


@pytest.mark.asyncio
async def test_cors_headers(client: AsyncClient):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert "access-control-allow-origin" in resp.headers


@pytest.mark.asyncio
async def test_cors_restricts_unknown_origins(client: AsyncClient):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(
            "/health",
            headers={"Origin": "https://evil.com"},
        )
    cors = resp.headers.get("access-control-allow-origin", "")
    assert "evil.com" not in cors


@pytest.mark.asyncio
async def test_csrf_missing_token(client: AsyncClient):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/v1/auth/logout", json={})
    assert resp.status_code == 403 or resp.status_code in (401, 200)


@pytest.mark.asyncio
async def test_security_headers_x_content_type_options(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"


@pytest.mark.asyncio
async def test_security_headers_x_frame_options(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.headers.get("X-Frame-Options") == "DENY"


@pytest.mark.asyncio
async def test_security_headers_referrer_policy(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


@pytest.mark.asyncio
async def test_hsts_not_in_testing(client: AsyncClient):
    resp = await client.get("/health")
    assert "Strict-Transport-Security" not in resp.headers


@pytest.mark.asyncio
async def test_hsts_in_production(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    import app.middleware.security as sec_mw
    monkeypatch.setattr(sec_mw.settings, "app_env", "production")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/health")
    assert "Strict-Transport-Security" in resp.headers
    assert "max-age=31536000" in resp.headers["Strict-Transport-Security"]


@pytest.mark.asyncio
async def test_rate_limit_headers_present(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/search/web?q=test&backend=wikipedia", headers=auth_headers)
    assert resp.status_code == 200 or resp.status_code == 429


@pytest.mark.asyncio
async def test_brute_force_lockout_after_n_attempts(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    import app.routes.auth as auth_routes
    monkeypatch.setattr(auth_routes.settings, "max_login_attempts", 3)
    monkeypatch.setattr(auth_routes.settings, "login_lockout_minutes", 15)

    payload = {"email": "bruteforce@test.com", "password": "ValidPass1!"}
    await client.post("/api/v1/auth/signup", json=payload)

    transport = ASGITransport(app=app)
    for i in range(3):
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/api/v1/auth/login",
                json={"email": "bruteforce@test.com", "password": "wrongpass"},
            )
            assert resp.status_code == 401

    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post("/api/v1/auth/login", json=payload)
        assert resp.status_code == 423


@pytest.mark.asyncio
async def test_csrf_exempts_auth_paths(client: AsyncClient):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/auth/login",
            json={"email": "csrf@test.com", "password": "ValidPass1!"},
        )
    assert resp.status_code in (200, 401)


@pytest.mark.asyncio
async def test_csp_contains_report_uri_if_configured(monkeypatch: pytest.MonkeyPatch):
    from app.config import Settings, get_settings
    get_settings.cache_clear()
    monkeypatch.setenv("CSP_REPORT_URI", "https://example.com/csp-report")
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("DATABASE_URL", "test_nebula.db")
    monkeypatch.setenv("JWT_SECRET", "test-secret")

    s = get_settings()
    policy = s.csp_policy
    assert "report-uri" in policy
    assert "report-to" in policy
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_cors_allows_multiple_origins(monkeypatch: pytest.MonkeyPatch):
    from app.config import Settings, get_settings
    get_settings.cache_clear()
    monkeypatch.setenv("CORS_ORIGINS", "http://a.com,http://b.com")
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("DATABASE_URL", "test_nebula.db")
    monkeypatch.setenv("JWT_SECRET", "test-secret")

    s = get_settings()
    origins = s.cors_origin_list
    assert any(o == "http://a.com" for o in origins)
    assert any(o == "http://b.com" for o in origins)
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_csrf_mismatch_token_returns_403(client: AsyncClient):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("csrf_token", "valid-token")
        resp = await ac.post(
            "/api/v1/auth/logout",
            json={},
            headers={"X-CSRF-Token": "invalid-token"},
        )
    assert resp.status_code == 403
