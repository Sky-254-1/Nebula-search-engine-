"""Health monitoring for vector worker service."""

import time
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import APIRouter
import os

router = APIRouter(prefix="/api/v1/vector", tags=["Vector Health"])


def check_faiss_index() -> Dict[str, Any]:
    """Check FAISS index status."""
    start = time.time()
    try:
        from app.config import get_settings
        settings = get_settings()
        vector_path = settings.storage_vector
        os.makedirs(vector_path, exist_ok=True)
        
        # Check if index exists or can be created
        test_index = os.path.join(vector_path, ".health_check.index")
        if not os.path.exists(test_index):
            with open(test_index, "w") as f:
                f.write("ok")
            os.remove(test_index)
        
        response_time_ms = int((time.time() - start) * 1000)
        return {
            "status": "healthy",
            "response_time_ms": response_time_ms,
            "path": str(vector_path)
        }
    except Exception as exc:
        return {
            "status": "unhealthy",
            "response_time_ms": int((time.time() - start) * 1000),
            "error": str(exc)
        }


def check_ai_provider() -> Dict[str, Any]:
    """Check AI provider connectivity for vector embeddings."""
    start = time.time()
    try:
        from app.providers.ai.router import AIProviderRouter
        router = AIProviderRouter()
        provider_info = router.get_provider_info()
        
        response_time_ms = int((time.time() - start) * 1000)
        return {
            "status": "healthy",
            "response_time_ms": response_time_ms,
            "provider": provider_info.get("provider", "unknown"),
            "model": provider_info.get("model", "unknown")
        }
    except Exception as exc:
        return {
            "status": "unhealthy",
            "response_time_ms": int((time.time() - start) * 1000),
            "error": str(exc)
        }


@router.get("/health")
async def vector_liveness() -> Dict[str, Any]:
    """
    Vector worker liveness check.
    Returns 200 if vector worker process is running.
    """
    return {
        "status": "alive",
        "service": "nebula-vector-worker",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/health/ready")
async def vector_readiness() -> Dict[str, Any]:
    """
    Vector worker readiness check.
    Returns 200 if vector worker is ready to process requests.
    Checks FAISS index and AI provider connectivity.
    """
    faiss_status = check_faiss_index()
    ai_status = check_ai_provider()
    
    overall_status = "ready"
    if faiss_status["status"] == "unhealthy" or ai_status["status"] == "unhealthy":
        overall_status = "not_ready"
    
    return {
        "status": overall_status,
        "service": "nebula-vector-worker",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dependencies": {
            "faiss_index": faiss_status,
            "ai_provider": ai_status
        }
    }
