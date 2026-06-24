"""Authentication routes."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.database.repositories.session import SessionRepository
from app.database.repositories.user import UserRepository
from app.models.schemas import AuthRequest, AuthResponse, RefreshRequest
from app.config import get_settings
from app.services.auth import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    hash_token,
    verify_password,
)

settings = get_settings()
router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@router.post("/signup", status_code=201)
async def signup(body: AuthRequest, db=Depends(get_db)):
    users = UserRepository(db)
    existing = await users.get_by_email(str(body.email))
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    await users.create(str(body.email), hash_password(body.password))
    return {"message": "User created successfully"}


@router.post("/login", response_model=AuthResponse)
async def login(body: AuthRequest, db=Depends(get_db)):
    users = UserRepository(db)
    row = await users.get_by_email(str(body.email))
    if not row or not verify_password(body.password, row["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(str(body.email))
    refresh_token = create_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days)

    sessions = SessionRepository(db)
    await sessions.create(row["id"], hash_token(refresh_token), expires_at)

    return AuthResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=AuthResponse)
async def refresh(body: RefreshRequest, db=Depends(get_db)):
    sessions = SessionRepository(db)
    token_hash = hash_token(body.refresh_token)
    session = await sessions.get_by_hash(token_hash)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

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

    access_token = create_access_token(user["email"])
    new_refresh = create_refresh_token()
    await sessions.delete(session["id"])
    new_expires = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days)
    await sessions.create(session["user_id"], hash_token(new_refresh), new_expires)
    return AuthResponse(access_token=access_token, refresh_token=new_refresh)


@router.post("/logout")
async def logout(body: RefreshRequest, db=Depends(get_db)):
    sessions = SessionRepository(db)
    session = await sessions.get_by_hash(hash_token(body.refresh_token))
    if session:
        await sessions.delete(session["id"])
    return {"message": "Logged out"}


@router.get("/me")
async def get_me(email: str = Depends(get_current_user)):
    return {"email": email}
