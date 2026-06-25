"""
Nebula Search Engine — Backend API
A private, online and offline-capable, AI-powered, hybrid search engine.

Run:
    uvicorn app.main:app --reload

Docs:
    http://localhost:8000/docs
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import init_db
from app.middleware.security import SecurityHeadersMiddleware
from app.routes import ai, auth, health, search, storage, vector
from app.services.cache import cache_service
from app.services.queue import job_queue

settings = get_settings()

logging.basicConfig(
    level=logging.INFO if settings.is_production else logging.DEBUG,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("nebula")


async def _process_index_jobs() -> None:
    """Drain in-memory index jobs when Redis is unavailable."""
    from app.database.engine import connect
    from vector.pipeline import index_document

    while True:
        job = await job_queue.dequeue()
        if not job:
            break
        if job.get("type") != "index_document":
            continue
        payload = job.get("payload", {})
        doc_id = payload.get("document_id")
        user_id = payload.get("user_id")
        if not doc_id or not user_id:
            continue
        db = await connect()
        try:
            await index_document(db, doc_id, user_id)
        except Exception:
            logger.exception("Background index failed for doc %s", doc_id)
        finally:
            await db.close()


async def _background_worker_loop() -> None:
    while True:
        await asyncio.sleep(2.0)
        if job_queue._redis:
            continue
        try:
            await _process_index_jobs()
        except Exception:
            logger.exception("Background worker error")


def _ensure_storage_dirs() -> None:
    for path in (
        settings.storage_uploads,
        settings.storage_cache,
        settings.storage_vector,
        settings.storage_indexes,
        settings.storage_exports,
    ):
        Path(path).mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ensure_storage_dirs()
    await init_db()
    await cache_service.connect()
    await job_queue.connect()
    worker_task = asyncio.create_task(_background_worker_loop())
    logger.info(
        "Nebula Search API started (env=%s, db=%s)",
        settings.app_env,
        "postgresql" if settings.uses_postgres else "sqlite",
    )
    yield
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    await cache_service.close()
    await job_queue.close()


app = FastAPI(
    title="Nebula Search API",
    description="A private, AI-powered, hybrid search engine backend.",
    version="1.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(search.router)
app.include_router(ai.router)
app.include_router(storage.router)
app.include_router(vector.router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=not settings.is_production,
    )
