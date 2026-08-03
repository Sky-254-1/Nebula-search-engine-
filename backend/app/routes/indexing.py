"""Indexing routes with health endpoints."""

from fastapi import APIRouter

from app.indexing.health import router as indexing_health_router

router = APIRouter(prefix="/api/v1/indexing", tags=["Indexing"])

# Include health endpoints
router.include_router(indexing_health_router)

__all__ = ["router", "indexing_health_router"]
