from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api import auth, search, ai, documents
from db.database import engine, Base
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(title="Nebula Search API", version="0.1.0", lifespan=lifespan)

# ✅ Correct CORS for credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes first
app.include_router(auth.router, prefix="/api/v1/auth")
app.include_router(search.router, prefix="/api/v1/search")
app.include_router(ai.router, prefix="/api/v1/ai")
app.include_router(documents.router, prefix="/api/v1/documents")

# Then static files (frontend)
app.mount("/", StaticFiles(directory="static", html=True), name="static")