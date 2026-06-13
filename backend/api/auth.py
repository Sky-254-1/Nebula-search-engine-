from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from db.database import async_session
from db.models import User
from pydantic import BaseModel
from config import SECRET_KEY

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserSignup(BaseModel):
    email: str
    password: str
    name: str | None = None

class UserLogin(BaseModel):
    email: str
    password: str

async def get_db():
    async with async_session() as session:
        yield session

@router.post("/signup")
async def signup(data: UserSignup, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=data.email, hashed_password=pwd_context.hash(data.password), name=data.name)
    db.add(user)
    await db.commit()
    return {"msg": "User created"}

@router.post("/login")
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalars().first()
    if not user or not pwd_context.verify(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = jwt.encode(
        {"sub": str(user.id), "exp": datetime.utcnow() + timedelta(hours=24)},
        SECRET_KEY, algorithm="HS256"
    )
    return {"access_token": token, "token_type": "bearer"}