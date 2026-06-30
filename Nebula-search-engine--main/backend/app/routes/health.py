"""Health and root endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter

from app.config import get_settings
from app.models.schemas import HealthResponse
from app.services.cache import cache_service

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get("/")
async def root():
    return {"message": "Nebula Search API is running.", "docs": "/docs", "version": "1.0.0"}


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        environment=settings.app_env,
        timestamp=datetime.now(timezone.utc).isoformat(),
        database="postgresql" if settings.uses_postgres else "sqlite",
        cache="redis" if cache_service._redis else "memory",
    )
