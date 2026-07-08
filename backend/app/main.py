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
import os
import signal
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from app.config import get_settings
from app.database import init_db
from app.middleware.rate_limit import get_limiter, rate_limit_exceeded_handler, slowapi_middleware
from app.middleware.security import SecurityHeadersMiddleware, CSRFProtectionMiddleware
from app.middleware.versioning import VersioningMiddleware
from app.middleware.response import ResponseStandardizationMiddleware
from app.middleware.rate_limit import RateLimitHeadersMiddleware
from app.services.monitoring import MetricsMiddleware
from app.routes import admin, ai, audio, auth, crawler, features, health, oauth, search, storage, vector
from app.routes.analytics import router as analytics_router
from app.routes.auth_extended import router as auth_extended_router
from app.routes.documents import router as documents_router
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
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

settings = get_settings()

# ---------------------------------------------------------------------------
# Structured logging — JSON in production, human-readable otherwise
# ---------------------------------------------------------------------------

_LOG_FORMAT_JSON = settings.log_json_format


class _JsonFormatter(logging.Formatter):
    """Minimal JSON log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        import json as _json

        log_entry: dict = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            log_entry["exc_info"] = self.formatException(record.exc_info)
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        return _json.dumps(log_entry, default=str)


_handler = logging.StreamHandler()
_handler.setLevel(settings.log_level.upper())

if _LOG_FORMAT_JSON:
    _handler.setFormatter(_JsonFormatter())
else:
    _handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    )

logging.basicConfig(level=settings.log_level.upper(), handlers=[_handler])
logger = logging.getLogger("nebula")

# ---------------------------------------------------------------------------
# Sentry initialisation
# ---------------------------------------------------------------------------

if settings.sentry_dsn:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.asyncio import AsyncioIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.app_env,
            traces_sample_rate=0.2 if settings.is_production else 1.0,
            integrations=[
                FastApiIntegration(),
                AsyncioIntegration(),
            ],
        )
        logger.info("Sentry SDK initialised")
    except Exception as exc:
        logger.warning("Failed to initialise Sentry: %s", exc)

# ---------------------------------------------------------------------------
# OpenTelemetry instrumentation
# ---------------------------------------------------------------------------

if settings.otel_exporter_otlp_endpoint:
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": settings.otel_service_name})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        _otel_instrumented = True
        logger.info(
            "OpenTelemetry initialised (endpoint=%s)", settings.otel_exporter_otlp_endpoint
        )
    except Exception as exc:
        _otel_instrumented = False
        logger.warning("Failed to initialise OpenTelemetry: %s", exc)
else:
    _otel_instrumented = False

# ---------------------------------------------------------------------------
# Helper: background workers
# ---------------------------------------------------------------------------


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
        if now - last_cleanup > 86400:  # 24 hours
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


# ---------------------------------------------------------------------------
# Health verification on startup
# ---------------------------------------------------------------------------


async def _verify_dependencies() -> list[str]:
    """Check all core dependencies and return a list of issues (empty = all good)."""
    issues: list[str] = []

    # Database
    from app.database.engine import connect

    try:
        db = await connect()
        await db.execute("SELECT 1")
        await db.close()
        logger.info("Database health check passed")
    except Exception as exc:
        issues.append(f"Database: {exc}")
        logger.warning("Database health check failed: %s", exc)

    # Cache
    try:
        if cache_service._redis:
            await cache_service._redis.ping()
            logger.info("Redis cache health check passed")
        else:
            logger.info("Cache health check: in-memory (no Redis configured)")
    except Exception as exc:
        issues.append(f"Redis cache: {exc}")
        logger.warning("Redis cache health check failed: %s", exc)

    # Storage directories
    _ensure_storage_dirs()
    for name, path in (
        ("uploads", settings.storage_uploads),
        ("cache", settings.storage_cache),
        ("vector", settings.storage_vector),
        ("indexes", settings.storage_indexes),
        ("exports", settings.storage_exports),
    ):
        if not Path(path).exists():
            issues.append(f"Storage dir '{name}' missing at {path}")

    return issues


# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------

try:
    from prometheus_client import Counter, Gauge, Histogram, generate_latest, REGISTRY

    _prom_requests = Counter(
        "nebula_http_requests_total",
        "Total HTTP requests",
        ["method", "path", "status"],
    )
    _prom_request_duration = Histogram(
        "nebula_http_request_duration_seconds",
        "HTTP request duration in seconds",
        ["method", "path"],
        buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    )
    _prom_active_requests = Gauge(
        "nebula_http_active_requests", "Active HTTP requests"
    )
    _prom_db_pool_size = Gauge("nebula_db_pool_size", "Database connection pool size")
    _prom_cache_hits = Counter("nebula_cache_hits_total", "Cache hit count")
    _prom_cache_misses = Counter("nebula_cache_misses_total", "Cache miss count")
    _HAS_PROMETHEUS = True
except ImportError:
    _HAS_PROMETHEUS = False
    logger.debug("prometheus_client not available — metrics disabled")


# ---------------------------------------------------------------------------
# Request ID middleware (inline, lightweight)
# ---------------------------------------------------------------------------


async def _request_id_middleware(request: Request, call_next):
    """Attach a unique request ID to every request and response."""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    start = time.monotonic()
    if _HAS_PROMETHEUS:
        _prom_active_requests.inc()

    response = await call_next(request)

    if _HAS_PROMETHEUS:
        _prom_active_requests.dec()
        _prom_requests.labels(
            method=request.method, path=request.url.path, status=response.status_code
        ).inc()
        _prom_request_duration.labels(
            method=request.method, path=request.url.path
        ).observe(time.monotonic() - start)

    response.headers["X-Request-ID"] = request_id
    return response


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ensure_storage_dirs()
    await init_db()
    from app.database.engine import init_pool
    await init_pool()
    await cache_service.connect()
    await job_queue.connect()
    from app.crawler.scheduler import crawl_scheduler

    await crawl_scheduler.start()

    # Verify deps on startup
    issues = await _verify_dependencies()
    if issues:
        logger.warning("Startup dependency issues: %s", "; ".join(issues))
    else:
        logger.info("All dependency health checks passed")

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
    from app.crawler.scheduler import crawl_scheduler

    await crawl_scheduler.stop()

    # Close any remaining database connections
    from app.database.engine import close_db

    try:
        await close_db()
    except Exception:
        pass

    logger.info("Nebula Search API shut down cleanly")


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Nebula Search API",
    description="A private, AI-powered, hybrid search engine backend.",
    version="1.1.0",
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

# --- SlowAPI rate limiter ---
# Note: Using custom rate limiter implementation, not SlowAPIMiddleware
# app.state.limiter = get_limiter()  # Not needed for custom implementation
# app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)  # Not used
# app.add_middleware(SlowAPIMiddleware)  # Removed - using custom RateLimitHeadersMiddleware instead

# --- Middleware stack (order matters) ---
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(VersioningMiddleware)
app.add_middleware(ResponseStandardizationMiddleware)
app.add_middleware(RateLimitHeadersMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(CSRFProtectionMiddleware)

# Register compression middleware
from app.middleware.compression import CompressionMiddleware
app.add_middleware(CompressionMiddleware, minimum_size=1024)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS", "PUT", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token", "X-Request-ID"],
)

# --- OpenTelemetry instrumentation (wraps ASGI app) ---
if _otel_instrumented:
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI OpenTelemetry instrumentation applied")
    except Exception as exc:
        logger.warning("OpenTelemetry instrument_app failed: %s", exc)

# --- Routes ---
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(search_unified_router)
# Enhanced search routes (v2) with semantic search, trending, analytics
app.include_router(search_v2_router)
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
app.include_router(crawler.router)  # Crawler management
app.include_router(features.router)  # Collections, bookmarks, saved searches

# --- Prometheus /metrics endpoint (mounted after routes) ---


@app.get("/metrics", include_in_schema=False)
async def metrics():
    """Prometheus metrics endpoint."""
    if not _HAS_PROMETHEUS:
        return PlainTextResponse(
            "prometheus_client not installed", status_code=501
        )
    return PlainTextResponse(
        generate_latest(REGISTRY).decode("utf-8"),
        media_type="text/plain; version=0.0.4",
    )


# --- Request ID middleware (applied last so it wraps everything) ---
app.middleware("http")(_request_id_middleware)


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None)
    logger.exception(
        "Unhandled error on %s %s (request_id=%s)",
        request.method,
        request.url.path,
        request_id,
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ---------------------------------------------------------------------------
# Graceful shutdown (OS signals)
# ---------------------------------------------------------------------------


async def _shutdown(sig: signal.Signals):
    logger.info("Received signal %s — shutting down", sig.name)
    # The lifespan context manager handles cleanup; we just need to stop accepting.
    for existing in asyncio.all_tasks():
        if existing is not asyncio.current_task():
            existing.cancel()


if os.name != "nt":  # Signals not fully supported on Windows
    try:
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(_shutdown(s)))
    except NotImplementedError:
        pass  # Some event loops don't support add_signal_handler


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

