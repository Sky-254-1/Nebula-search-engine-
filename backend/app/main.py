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
from app.docs.openapi_config import configure_openapi
from app.middleware.security import SecurityHeadersMiddleware
from app.middleware.versioning import VersioningMiddleware
from app.middleware.response import ResponseStandardizationMiddleware
from app.middleware.rate_limit import RateLimitHeadersMiddleware
from app.services.monitoring import MetricsMiddleware
from app.routes import admin, ai, audio, auth, health, search, storage, vector
from app.routes.auth_extended import router as auth_extended_router
from app.routes.mfa import router as mfa_router
from app.routes.oauth import router as oauth_router
from app.routes.webhooks import router as webhooks_router
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
    # Track last audit cleanup to run daily
    last_cleanup = 0.0
    while True:
        await asyncio.sleep(2.0)

        # Audit log retention: 90 days
        now = asyncio.get_event_loop().time()
        if now - last_cleanup > 86400: # 24 hours
            from app.database.engine import connect
            from app.database.repositories.audit import AuditRepository
            db = await connect()
            try:
                audit = AuditRepository(db)
                await audit.delete_old_logs(days=90)
                last_cleanup = now
                logger.info("Audit logs cleanup completed")
            except Exception:
                logger.exception("Audit logs cleanup failed")
            finally:
                await db.close()

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
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "Health", "description": "Health check endpoints"},
        {"name": "Auth", "description": "Authentication and authorization"},
        {"name": "Search", "description": "Web and hybrid search"},
        {"name": "Vector", "description": "Vector search and RAG"},
        {"name": "AI", "description": "AI-powered features"},
        {"name": "Audio", "description": "Audio transcription and processing"},
        {"name": "Storage", "description": "File upload and management"},
        {"name": "Webhooks", "description": "Webhook management"},
        {"name": "Admin", "description": "Administrative endpoints"},
    ],
)

# Add middleware in order (last added = first executed)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(VersioningMiddleware)
app.add_middleware(ResponseStandardizationMiddleware)
app.add_middleware(RateLimitHeadersMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS", "PUT", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(auth_extended_router)
app.include_router(mfa_router)
app.include_router(oauth_router)
app.include_router(admin.router)
app.include_router(search.router)
app.include_router(ai.router)
app.include_router(audio.router)
app.include_router(storage.router)
app.include_router(vector.router)
app.include_router(webhooks_router)

# Configure OpenAPI documentation
configure_openapi(app)


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