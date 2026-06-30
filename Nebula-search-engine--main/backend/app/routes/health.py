"""Health and root endpoints."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import get_settings
from app.database import get_db
from app.models.schemas import HealthResponse
from app.services.cache import cache_service
from app.services.ai import check_ai_health

logger = logging.getLogger("nebula.health")
router = APIRouter(tags=["Health"])
settings = get_settings()


class DeepHealthResponse(HealthResponse):
    db_reachable: bool = False
    cache_reachable: bool = False
    ai_available: bool = False
    checks: dict = {}


@router.get("/")
async def root():
    return {"message": "Nebula Search API is running.", "docs": "/docs", "version": "1.0.0"}


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        version="1.1.0",
        environment=settings.app_env,
        timestamp=datetime.now(timezone.utc).isoformat(),
        database="postgresql" if settings.uses_postgres else "sqlite",
        cache="redis" if cache_service._redis else "memory",
    )


@router.get("/health/deep", response_model=DeepHealthResponse)
async def deep_health_check(db=Depends(get_db)):
    checks = {}
    db_ok = cache_ok = ai_ok = False

    try:
        row = await db.fetchone("SELECT 1 as ok")
        db_ok = row is not None
        checks["database"] = "reachable" if db_ok else "unreachable"
    except Exception as exc:
        checks["database"] = f"error: {exc}"
        logger.warning("Deep health DB check failed: %s", exc)

    try:
        if cache_service._redis:
            await cache_service._redis.ping()
        cache_ok = True
        checks["cache"] = "redis_connected" if cache_service._redis else "in_memory"
    except Exception as exc:
        checks["cache"] = f"redis_error: {exc}"
        logger.warning("Deep health cache check failed: %s", exc)

    try:
        ai_ok = await check_ai_health()
        checks["ai"] = "available" if ai_ok else "unavailable"
    except Exception as exc:
        checks["ai"] = f"error: {exc}"

    overall_status = "healthy" if (db_ok and cache_ok) else "degraded"
    return DeepHealthResponse(
        status=overall_status,
        version="1.1.0",
        environment=settings.app_env,
        timestamp=datetime.now(timezone.utc).isoformat(),
        database="postgresql" if settings.uses_postgres else "sqlite",
        cache="redis" if cache_service._redis else "memory",
        db_reachable=db_ok,
        cache_reachable=cache_ok,
        ai_available=ai_ok,
        checks=checks,
    )
