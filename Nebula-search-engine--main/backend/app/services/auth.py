"""Authentication: password hashing, JWT, and refresh tokens."""

import asyncio
import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, Request

from app.config import get_settings
from app.services.cache import cache_service

settings = get_settings()


def validate_password(password: str, email: str | None = None) -> None:
    """Enhanced password validation policy with generic error messages."""
    is_valid = True
    if len(password) < 8 or len(password) > 128 or password.isspace():
        is_valid = False
    if email and password.lower() == email.lower():
        is_valid = False

    if not re.search(r"[A-Z]", password):
        is_valid = False
    if not re.search(r"[a-z]", password):
        is_valid = False
    if not re.search(r"\d", password):
        is_valid = False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        is_valid = False

    common = {"password123", "qwerty123", "admin123", "nebula123"}
    if password.lower() in common:
        is_valid = False

    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail="Password does not meet security requirements."
        )


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
    return f"{salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, hashed = stored.split("$", 1)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
        return secrets.compare_digest(dk.hex(), hashed)
    except Exception:
        return False


def hash_token(token: str) -> str:
    """Hash a token using HMAC-SHA256 with the JWT secret as the key."""
    return hmac.new(settings.jwt_secret.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()


def create_access_token(email: str, role: str = "user") -> str:
    payload = {
        "sub": email,
        "role": role,
        "type": "access",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiry_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


async def check_brute_force(ip: str, email: str) -> None:
    """Check if login/signup is blocked due to brute-force protection."""
    lock_key = f"lockout:{ip}:{email}"
    if await cache_service.get(lock_key):
        raise HTTPException(
            status_code=423,
            detail="Account temporarily locked. Try again in 15 minutes.",
        )


async def record_login_failure(ip: str, email: str) -> int:
    """Track failed login attempts and apply lockout/delay."""
    attempts_key = f"attempts:{ip}:{email}"
    attempts = (await cache_service.get(attempts_key)) or 0
    attempts += 1
    await cache_service.set(attempts_key, attempts, ttl=3600)

    if attempts >= settings.max_login_attempts:
        lock_key = f"lockout:{ip}:{email}"
        await cache_service.set(lock_key, True, ttl=settings.login_lockout_minutes * 60)

    # Exponential delay: 1, 2, 4, 8, 15
    delay = min(2 ** (attempts - 1), 15)
    await asyncio.sleep(delay)
    return attempts


async def clear_login_attempts(ip: str, email: str) -> None:
    await cache_service.delete(f"attempts:{ip}:{email}")
    await cache_service.delete(f"lockout:{ip}:{email}")


def decode_token(token: str, expected_type: str | None = None) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    if expected_type:
        token_type = payload.get("type", "access")
        if token_type != expected_type:
            raise HTTPException(status_code=401, detail="Invalid token type")
    return payload


def create_token(email: str) -> str:
    """Backward-compatible alias for access token creation."""
    return create_access_token(email)


async def get_current_user_token_payload(request: Request) -> dict:
    token = None
    if settings.auth_cookie_mode:
        token = request.cookies.get("access_token")

    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid authentication",
        )

    payload = decode_token(token, expected_type="access")
    return payload


async def get_current_user(request: Request) -> str:
    payload = await get_current_user_token_payload(request)
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    return email


def require_role(role: str):
    async def role_checker(request: Request):
        payload = await get_current_user_token_payload(request)
        user_role = payload.get("role", "user")
        if role == "admin" and user_role != "admin":
            raise HTTPException(status_code=403, detail="Admin role required")
        return payload

    return role_checker


require_admin = require_role("admin")
require_user = require_role("user")
