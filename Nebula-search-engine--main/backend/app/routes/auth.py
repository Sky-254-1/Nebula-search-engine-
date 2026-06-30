"""Authentication routes."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.database import get_db
from app.database.repositories.api_key import APIKeyRepository
from app.database.repositories.audit import AuditRepository
from app.database.repositories.session import SessionRepository
from app.database.repositories.user import UserRepository
from app.middleware.rate_limit import limit_login, limit_refresh, limit_signup
from app.models.schemas import AuthRequest, AuthResponse, RefreshRequest
from app.config import get_settings
from app.services.auth import (
    check_brute_force,
    clear_login_attempts,
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    hash_token,
    record_login_failure,
    validate_password,
    verify_password,
)

settings = get_settings()
router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    if not settings.auth_cookie_mode:
        return
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.jwt_expiry_hours * 3600,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.refresh_token_days * 86400,
    )


@router.post("/signup", status_code=201, dependencies=[Depends(limit_signup)])
async def signup(request: Request, body: AuthRequest, db=Depends(get_db)):
    validate_password(body.password, str(body.email))
    users = UserRepository(db)
    existing = await users.get_by_email(str(body.email))
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    await users.create(str(body.email), hash_password(body.password))

    if settings.enable_audit_logs:
        audit = AuditRepository(db)
        new_user = await users.get_by_email(str(body.email))
        if not new_user:
            # Should not happen but for safety
            return {"message": "User created successfully"}
        await audit.create(
            new_user["id"],
            "signup",
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

    return {"message": "User created successfully"}


@router.post("/login", response_model=AuthResponse, dependencies=[Depends(limit_login)])
async def login(request: Request, response: Response, body: AuthRequest, db=Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    await check_brute_force(ip, str(body.email))

    users = UserRepository(db)
    row = await users.get_by_email(str(body.email))

    if not row or not verify_password(body.password, row["hashed_password"]):
        await record_login_failure(ip, str(body.email))
        raise HTTPException(status_code=401, detail="Invalid email or password")

    await clear_login_attempts(ip, str(body.email))

    access_token = create_access_token(str(body.email), role=row["role"])
    refresh_token = create_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days)

    session_id = str(uuid.uuid4())
    sessions = SessionRepository(db)
    await sessions.create(
        row["id"],
        hash_token(refresh_token),
        expires_at,
        session_id=session_id,
        device_name=request.headers.get("user-agent"),
    )

    if settings.enable_audit_logs:
        audit = AuditRepository(db)
        await audit.create(
            row["id"],
            "login",
            metadata={"session_id": session_id},
            ip=ip,
            user_agent=request.headers.get("user-agent"),
        )

    _set_auth_cookies(response, access_token, refresh_token)
    return AuthResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=AuthResponse, dependencies=[Depends(limit_refresh)])
async def refresh(request: Request, response: Response, body: RefreshRequest | None = None, db=Depends(get_db)):
    refresh_token = None
    if body and body.refresh_token:
        refresh_token = body.refresh_token
    elif settings.auth_cookie_mode:
        refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    sessions = SessionRepository(db)
    token_hash = hash_token(refresh_token)
    session = await sessions.get_by_hash(token_hash)

    if not session:
        # Check for reuse if detection is enabled
        # In a real scenario, we'd need a way to find which session this token *belonged* to
        # For now, we'll just treat it as invalid.
        # Advanced reuse detection usually requires keeping a record of old tokens.
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if session["revoked_reason"]:
        raise HTTPException(status_code=401, detail=f"Session revoked: {session['revoked_reason']}")

    if session["rotated_at"]:
        # Token already used! Potential theft.
        if settings.enable_refresh_reuse_detection:
            await sessions.revoke_session_family(session["session_id"], "Refresh token reuse detected")
            if settings.enable_audit_logs:
                audit = AuditRepository(db)
                await audit.create(
                    session["user_id"],
                    "security_alert",
                    resource="session",
                    metadata={"action": "reuse_detected", "session_id": session["session_id"]},
                    ip=request.client.host if request.client else None,
                )
        raise HTTPException(status_code=401, detail="Token reuse detected")

    expires_at = datetime.fromisoformat(str(session["expires_at"]).replace("Z", "+00:00"))
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        await sessions.delete(session["id"])
        raise HTTPException(status_code=401, detail="Refresh token expired")

    users = UserRepository(db)
    user = await users.get_by_id(session["user_id"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    access_token = create_access_token(user["email"], role=user["role"])
    new_refresh = create_refresh_token()

    # Mark old token as rotated
    await sessions.update_rotation(session["id"], datetime.now(timezone.utc))

    # Create new session entry in the same family
    new_expires = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days)
    await sessions.create(
        session["user_id"],
        hash_token(new_refresh),
        new_expires,
        session_id=session["session_id"],
        device_name=session["device_name"],
        parent_refresh_id=session["id"],
    )

    if settings.enable_audit_logs:
        audit = AuditRepository(db)
        await audit.create(
            user["id"],
            "token_refresh",
            metadata={"session_id": session["session_id"]},
            ip=request.client.host if request.client else None,
        )

    _set_auth_cookies(response, access_token, new_refresh)
    return AuthResponse(access_token=access_token, refresh_token=new_refresh)


@router.post("/logout")
async def logout(request: Request, response: Response, body: RefreshRequest | None = None, db=Depends(get_db)):
    refresh_token = None
    if body and body.refresh_token:
        refresh_token = body.refresh_token
    elif settings.auth_cookie_mode:
        refresh_token = request.cookies.get("refresh_token")

    if refresh_token:
        sessions = SessionRepository(db)
        session = await sessions.get_by_hash(hash_token(refresh_token))
        if session:
            # Delete the whole session family on logout
            await sessions.delete_by_session_id(session["session_id"])
            if settings.enable_audit_logs:
                audit = AuditRepository(db)
                await audit.create(
                    session["user_id"],
                    "logout",
                    metadata={"session_id": session["session_id"]},
                    ip=request.client.host if request.client else None,
                )

    if settings.auth_cookie_mode:
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")

    return {"message": "Logged out"}


@router.post("/logout-all")
async def logout_all(request: Request, response: Response, db=Depends(get_db), email: str = Depends(get_current_user)):
    users = UserRepository(db)
    user = await users.get_by_email(email)
    if user:
        sessions = SessionRepository(db)
        await sessions.delete_all_for_user(user["id"])
        if settings.enable_audit_logs:
            audit = AuditRepository(db)
            await audit.create(
                user["id"],
                "logout_all",
                ip=request.client.host if request.client else None,
            )

    if settings.auth_cookie_mode:
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")

    return {"message": "Logged out from all devices"}


@router.get("/me")
async def get_me(email: str = Depends(get_current_user), db=Depends(get_db)):
    users = UserRepository(db)
    user = await users.get_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"email": user["email"], "role": user["role"], "id": user["id"]}


@router.put("/profile")
async def update_profile(body: dict, db=Depends(get_db), email: str = Depends(get_current_user)):
    from app.database.repositories.settings import SettingsRepository

    if not body:
        raise HTTPException(status_code=400, detail="Request body required")
    users = UserRepository(db)
    user = await users.get_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    settings_repo = SettingsRepository(db)
    current = await settings_repo.get_for_user(user["id"])
    current.update({k: v for k, v in body.items() if k in ("name", "avatar_url", "preferences")})
    await settings_repo.upsert(user["id"], current)
    return {"message": "Profile updated"}


@router.post("/change-password")
async def change_password(body: dict, db=Depends(get_db), email: str = Depends(get_current_user)):
    current_password = (body or {}).get("current_password", "")
    new_password = (body or {}).get("new_password", "")
    if not current_password or not new_password:
        raise HTTPException(status_code=400, detail="Current and new passwords required")
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")

    users = UserRepository(db)
    user = await users.get_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not verify_password(current_password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    new_hashed = hash_password(new_password)
    await users.update_password(user["id"], new_hashed)
    return {"message": "Password changed successfully"}


# ---------------------------------------------------------------------------
# API Key management
# ---------------------------------------------------------------------------


@router.post("/api-keys")
async def create_api_key(name: str = Query("default", min_length=1, max_length=100), db=Depends(get_db), email: str = Depends(get_current_user)):
    from app.services.security import generate_api_key as _gen_key

    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="API key name is required")
    name = name.strip()

    users = UserRepository(db)
    user = await users.get_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    raw_key, hashed_key = _gen_key()
    prefix = settings.api_key_prefix
    repo = APIKeyRepository(db)
    kid = await repo.create(user["id"], hashed_key, prefix, name)
    return {"id": kid, "api_key": raw_key, "name": name, "detail": "Save this key — it will not be shown again"}


@router.get("/api-keys")
async def list_api_keys(db=Depends(get_db), email: str = Depends(get_current_user)):
    users = UserRepository(db)
    user = await users.get_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    repo = APIKeyRepository(db)
    keys = await repo.list_for_user(user["id"])
    return {"api_keys": keys}


@router.delete("/api-keys/{key_id}", status_code=204)
async def revoke_api_key(key_id: int, db=Depends(get_db), email: str = Depends(get_current_user)):
    users = UserRepository(db)
    user = await users.get_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    repo = APIKeyRepository(db)
    existing = await repo.get_by_id(key_id, user["id"])
    if not existing:
        raise HTTPException(status_code=404, detail="API key not found")
    await repo.revoke(key_id, user["id"])
