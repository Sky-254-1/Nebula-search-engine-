"""Extended authentication tests: validation, rate-limiting, refresh rotation, 2FA, roles."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient

from app.services.auth import validate_password


class TestPasswordValidation:
    def test_weak_password_too_short(self):
        with pytest.raises(Exception):
            validate_password("Ab1!", "test@example.com")

    def test_weak_password_no_uppercase(self):
        with pytest.raises(Exception):
            validate_password("lowercase1!", "test@example.com")

    def test_weak_password_no_lowercase(self):
        with pytest.raises(Exception):
            validate_password("UPPERCASE1!", "test@example.com")

    def test_weak_password_no_digit(self):
        with pytest.raises(Exception):
            validate_password("NoDigits!!", "test@example.com")

    def test_weak_password_no_special(self):
        with pytest.raises(Exception):
            validate_password("NoSpecial1", "test@example.com")

    def test_weak_password_matches_email(self):
        with pytest.raises(Exception):
            validate_password("Test@example.com1", "test@example.com")

    def test_weak_password_common(self):
        with pytest.raises(Exception):
            validate_password("Password123!", "test@example.com")

    def test_strong_password_passes(self):
        validate_password("Str0ng!Pass#99", "test@example.com")


@pytest.mark.asyncio
async def test_signup_weak_password_rejected(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/signup",
        json={"email": "weak@example.com", "password": "short"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_signup_common_password_rejected(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/signup",
        json={"email": "common@example.com", "password": "Password123!"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_signup_duplicate_email_returns_409(client: AsyncClient):
    payload = {"email": "dup@example.com", "password": "ValidPass1!"}
    r1 = await client.post("/api/v1/auth/signup", json=payload)
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/auth/signup", json=payload)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_login_rate_limit_enforced(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    import app.middleware.rate_limit as rl
    monkeypatch.setattr(rl.settings, "login_rate_limit", 2)

    payload = {"email": "ratelimit@example.com", "password": "ValidPass1!"}
    await client.post("/api/v1/auth/signup", json=payload)

    resp1 = await client.post("/api/v1/auth/login", json=payload)
    assert resp1.status_code == 200

    # Use a fresh client to avoid cookies from previous login
    from httpx import ASGITransport
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c2:
        resp2 = await c2.post("/api/v1/auth/login", json=payload)
        assert resp2.status_code == 200

        async with AsyncClient(transport=transport, base_url="http://test") as c3:
            resp3 = await c3.post("/api/v1/auth/login", json=payload)
            assert resp3.status_code == 429


@pytest.mark.asyncio
async def test_refresh_token_rotation(client: AsyncClient):
    signup = await client.post(
        "/api/v1/auth/signup",
        json={"email": "rotate@example.com", "password": "ValidPass1!"},
    )
    assert signup.status_code == 201

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "rotate@example.com", "password": "ValidPass1!"},
    )
    assert login.status_code == 200
    old_refresh = login.json()["refresh_token"]

    refresh1 = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert refresh1.status_code == 200
    new_refresh = refresh1.json()["refresh_token"]

    refresh2 = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": new_refresh},
    )
    assert refresh2.status_code == 200


@pytest.mark.asyncio
async def test_refresh_token_reuse_detected(client: AsyncClient):
    signup = await client.post(
        "/api/v1/auth/signup",
        json={"email": "reuse@example.com", "password": "ValidPass1!"},
    )
    assert signup.status_code == 201

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "reuse@example.com", "password": "ValidPass1!"},
    )
    assert login.status_code == 200
    old_refresh = login.json()["refresh_token"]

    await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 401
    data = resp.json()
    assert "reuse" in data.get("detail", "").lower()


@pytest.mark.asyncio
async def test_logout_revokes_session(client: AsyncClient):
    signup = await client.post(
        "/api/v1/auth/signup",
        json={"email": "logout@example.com", "password": "ValidPass1!"},
    )
    assert signup.status_code == 201

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "logout@example.com", "password": "ValidPass1!"},
    )
    assert login.status_code == 200
    refresh_token = login.json()["refresh_token"]

    logout = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert logout.status_code == 200

    refresh = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh.status_code == 401


@pytest.mark.asyncio
async def test_logout_all_revokes_all_sessions(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/v1/auth/logout-all", headers=auth_headers)
    assert resp.status_code == 200

    me = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert me.status_code == 401


@pytest.mark.asyncio
async def test_admin_role_enforced(client: AsyncClient):
    from app.middleware.rate_limit import rate_limit
    from app.services.auth import get_current_user
    from app.database import get_db
    from app.database.repositories.user import UserRepository

    app_deps = {}
    import app.main as main_mod
    app_deps = main_mod.app.dependency_overrides

    try:
        main_mod.app.dependency_overrides[get_current_user] = lambda: "nonadmin@test.com"
        main_mod.app.dependency_overrides[get_db] = lambda: MagicMock()
        main_mod.app.dependency_overrides[rate_limit] = lambda: None

        user_repo_mock = AsyncMock()
        user_repo_mock.get_id_by_email.return_value = 1
        user_repo_mock.get_by_email.return_value = {"id": 1, "email": "nonadmin@test.com", "role": "user", "hashed_password": "x"}
        from unittest.mock import patch
        with patch("app.routes.admin.UserRepository", return_value=user_repo_mock):
            resp = await client.get("/api/v1/admin/audit-logs")
            assert resp.status_code == 403
    finally:
        main_mod.app.dependency_overrides = app_deps


@pytest.mark.asyncio
async def test_admin_can_access_admin_routes(client: AsyncClient):
    from app.middleware.rate_limit import rate_limit
    from app.services.auth import get_current_user, decode_token, create_access_token
    from app.database import get_db
    import app.main as main_mod

    admin_token = create_access_token("admin@test.com", role="admin")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    try:
        main_mod.app.dependency_overrides[get_current_user] = lambda: "admin@test.com"
        main_mod.app.dependency_overrides[get_db] = lambda: MagicMock()
        main_mod.app.dependency_overrides[rate_limit] = lambda: None

        with patch("app.routes.admin.AuditRepository.get_recent", new_callable=AsyncMock) as mock:
            mock.return_value = []
            resp = await client.get("/api/v1/admin/audit-logs", headers=admin_headers)
            assert resp.status_code == 200
    finally:
        main_mod.app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_brute_force_lockout(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    import app.routes.auth as auth_routes
    monkeypatch.setattr(auth_routes.settings, "max_login_attempts", 3)
    monkeypatch.setattr(auth_routes.settings, "login_lockout_minutes", 15)

    payload = {"email": "brute@example.com", "password": "ValidPass1!"}
    await client.post("/api/v1/auth/signup", json=payload)

    from httpx import ASGITransport
    from app.main import app
    transport = ASGITransport(app=app)

    for _ in range(3):
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            await c.post("/api/v1/auth/login", json={"email": "brute@example.com", "password": "wrong"})

    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post("/api/v1/auth/login", json=payload)
        assert resp.status_code == 423


@pytest.mark.asyncio
async def test_session_revocation_by_admin(client: AsyncClient):
    from app.middleware.rate_limit import rate_limit
    from app.services.auth import get_current_user, create_access_token
    from app.database import get_db
    import app.main as main_mod

    admin_token = create_access_token("admin@test.com", role="admin")

    try:
        main_mod.app.dependency_overrides[get_current_user] = lambda: "admin@test.com"
        main_mod.app.dependency_overrides[get_db] = lambda: MagicMock()
        main_mod.app.dependency_overrides[rate_limit] = lambda: None

        with patch("app.routes.admin.SessionRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo_cls.return_value = mock_repo
            resp = await client.post(
                "/api/v1/admin/sessions/test-session-id/revoke",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert resp.status_code == 200
            mock_repo.revoke_session_family.assert_called_once_with("test-session-id", "Revoked by administrator")
    finally:
        main_mod.app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_me_returns_correct_email(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"
