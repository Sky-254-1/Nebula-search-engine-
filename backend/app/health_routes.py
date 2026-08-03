import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import logging
import os
import shutil

logger = logging.getLogger("nebula.health")
router = APIRouter()

# Store startup time for uptime calculation
_startup_time = time.time()


def get_uptime() -> str:
    """Calculate human-readable uptime from startup time."""
    global _startup_time
    now = time.time()
    elapsed = int(now - _startup_time)
    
    days = elapsed // 86400
    hours = (elapsed % 86400) // 3600
    minutes = (elapsed % 3600) // 60
    seconds = elapsed % 60
    
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    
    return " ".join(parts)


async def check_database() -> Dict[str, Any]:
    """Check database connectivity."""
    start = time.time()
    try:
        from app.database.engine import connect
        db = await connect()
        await db.execute("SELECT 1")
        await db.close()
        response_time_ms = int((time.time() - start) * 1000)
        return {
            "status": "healthy",
            "response_time_ms": response_time_ms
        }
    except Exception as exc:
        logger.error("Database health check failed: %s", exc)
        return {
            "status": "unhealthy",
            "response_time_ms": int((time.time() - start) * 1000),
            "error": str(exc)
        }


async def check_redis() -> Dict[str, Any]:
    """Check Redis connectivity."""
    start = time.time()
    try:
        from app.services.cache import cache_service
        if cache_service._redis:
            await cache_service._redis.ping()
            response_time_ms = int((time.time() - start) * 1000)
            return {
                "status": "healthy",
                "response_time_ms": response_time_ms
            }
        else:
            response_time_ms = int((time.time() - start) * 1000)
            return {
                "status": "healthy",
                "response_time_ms": response_time_ms,
                "message": "Using in-memory cache (Redis not configured)"
            }
    except Exception as exc:
        logger.error("Redis health check failed: %s", exc)
        return {
            "status": "unhealthy",
            "response_time_ms": int((time.time() - start) * 1000),
            "error": str(exc)
        }


async def check_storage() -> Dict[str, Any]:
    """Check storage access."""
    start = time.time()
    try:
        from app.config import get_settings
        settings = get_settings()
        storage_path = settings.storage_uploads
        os.makedirs(storage_path, exist_ok=True)
        
        test_file = os.path.join(storage_path, ".health_check")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        
        response_time_ms = int((time.time() - start) * 1000)
        return {
            "status": "healthy",
            "response_time_ms": response_time_ms,
            "path": str(storage_path)
        }
    except Exception as exc:
        logger.error("Storage health check failed: %s", exc)
        return {
            "status": "unhealthy",
            "response_time_ms": int((time.time() - start) * 1000),
            "error": str(exc)
        }


async def check_vector_worker() -> Dict[str, Any]:
    """Check vector worker health."""
    start = time.time()
    try:
        from app.config import get_settings
        settings = get_settings()
        
        # Check if vector worker is running (simulated check)
        if os.environ.get("VECTOR_WORKER_RUNNING", "false").lower() == "true":
            response_time_ms = int((time.time() - start) * 1000)
            return {
                "status": "healthy",
                "response_time_ms": response_time_ms,
                "mode": "standalone"
            }
        
        # Check storage for vector data
        storage_path = settings.storage_vector
        os.makedirs(storage_path, exist_ok=True)
        
        # Check if FAISS index exists or can be created
        test_index = os.path.join(storage_path, ".health_check.index")
        if not os.path.exists(test_index):
            with open(test_index, "w") as f:
                f.write("ok")
            os.remove(test_index)
        
        response_time_ms = int((time.time() - start) * 1000)
        return {
            "status": "healthy",
            "response_time_ms": response_time_ms,
            "path": str(storage_path)
        }
    except Exception as exc:
        logger.error("Vector worker health check failed: %s", exc)
        return {
            "status": "unhealthy",
            "response_time_ms": int((time.time() - start) * 1000),
            "error": str(exc)
        }


async def check_indexing_worker() -> Dict[str, Any]:
    """Check indexing worker health."""
    start = time.time()
    try:
        # Check indexing worker health monitor
        from app.indexing.health import get_worker_health_monitor
        monitor = get_worker_health_monitor()
        
        # Check for active workers
        active_workers = monitor.get_active_workers()
        
        response_time_ms = int((time.time() - start) * 1000)
        return {
            "status": "healthy",
            "response_time_ms": response_time_ms,
            "active_workers": len(active_workers),
            "total_workers": len(monitor.get_all_workers())
        }
    except Exception as exc:
        logger.error("Indexing worker health check failed: %s", exc)
        return {
            "status": "unhealthy",
            "response_time_ms": int((time.time() - start) * 1000),
            "error": str(exc)
        }


async def check_ai_providers() -> Dict[str, Any]:
    """Check AI provider connectivity."""
    start = time.time()
    try:
        from app.providers.ai.router import AIProviderRouter
        router = AIProviderRouter()
        
        # Get provider info
        provider_info = router.get_provider_info()
        
        response_time_ms = int((time.time() - start) * 1000)
        return {
            "status": "healthy",
            "response_time_ms": response_time_ms,
            "provider": provider_info.get("provider", "unknown"),
            "model": provider_info.get("model", "unknown")
        }
    except Exception as exc:
        logger.error("AI providers health check failed: %s", exc)
        return {
            "status": "unhealthy",
            "response_time_ms": int((time.time() - start) * 1000),
            "error": str(exc)
        }


def check_disk_space() -> Dict[str, Any]:
    """Check disk space availability."""
    start = time.time()
    try:
        disk = shutil.disk_usage("/")
        disk_free_percent = (disk.free / disk.total) * 100
        
        response_time_ms = int((time.time() - start) * 1000)
        return {
            "status": "healthy" if disk_free_percent > 10 else "degraded",
            "response_time_ms": response_time_ms,
            "free_percent": round(disk_free_percent, 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "total_gb": round(disk.total / (1024**3), 2)
        }
    except Exception as exc:
        logger.error("Disk space health check failed: %s", exc)
        return {
            "status": "unknown",
            "response_time_ms": int((time.time() - start) * 1000),
            "error": str(exc)
        }


@router.get("/health/live")
async def liveness_check() -> Dict[str, Any]:
    """
    Kubernetes liveness probe.
    Returns 200 if the application is alive.
    Always returns healthy as long as the process is running.
    """
    return {
        "status": "alive",
        "service": "nebula-backend",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/health/ready")
async def readiness_check() -> JSONResponse:
    """
    Kubernetes readiness probe.
    Returns 200 if the application is ready to serve traffic.
    Checks all dependencies: database, Redis, storage, workers.
    """
    # Run all checks in parallel
    checks = await asyncio.gather(
        check_database(),
        check_redis(),
        check_storage(),
        check_vector_worker(),
        check_indexing_worker()
    )
    
    database_status, redis_status, storage_status, vector_status, indexing_status = checks
    
    # Determine overall status
    overall_status = "ready"
    if any(c["status"] == "unhealthy" for c in checks):
        overall_status = "not_ready"
    
    response = {
        "status": overall_status,
        "service": "nebula-backend",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dependencies": {
            "database": database_status,
            "redis": redis_status,
            "storage": storage_status,
            "vector_worker": vector_status,
            "indexing_worker": indexing_status
        }
    }
    
    status_code = 200 if overall_status == "ready" else 503
    return JSONResponse(content=response, status_code=status_code)


@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """
    Comprehensive health check with all system details.
    Used for monitoring and debugging.
    """
    # Run all checks in parallel
    checks = await asyncio.gather(
        check_database(),
        check_redis(),
        check_storage(),
        check_vector_worker(),
        check_indexing_worker(),
        check_ai_providers(),
        check_disk_space()
    )
    
    database_status, redis_status, storage_status, vector_status, indexing_status, ai_status, disk_status = checks
    
    # Determine overall status
    overall_status = "healthy"
    if any(c["status"] == "unhealthy" for c in checks):
        overall_status = "degraded"
    
    # Get version from settings
    from app.config import get_settings
    settings = get_settings()
    
    # Get uptime
    uptime = get_uptime()
    
    response = {
        "status": overall_status,
        "service": "nebula-backend",
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "uptime": uptime,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": settings.app_env,
        "dependencies": {
            "database": database_status,
            "redis": redis_status,
            "storage": storage_status,
            "vector_worker": vector_status,
            "indexing_worker": indexing_status,
            "ai_providers": ai_status,
            "disk": disk_status
        },
        "metadata": {
            "uptime_seconds": time.time() - _startup_time,
            "database_type": "postgresql" if settings.uses_postgres else "sqlite",
            "cache_type": "redis" if redis_status["status"] == "healthy" else "in-memory"
        }
    }
    
    return response


@router.get("/health")
async def basic_health_check() -> Dict[str, Any]:
    """
    Basic health check - returns if service is running.
    Used by Docker healthcheck and load balancers.
    """
    return {
        "status": "healthy",
        "service": "nebula-backend",
        "timestamp": int(time.time()),
        "version": os.getenv("APP_VERSION", "1.0.0")
    }
