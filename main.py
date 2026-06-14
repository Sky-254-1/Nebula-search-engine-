"""
Nebula Search – main FastAPI application.

This file is the entry point for the backend.
It sets up CORS, mounts the API routers, and serves the static frontend.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from config import SECRET_KEY
from db.database import engine, Base
from api import auth, search, ai, documents


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Create database tables on startup (if they don't exist yet)
    and clean up resources on shutdown.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Optionally: close connections, etc.


# Create the FastAPI application
app = FastAPI(
    title="Nebula Search API",
    version="0.2.0",
    lifespan=lifespan,
    description="Private, offline‑capable, AI‑powered search engine backend.",
)

# ---------------------------------------------------------------------
# CORS Configuration
# ---------------------------------------------------------------------
# For production, replace the origins with your actual frontend domain(s).
# Using credentials (JWT tokens) requires explicit origins, NOT a wildcard.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # React / Vite dev server
        "http://localhost:8000",   # direct access to FastAPI
        # Add your production domain here later
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------
# API Routers
# ---------------------------------------------------------------------
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(search.router, prefix="/api/v1/search", tags=["Search"])
app.include_router(ai.router, prefix="/api/v1/ai", tags=["AI"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])

# ---------------------------------------------------------------------
# Static files (frontend)
# ---------------------------------------------------------------------
# Place your "index.html" inside the "static/" folder next to main.py
# The server will automatically serve it at http://localhost:8000/
app.mount("/", StaticFiles(directory="static", html=True), name="static")
