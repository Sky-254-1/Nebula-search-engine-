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
from app.routes.analytics import router as analytics_router
from app.routes.auth_extended import router as auth_extended_router
from app.routes.crawler import router as crawler_router
from app.routes.documents import router as documents_router
from app.routes.features import router as features_router
from app.routes.mfa import router as mfa_router
from app.routes.notifications import router as notifications_router
from app.routes.oauth import router as oauth_router
from app.routes.recommendations import router as recommendations_router
from app.routes.search_unified import router as search_unified_router
from app.routes.search_v2 import router as search_v2_router
from app.routes.users import router as users_router
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
    from app.database.engine import init_pool
    await init_pool()
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
    from app.database.engine import close_pool
    await close_pool()
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
        {"name": "Documents", "description": "Document upload and management"},
        {"name": "Storage", "description": "File upload and management (legacy)"},
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

# Register CSRF protection for cookie-based auth
from app.middleware.security import CSRFProtectionMiddleware
app.add_middleware(CSRFProtectionMiddleware)

# Register compression middleware
from app.middleware.compression import CompressionMiddleware
app.add_middleware(CompressionMiddleware, minimum_size=1024)
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
# Consolidated search API - search_unified includes all features from v1 and v2
app.include_router(search_unified_router)
# Legacy search routes (deprecated, kept for backward compatibility)
app.include_router(search.router)
app.include_router(ai.router)
app.include_router(audio.router)
app.include_router(users_router)  # New users domain
app.include_router(notifications_router)  # New notifications domain
app.include_router(analytics_router)  # New analytics domain
app.include_router(recommendations_router)  # New recommendations domain
app.include_router(documents_router)  # New documents domain
app.include_router(storage.router)  # Legacy storage routes (backward compatible)
app.include_router(vector.router)
app.include_router(webhooks_router)
app.include_router(crawler_router)  # Crawler management
app.include_router(features_router)  # Collections, bookmarks, saved searches

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