"""
Nebula Search Engine — Backend API
A private, online and offline-capable, AI-powered, hybrid search engine.

Run:
    uvicorn app.main:app --reload

Docs:
    http://localhost:8000/docs
"""

import os
import re
import time
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from contextlib import asynccontextmanager

import aiosqlite
import httpx
import jwt
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field

load_dotenv()

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL", "nebula.db")
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
REDIS_URL = os.getenv("REDIS_URL", "")
APP_ENV = os.getenv("APP_ENV", "development")
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

# ──────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────

DB_PATH = DATABASE_URL if not DATABASE_URL.startswith("postgresql") else "nebula.db"

async def get_db():
    """Yield an aiosqlite connection."""
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        yield conn

async def init_db():
    """Create tables if they don't exist."""
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS search_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                query TEXT NOT NULL,
                backend TEXT,
                results_count INTEGER DEFAULT 0,
                searched_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        await conn.commit()

# ──────────────────────────────────────────────
# Password hashing (PBKDF2 — no extra dependency)
# ──────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a password with PBKDF2-SHA256 and a random salt."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
    return f"{salt}${dk.hex()}"

def verify_password(password: str, stored: str) -> bool:
    """Verify a password against the stored hash."""
    try:
        salt, hashed = stored.split("$", 1)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
        return secrets.compare_digest(dk.hex(), hashed)
    except Exception:
        return False

# ──────────────────────────────────────────────
# JWT helpers
# ──────────────────────────────────────────────

def create_token(email: str) -> str:
    payload = {
        "sub": email,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(request: Request):
    """Dependency: extract and validate JWT from Authorization header."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = auth[7:]
    payload = decode_token(token)
    return payload.get("sub")

# ──────────────────────────────────────────────
# Rate limiter (in-memory, per-IP)
# ──────────────────────────────────────────────

_rate_store: dict[str, list[float]] = {}

async def rate_limit(request: Request):
    """Simple sliding-window rate limiter."""
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = _rate_store.setdefault(ip, [])
    # Remove entries older than 60s
    _rate_store[ip] = [t for t in window if now - t < 60]
    if len(_rate_store[ip]) >= RATE_LIMIT_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again shortly.")
    _rate_store[ip].append(now)

# ──────────────────────────────────────────────
# Pydantic models
# ──────────────────────────────────────────────

class AuthRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    password: str = Field(..., min_length=6, max_length=128)

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class AIRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)

class AIResponse(BaseModel):
    answer: str

class SearchResult(BaseModel):
    title: str
    snippet: str
    url: str
    source: str

class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    timestamp: str

# ──────────────────────────────────────────────
# Lifespan
# ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

# ──────────────────────────────────────────────
# FastAPI app
# ──────────────────────────────────────────────

app = FastAPI(
    title="Nebula Search API",
    description="A private, AI-powered, hybrid search engine backend.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# Health check
# ──────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {"message": "Nebula Search API is running.", "docs": "/docs"}

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        environment=APP_ENV,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

# ══════════════════════════════════════════════
# AUTH ROUTES
# ══════════════════════════════════════════════

@app.post("/api/v1/auth/signup", tags=["Auth"], status_code=201)
async def signup(body: AuthRequest, db=Depends(get_db)):
    """Register a new user."""
    # Check if email already exists
    cursor = await db.execute("SELECT id FROM users WHERE email = ?", (body.email,))
    existing = await cursor.fetchone()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    hashed = hash_password(body.password)
    await db.execute(
        "INSERT INTO users (email, hashed_password) VALUES (?, ?)",
        (body.email, hashed),
    )
    await db.commit()
    return {"message": "User created successfully"}

@app.post("/api/v1/auth/login", response_model=AuthResponse, tags=["Auth"])
async def login(body: AuthRequest, db=Depends(get_db)):
    """Authenticate and receive a JWT token."""
    cursor = await db.execute(
        "SELECT hashed_password FROM users WHERE email = ?", (body.email,)
    )
    row = await cursor.fetchone()
    if not row or not verify_password(body.password, row["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(body.email)
    return AuthResponse(access_token=token)

@app.get("/api/v1/auth/me", tags=["Auth"])
async def get_me(email: str = Depends(get_current_user)):
    """Return the current authenticated user's email."""
    return {"email": email}

# ══════════════════════════════════════════════
# SEARCH ROUTES
# ══════════════════════════════════════════════

async def _search_wikipedia(query: str, page: int, page_size: int) -> list[dict]:
    """Search Wikipedia's public API."""
    offset = (page - 1) * page_size
    url = (
        f"https://en.wikipedia.org/w/api.php"
        f"?action=query&list=search&srsearch={query}"
        f"&srlimit={page_size}&sroffset={offset}"
        f"&format=json&origin=*"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    results = []
    for item in data.get("query", {}).get("search", []):
        # Strip HTML from snippet
        snippet = item.get("snippet", "")
        snippet = re.sub(r"<[^>]+>", "", snippet)
        title = item.get("title", "")
        results.append({
            "title": title,
            "snippet": snippet,
            "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
            "source": "wikipedia",
        })
    return results

async def _search_brave(query: str, api_key: str, page: int, page_size: int) -> list[dict]:
    """Search via Brave Search API."""
    if not api_key:
        raise HTTPException(status_code=400, detail="Brave API key not configured on server")
    offset = (page - 1) * page_size
    url = f"https://api.search.brave.com/res/v1/web/search?q={query}&count={page_size}&offset={offset}"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers={"X-Subscription-Token": api_key, "Accept": "application/json"})
        resp.raise_for_status()
        data = resp.json()

    results = []
    for item in data.get("web", {}).get("results", []):
        results.append({
            "title": item.get("title", ""),
            "snippet": item.get("description", ""),
            "url": item.get("url", ""),
            "source": "brave",
        })
    return results

async def _search_serpapi(query: str, api_key: str, page: int, page_size: int) -> list[dict]:
    """Search via SerpAPI (Google results)."""
    if not api_key:
        raise HTTPException(status_code=400, detail="SerpAPI key not configured on server")
    start = (page - 1) * page_size
    url = (
        f"https://serpapi.com/search.json"
        f"?q={query}&api_key={api_key}&engine=google"
        f"&start={start}&num={page_size}"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    results = []
    for item in data.get("organic_results", []):
        results.append({
            "title": item.get("title", ""),
            "snippet": item.get("snippet", ""),
            "url": item.get("link", ""),
            "source": "serpapi",
        })
    return results

@app.get(
    "/api/v1/search/web",
    response_model=list[SearchResult],
    tags=["Search"],
    dependencies=[Depends(rate_limit)],
)
async def web_search(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    backend: str = Query("wikipedia", description="Search backend: wikipedia, brave, serpapi"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Results per page"),
    email: str = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Perform a web search using the specified backend.
    Requires authentication.
    """
    # Log the search
    cursor = await db.execute("SELECT id FROM users WHERE email = ?", (email,))
    user = await cursor.fetchone()
    user_id = user["id"] if user else None

    try:
        if backend == "wikipedia":
            results = await _search_wikipedia(q, page, page_size)
        elif backend == "brave":
            results = await _search_brave(q, BRAVE_API_KEY, page, page_size)
        elif backend == "serpapi":
            results = await _search_serpapi(q, SERPAPI_KEY, page, page_size)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown backend: {backend}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Search backend error: {e.response.status_code}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Search backend unreachable: {str(e)}")

    # Log search
    await db.execute(
        "INSERT INTO search_logs (user_id, query, backend, results_count) VALUES (?, ?, ?, ?)",
        (user_id, q, backend, len(results)),
    )
    await db.commit()

    return results

# ══════════════════════════════════════════════
# AI ROUTES
# ══════════════════════════════════════════════

async def _ai_openai(prompt: str) -> str:
    """Get an answer from an OpenAI-compatible API."""
    url = f"{OPENAI_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Nebula, a helpful and concise search assistant. "
                    "Provide clear, accurate, and brief answers. "
                    "If you're unsure, say so. Do not make up facts."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 500,
        "temperature": 0.7,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    return data["choices"][0]["message"]["content"].strip()

async def _ai_duckduckgo(prompt: str) -> Optional[str]:
    """Fallback: get an instant answer from DuckDuckGo."""
    url = f"https://api.duckduckgo.com/?q={prompt}&format=json&no_redirect=1&t=nebula"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
    answer = data.get("AbstractText") or data.get("Answer") or None
    return answer

@app.post(
    "/api/v1/ai/ask",
    response_model=AIResponse,
    tags=["AI"],
    dependencies=[Depends(rate_limit)],
)
async def ai_ask(
    body: AIRequest,
    email: str = Depends(get_current_user),
):
    """
    Get an AI-powered answer.
    Uses OpenAI if API key is configured, otherwise falls back to DuckDuckGo instant answers.
    """
    answer = None

    # Try OpenAI first
    if OPENAI_API_KEY:
        try:
            answer = await _ai_openai(body.prompt)
        except httpx.HTTPStatusError as e:
            # Log but don't fail — fall through to DuckDuckGo
            print(f"OpenAI error: {e.response.status_code} — falling back to DuckDuckGo")
        except httpx.RequestError as e:
            print(f"OpenAI unreachable: {e} — falling back to DuckDuckGo")

    # Fallback to DuckDuckGo
    if not answer:
        try:
            answer = await _ai_duckduckgo(body.prompt)
        except Exception:
            pass

    if not answer:
        raise HTTPException(
            status_code=404,
            detail="No AI answer available for this query. Try rephrasing.",
        )

    return AIResponse(answer=answer)

# ══════════════════════════════════════════════
# SYNTHESIS ROUTE (bonus — supports the Synthesize button)
# ══════════════════════════════════════════════

class SynthesizeRequest(BaseModel):
    snippets: list[str] = Field(..., min_length=1, max_length=20)
    query: str = Field(..., min_length=1, max_length=500)

class SynthesizeResponse(BaseModel):
    synthesis: str

@app.post(
    "/api/v1/ai/synthesize",
    response_model=SynthesizeResponse,
    tags=["AI"],
    dependencies=[Depends(rate_limit)],
)
async def synthesize(
    body: SynthesizeRequest,
    email: str = Depends(get_current_user),
):
    """
    Synthesize multiple search result snippets into a coherent summary.
    Uses OpenAI if available, otherwise does a simple concatenation.
    """
    combined = "\n".join(f"- {s}" for s in body.snippets[:10])

    if OPENAI_API_KEY:
        prompt = (
            f"The user searched for: \"{body.query}\"\n\n"
            f"Here are the top search result snippets:\n{combined}\n\n"
            f"Synthesize these into a clear, concise summary paragraph (3-5 sentences). "
            f"Do not add information not present in the snippets."
        )
        try:
            synthesis = await _ai_openai(prompt)
            return SynthesizeResponse(synthesis=synthesis)
        except Exception:
            pass

    # Fallback: simple concatenation with transitions
    transitions = [
        "According to search results, ",
        "Additionally, ",
        "Furthermore, ",
        "It is also noted that ",
        "Moreover, ",
    ]
    parts = []
    for i, snippet in enumerate(body.snippets[:5]):
        prefix = transitions[i] if i < len(transitions) else ""
        parts.append(f"{prefix}{snippet.strip().rstrip('.')}.")
    return SynthesizeResponse(synthesis=" ".join(parts))

# ══════════════════════════════════════════════
# ERROR HANDLERS
# ══════════════════════════════════════════════

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    print(f"Unhandled error: {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

# ──────────────────────────────────────────────
# Run directly: python -m app.main
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=(APP_ENV == "development"),
    )
