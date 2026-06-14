import os
import uuid
import hashlib
import asyncio
import httpx
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, BackgroundTasks, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, validator
from sqlalchemy import create_engine, Column, String, Boolean, Integer, BigInteger, Text, DateTime, JSON, select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, declared_attr
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from jose import jwt, JWTError
from passlib.context import CryptContext
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# ---------- Configuration ----------
SECRET_KEY = "change-this-to-a-long-random-string-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 30

DATABASE_URL = "sqlite+aiosqlite:///./iois.db"
UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# AI settings (optional)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OLLAMA_MODEL = "mistral"

# ---------- Database ----------
class Base(DeclarativeBase):
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# ---------- Models ----------
class User(Base):
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    display_name = Column(String)
    plan = Column(String, default="free")
    preferences = Column(JSON, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)

class Session(Base):
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    token_hash = Column(Text, nullable=False)
    refresh_hash = Column(Text)
    ip_address = Column(String)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked = Column(Boolean, default=False)

class Document(Base):
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    filename = Column(Text, nullable=False)
    file_path = Column(Text)
    file_type = Column(String)
    file_size = Column(BigInteger)
    content_hash = Column(Text)
    is_indexed = Column(Boolean, default=False)
    index_status = Column(String, default="pending")
    word_count = Column(Integer)
    tags = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    indexed_at = Column(DateTime)

class SearchHistory(Base):
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    query = Column(Text, nullable=False)
    query_type = Column(String)
    result_count = Column(Integer)
    clicked_url = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class SavedPage(Base):
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    url = Column(Text, nullable=False)
    title = Column(Text)
    content = Column(Text)
    summary = Column(Text)
    saved_at = Column(DateTime, default=datetime.utcnow)

# ---------- Auth helpers ----------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(user_id: str) -> str:
    exp = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": user_id, "exp": exp, "type": "access"}, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    exp = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode({"sub": user_id, "exp": exp, "type": "refresh"}, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

# ---------- Dependency: current user ----------
bearer = HTTPBearer()

async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_token(creds.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user

# ---------- Pydantic schemas ----------
class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str

    @validator("username")
    def username_valid(cls, v):
        if not v.isalnum() or len(v) < 3:
            raise ValueError("Username must be alphanumeric and at least 3 characters")
        return v.lower()

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: dict

class SearchRequest(BaseModel):
    query: str
    filters: Optional[dict] = {}
    page: int = 1
    per_page: int = 10
    ai_summary: bool = True
    include_local: bool = True

# ---------- Simple offline index (in‑memory for demo) ----------
# In production you would use FAISS + SQLite FTS. This is a minimal example.
local_docs = {}  # doc_id -> {"title": str, "content": str, "user_id": str}

def index_document(doc_id: str, user_id: str, title: str, content: str):
    local_docs[doc_id] = {"user_id": user_id, "title": title, "content": content}

def search_local(query: str, user_id: str, top_k: int = 5) -> list:
    results = []
    q_lower = query.lower()
    for doc_id, doc in local_docs.items():
        if doc["user_id"] != user_id:
            continue
        score = doc["content"].lower().count(q_lower) + doc["title"].lower().count(q_lower) * 2
        if score > 0:
            results.append({
                "id": doc_id,
                "title": doc["title"],
                "snippet": doc["content"][:280],
                "source": "local",
                "score": score,
                "url": None,
            })
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]

# ---------- Online search (Wikipedia only) ----------
async def search_wikipedia(query: str, limit: int = 10) -> list:
    async with httpx.AsyncClient() as client:
        # search
        r1 = await client.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": limit,
                "origin": "*"
            }
        )
        data = r1.json()
        pages = data.get("query", {}).get("search", [])
        if not pages:
            return []
        page_ids = [str(p["pageid"]) for p in pages]
        r2 = await client.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "prop": "extracts|pageimages",
                "exintro": True,
                "explaintext": True,
                "exsentences": 3,
                "pithumbsize": 200,
                "pageids": "|".join(page_ids),
                "format": "json",
                "origin": "*"
            }
        )
        extracts = r2.json().get("query", {}).get("pages", {})
        results = []
        for p in pages:
            pid = str(p["pageid"])
            ext = extracts.get(pid, {})
            results.append({
                "id": f"wiki_{p['pageid']}",
                "title": p["title"],
                "snippet": ext.get("extract", p["snippet"]),
                "url": f"https://en.wikipedia.org/wiki/{p['title'].replace(' ', '_')}",
                "thumbnail": ext.get("thumbnail", {}).get("source"),
                "source": "wikipedia",
                "score": 1.0,
            })
        return results

# ---------- AI summary (Ollama or OpenAI) ----------
async def generate_summary(query: str, top_results: list) -> Optional[str]:
    if not top_results:
        return None
    context = "\n".join([f"- {r['title']}: {r['snippet'][:200]}" for r in top_results[:3]])
    prompt = f"Summarize the following search results for the query '{query}':\n\n{context}\n\nSummary:"
    try:
        # Try Ollama first
        if OLLAMA_BASE_URL:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{OLLAMA_BASE_URL}/api/generate",
                    json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
                )
                if resp.status_code == 200:
                    return resp.json().get("response", "").strip()
        # Fallback to OpenAI
        if OPENAI_API_KEY:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                    json={
                        "model": "gpt-3.5-turbo",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 200,
                        "temperature": 0.3
                    }
                )
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass
    return None

# ---------- FastAPI app ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(title="IOIS API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ---------- Auth endpoints ----------
@app.post("/api/v1/auth/register", response_model=TokenResponse)
async def register(req: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    # check duplicates
    existing = await db.execute(select(User).where((User.email == req.email) | (User.username == req.username)))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Email or username already taken")
    user = User(
        email=req.email,
        username=req.username,
        password_hash=hash_password(req.password),
        display_name=req.username,
    )
    db.add(user)
    await db.flush()
    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)
    # store session
    session = Session(
        user_id=user.id,
        token_hash=hash_password(access),
        refresh_hash=hash_password(refresh),
        ip_address=request.client.host,
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )
    db.add(session)
    await db.commit()
    return TokenResponse(access_token=access, refresh_token=refresh, user={"id": user.id, "email": user.email, "username": user.username})

@app.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    user.last_login = datetime.utcnow()
    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)
    session = Session(
        user_id=user.id,
        token_hash=hash_password(access),
        refresh_hash=hash_password(refresh),
        ip_address=request.client.host,
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )
    db.add(session)
    await db.commit()
    return TokenResponse(access_token=access, refresh_token=refresh, user={"id": user.id, "email": user.email, "username": user.username})

@app.get("/api/v1/auth/me")
async def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "username": user.username, "display_name": user.display_name}

# ---------- Search endpoint ----------
@app.post("/api/v1/search")
async def search(req: SearchRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # 1. Online search
    online_results = await search_wikipedia(req.query, limit=req.per_page)
    # 2. Offline search (if requested)
    offline_results = []
    if req.include_local:
        offline_results = search_local(req.query, user.id, top_k=5)
    # 3. Merge and rank
    all_results = online_results + offline_results
    all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
    # 4. Paginate
    start = (req.page - 1) * req.per_page
    page_results = all_results[start:start + req.per_page]
    # 5. AI summary
    ai_summary = None
    if req.ai_summary and page_results:
        ai_summary = await generate_summary(req.query, page_results)
    # 6. Save history
    hist = SearchHistory(user_id=user.id, query=req.query, result_count=len(all_results))
    db.add(hist)
    await db.commit()
    return {
        "query": req.query,
        "total": len(all_results),
        "page": req.page,
        "per_page": req.per_page,
        "results": page_results,
        "ai_overview": {"text": ai_summary, "confidence": 0.8} if ai_summary else None,
        "elapsed_ms": 0,
    }

# ---------- Document upload (simplified) ----------
@app.post("/api/v1/documents/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    content_hash = hashlib.sha256(content).hexdigest()
    # Save file
    doc_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{user.id}_{doc_id}_{file.filename}"
    with open(file_path, "wb") as f:
        f.write(content)
    # Extract text (very basic, for demo)
    text_content = ""
    if file.filename.endswith(".txt") or file.filename.endswith(".md"):
        text_content = content.decode("utf-8", errors="ignore")
    elif file.filename.endswith(".pdf"):
        # You would add PyMuPDF or similar. Here a placeholder.
        text_content = "PDF text extraction not implemented in single-file demo."
    else:
        text_content = "Unsupported file type for full text extraction."
    # Index in-memory
    index_document(doc_id, user.id, file.filename, text_content)
    doc = Document(
        id=doc_id,
        user_id=user.id,
        filename=file.filename,
        file_path=str(file_path),
        file_type=file.filename.split(".")[-1],
        file_size=len(content),
        content_hash=content_hash,
        is_indexed=True,
        word_count=len(text_content.split()),
    )
    db.add(doc)
    await db.commit()
    return {"id": doc_id, "filename": file.filename, "status": "indexed"}

@app.get("/api/v1/documents")
async def list_documents(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.user_id == user.id))
    docs = result.scalars().all()
    return {"documents": [{"id": d.id, "filename": d.filename, "is_indexed": d.is_indexed, "created_at": d.created_at.isoformat()} for d in docs]}

# ---------- Health ----------
@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}

# ---------- Run ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
