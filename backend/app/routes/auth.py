"""Authentication routes."""

from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.models.schemas import AuthRequest, AuthResponse
from app.services.auth import create_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@router.post("/signup", status_code=201)
async def signup(body: AuthRequest, db=Depends(get_db)):
    cursor = await db.execute("SELECT id FROM users WHERE email = ?", (str(body.email),))
    existing = await cursor.fetchone()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    hashed = hash_password(body.password)
    await db.execute(
        "INSERT INTO users (email, hashed_password) VALUES (?, ?)",
        (str(body.email), hashed),
    )
    await db.commit()
    return {"message": "User created successfully"}


@router.post("/login", response_model=AuthResponse)
async def login(body: AuthRequest, db=Depends(get_db)):
    cursor = await db.execute(
        "SELECT hashed_password FROM users WHERE email = ?",
        (str(body.email),),
    )
    row = await cursor.fetchone()
    if not row or not verify_password(body.password, row["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(str(body.email))
    return AuthResponse(access_token=token)


@router.get("/me")
async def get_me(email: str = Depends(get_current_user)):
    return {"email": email}
