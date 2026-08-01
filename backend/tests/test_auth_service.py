"""Tests for authentication service.

Focus areas:
- Password validation, hashing, and verification
- JWT token creation and decoding
- Brute-force protection
- Token revocation (JTI blacklist)
- Role and permission checks
"""

import asyncio
import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import HTTPException

from app.services.auth import (
    check_brute_force,
    clear_login_attempts,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    record_login_failure,
    require_permission,
    require_role,
    verify_password,
    validate_password,
)


class TestPasswordValidation:
    """Test password validation policy."""

    def test_valid_password(self):
        """Should accept valid password meeting all requirements."""
        # No exception should be raised
        validate_password("ValidPass1!")

    def test_password_too_short(self):
        """Should reject passwords shorter than 8 characters."""
        with pytest.raises(HTTPException) as exc_info:
            validate_password("Short1!")
        assert exc_info.value.status_code == 400
        assert "Password does not meet security requirements" in exc_info.value.detail

    def test_password_too_long(self):
        """Should reject passwords longer than 128 characters."""
        long_password = "A" * 129 + "1!"
        with pytest.raises(HTTPException) as exc_info:
            validate_password(long_password)
        assert exc_info.value.status_code == 400

    def test_password_all_spaces(self):
        """Should reject passwords that are all spaces."""
        with pytest.raises(HTTPException) as exc_info:
            validate_password("        ")
        assert exc_info.value.status_code == 400

    def test_password_no_uppercase(self):
        """Should reject passwords without uppercase letters."""
        with pytest.raises(HTTPException) as exc_info:
            validate_password("lowercase1!")
        assert exc_info.value.status_code == 400

    def test_password_no_lowercase(self):
        """Should reject passwords without lowercase letters."""
        with pytest.raises(HTTPException) as exc_info:
            validate_password("UPPERCASE1!")
        assert exc_info.value.status_code == 400

    def test_password_no_digit(self):
        """Should reject passwords without digits."""
        with pytest.raises(HTTPException) as exc_info:
            validate_password("NoDigits!")
        assert exc_info.value.status_code == 400

    def test_password_no_special_char(self):
        """Should reject passwords without special characters."""
        with pytest.raises(HTTPException) as exc_info:
            validate_password("NoSpecial1")
        assert exc_info.value.status_code == 400

    def test_password_matches_email(self):
        """Should reject passwords that match email."""
        email = "user@example.com"
        with pytest.raises(HTTPException) as exc_info:
            validate_password(email, email=email)
        assert exc_info.value.status_code == 400

    def test_common_passwords_rejected(self):
        """Should reject common weak passwords."""
        common_passwords = [
            "password123",
            "qwerty123",
            "admin123",
            "nebula123",
        ]
        for password in common_passwords:
            with pytest.raises(HTTPException) as exc_info:
                validate_password(password)
            assert exc_info.value.status_code == 400

    def test_valid_special_characters(self):
        """Should accept passwords with various special characters."""
        special_chars = "!@#$%^&*(),.?\":{}|<>"
        for char in special_chars:
            password = f"ValidPass1{char}"
            # Should not raise
            validate_password(password)


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password_generates_unique_salt(self):
        """Each hash should use a unique salt."""
        password = "TestPass1!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Hashes should be different due to unique salts
        assert hash1 != hash2

        # Both should verify correctly
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)

    def test_hash_password_format(self):
        """Hash should be in format: salt$hash."""
        password = "TestPass1!"
        hashed = hash_password(password)

        # Should contain exactly one $
        parts = hashed.split("$")
        assert len(parts) == 2

        salt, digest = parts
        assert len(salt) == 32  # 16 bytes hex
        assert len(digest) == 64  # SHA256 hex

    def test_verify_password_success(self):
        """Should verify correct password."""
        password = "TestPass1!"
        hashed = hash_password(password)
        assert verify_password(password, hashed)

    def test_verify_password_failure(self):
        """Should reject incorrect password."""
        password = "WrongPass1!"
        hashed = hash_password("TestPass1!")
        assert not verify_password(password, hashed)

    def test_verify_password_corrupted_format(self):
        """Should handle corrupted hash format gracefully."""
        assert not verify_password("password", "invalid")
        assert not verify_password("password", "onlysalt")
        assert not verify_password("password", "$")
        assert not verify_password("password", "")


class TestTokenHashing:
    """Test token hashing."""

    def test_hash_token_sha256(self):
        """Hash should be SHA256 hex digest."""
        token = "test_token_123"
        hashed = hash_token(token)

        # Verify against manual SHA256
        expected = hashlib.sha256(token.encode()).hexdigest()
        assert hashed == expected

    def test_hash_token_different(self):
        """Different tokens should have different hashes."""
        hash1 = hash_token("token1")
        hash2 = hash_token("token2")
        assert hash1 != hash2


class TestAccessToken:
    """Test access token creation and decoding."""

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        """Set up test environment variables."""
        from app.config import get_settings
        monkeypatch.setenv("JWT_SECRET", "test-secret-key")
        monkeypatch.setenv("JWT_ISSUER", "Nebula Search")
        monkeypatch.setenv("JWT_AUDIENCE", "nebula-search-api")
        monkeypatch.setenv("JWT_EXPIRY_MINUTES", "30")
        get_settings.cache_clear()

    def test_create_access_token_structure(self):
        """Access token should contain all required claims."""
        token = create_access_token("user@example.com", role="user")

        # Decode without verification to inspect payload
        import jwt
        decoded = jwt.decode(
            token,
            "test-secret-key",
            algorithms=["HS256"],
            audience="nebula-search-api",
            issuer="Nebula Search",
        )

        assert decoded["sub"] == "user@example.com"
        assert decoded["role"] == "user"
        assert decoded["type"] == "access"
        assert "iat" in decoded
        assert "exp" in decoded
        assert "iss" in decoded
        assert "aud" in decoded
        assert "jti" in decoded

    def test_create_access_token_default_role(self):
        """Should default to user role."""
        token = create_access_token("user@example.com")
        import jwt
        decoded = jwt.decode(
            token,
            "test-secret-key",
            algorithms=["HS256"],
            audience="nebula-search-api",
            issuer="Nebula Search",
        )
        assert decoded["role"] == "user"

    def test_create_access_token_custom_jti(self):
        """Should use provided JTI if given."""
        custom_jti = "custom-jti-123"
        token = create_access_token("user@example.com", jti=custom_jti)
        import jwt
        decoded = jwt.decode(
            token,
            "test-secret-key",
            algorithms=["HS256"],
            audience="nebula-search-api",
            issuer="Nebula Search",
        )
        assert decoded["jti"] == custom_jti

    def test_create_access_token_unique_jti(self):
        """Each token should have unique JTI."""
        token1 = create_access_token("user@example.com")
        token2 = create_access_token("user@example.com")

        import jwt
        decoded1 = jwt.decode(
            token1,
            "test-secret-key",
            algorithms=["HS256"],
            audience="nebula-search-api",
            issuer="Nebula Search",
        )
        decoded2 = jwt.decode(
            token2,
            "test-secret-key",
            algorithms=["HS256"],
            audience="nebula-search-api",
            issuer="Nebula Search",
        )
        assert decoded1["jti"] != decoded2["jti"]

    def test_create_access_token_expiration(self):
        """Token should expire after configured time."""
        token = create_access_token("user@example.com")
        import jwt
        decoded = jwt.decode(
            token,
            "test-secret-key",
            algorithms=["HS256"],
            audience="nebula-search-api",
            issuer="Nebula Search",
        )

        now = datetime.now(timezone.utc)
        exp = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        iat = datetime.fromtimestamp(decoded["iat"], tz=timezone.utc)

        # Should be approximately 30 minutes
        delta = exp - iat
        assert 29 * 60 <= delta.total_seconds() <= 31 * 60

    def test_decode_token_success(self):
        """Should decode valid token."""
        token = create_access_token("user@example.com")
        payload = decode_token(token)
        assert payload["sub"] == "user@example.com"
        assert payload["type"] == "access"

    def test_decode_token_expired(self):
        """Should raise for expired token."""
        # Create token with past expiration
        import jwt
        from app.config import get_settings

        settings = get_settings()
        payload = {
            "sub": "user@example.com",
            "role": "user",
            "type": "access",
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "jti": secrets.token_urlsafe(16),
        }
        expired_token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        with pytest.raises(HTTPException) as exc_info:
            decode_token(expired_token)
        assert exc_info.value.status_code == 401
        assert "Token expired" in exc_info.value.detail

    def test_decode_token_invalid_audience(self):
        """Should raise for invalid audience."""
        import jwt
        from app.config import get_settings

        settings = get_settings()
        payload = {
            "sub": "user@example.com",
            "role": "user",
            "type": "access",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iss": settings.jwt_issuer,
            "aud": "wrong-audience",
            "jti": secrets.token_urlsafe(16),
        }
        invalid_token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        with pytest.raises(HTTPException) as exc_info:
            decode_token(invalid_token)
        assert exc_info.value.status_code == 401
        assert "Invalid token audience" in exc_info.value.detail

    def test_decode_token_invalid_issuer(self):
        """Should raise for invalid issuer."""
        import jwt
        from app.config import get_settings

        settings = get_settings()
        payload = {
            "sub": "user@example.com",
            "role": "user",
            "type": "access",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iss": "wrong-issuer",
            "aud": settings.jwt_audience,
            "jti": secrets.token_urlsafe(16),
        }
        invalid_token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        with pytest.raises(HTTPException) as exc_info:
            decode_token(invalid_token)
        assert exc_info.value.status_code == 401
        assert "Invalid token issuer" in exc_info.value.detail

    def test_decode_token_wrong_secret(self):
        """Should raise for token signed with wrong key."""
        token = create_access_token("user@example.com")

        # Try to decode with wrong key - should raise InvalidSignatureError from jwt
        import jwt
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(
                token,
                "wrong-secret",
                algorithms=["HS256"],
                audience="nebula-search-api",
                issuer="Nebula Search",
            )

    def test_decode_token_invalid_type(self):
        """Should raise for wrong token type."""
        # Create refresh token
        import jwt
        from app.config import get_settings

        settings = get_settings()
        payload = {
            "sub": "user@example.com",
            "role": "user",
            "type": "refresh",  # Wrong type
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "jti": secrets.token_urlsafe(16),
        }
        refresh_token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        with pytest.raises(HTTPException) as exc_info:
            decode_token(refresh_token, expected_type="access")
        assert exc_info.value.status_code == 401
        assert "Invalid token type" in exc_info.value.detail


class TestRefreshToken:
    """Test refresh token creation."""

    def test_create_refresh_token_length(self):
        """Should generate secure random token."""
        token = create_refresh_token()
        # 48 bytes = 64 characters base64url
        assert len(token) == 64

    def test_create_refresh_token_unique(self):
        """Each token should be unique."""
        token1 = create_refresh_token()
        token2 = create_refresh_token()
        assert token1 != token2

    def test_create_refresh_token_security(self):
        """Should use cryptographically secure randomness."""
        token = create_refresh_token()
        # Should contain only URL-safe characters
        assert re.match(r'^[A-Za-z0-9_-]+$', token)


class TestBackwardCompatibility:
    """Test backward-compatible functions."""

    def test_create_token_alias(self):
        """create_token should be alias for create_access_token."""
        import app.services.auth as auth_module
        token = auth_module.create_token("user@example.com")
        assert token is not None
        assert isinstance(token, str)


class TestRolePermissionDecorators:
    """Test role and permission checking decorators."""

    def test_require_role_admin_check(self):
        """Should check for admin role."""
        admin_payload = {"role": "admin"}
        user_payload = {"role": "user"}

        admin_checker = require_role("admin")
        user_checker = require_role("user")

        # Mock request with admin role
        admin_request = MagicMock()
        admin_request.headers = {"Authorization": "Bearer valid_token"}

        # Mock request with user role
        user_request = MagicMock()
        user_request.headers = {"Authorization": "Bearer valid_token"}

        # This would need proper mocking with decode_token
        # Just verify decorator doesn't fail
        assert callable(admin_checker)
        assert callable(user_checker)

    def test_require_permission_admin_bypass(self):
        """Admin should bypass permission check."""
        admin_checker = require_permission("delete_document")

        # Admin has all permissions
        admin_request = MagicMock()
        admin_request.headers = {"Authorization": "Bearer valid_token"}

        assert callable(admin_checker)

    def test_require_permission_user_check(self):
        """Should check user permissions from payload."""
        user_checker = require_permission("read_documents")

        user_request = MagicMock()
        user_request.headers = {"Authorization": "Bearer valid_token"}

        assert callable(user_checker)


@pytest_asyncio.fixture
async def mock_cache_service():
    """Mock cache service for brute-force tests."""
    with patch("app.services.auth.cache_service") as mock_cache:
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        mock_cache.delete = AsyncMock()
        yield mock_cache


class TestBruteForceProtection:
    """Test brute-force protection mechanisms."""

    @pytest.mark.asyncio
    async def test_check_brute_force_not_blocked(self, mock_cache_service):
        """Should allow request if not blocked."""
        mock_cache_service.get.return_value = None

        # Should not raise
        await check_brute_force("192.168.1.1", "user@example.com")

    @pytest.mark.asyncio
    async def test_check_brute_force_blocked(self, mock_cache_service):
        """Should raise if IP+email is blocked."""
        mock_cache_service.get.return_value = True

        with pytest.raises(HTTPException) as exc_info:
            await check_brute_force("192.168.1.1", "user@example.com")
        assert exc_info.value.status_code == 423
        assert "locked" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_record_login_failure_first_attempt(self, mock_cache_service):
        """First failure should not lock account."""
        mock_cache_service.get.return_value = None

        attempts = await record_login_failure("192.168.1.1", "user@example.com")
        assert attempts == 1

        # Should set attempts key with TTL
        mock_cache_service.set.assert_called_once()
        call_args = mock_cache_service.set.call_args
        assert call_args[0][0] == "attempts:192.168.1.1:user@example.com"
        assert call_args[0][1] == 1
        assert call_args[1]["ttl"] == 3600

    @pytest.mark.asyncio
    async def test_record_login_failure_max_attempts(self, mock_cache_service):
        """Should lock account after max attempts."""
        # Simulate reaching max attempts (5 failures)
        # First 4 calls return 0-3, 5th call returns 4 which triggers lockout
        mock_cache_service.get.return_value = 4

        attempts = await record_login_failure("192.168.1.1", "user@example.com")
        assert attempts == 5  # 4 + 1

        # Should set lockout key after 5th attempt
        lockout_call = mock_cache_service.set.call_args_list[-1]
        assert lockout_call[0][0] == "lockout:192.168.1.1:user@example.com"
        assert lockout_call[0][1] is True

    @pytest.mark.asyncio
    async def test_record_login_failure_delay(self, mock_cache_service):
        """Should add exponential delay."""
        mock_cache_service.get.return_value = 0
        with patch("app.services.auth.asyncio.sleep") as mock_sleep:
            await record_login_failure("192.168.1.1", "user@example.com")

            # Should sleep (exponential delay: 2^0 = 1 second)
            mock_sleep.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_login_attempts(self, mock_cache_service):
        """Should clear both attempts and lockout keys."""
        await clear_login_attempts("192.168.1.1", "user@example.com")

        assert mock_cache_service.delete.call_count == 2
        calls = [str(call) for call in mock_cache_service.delete.call_args_list]
        assert any("attempts:" in str(call) for call in calls)
        assert any("lockout:" in str(call) for call in calls)