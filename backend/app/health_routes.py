from fastapi import APIRouter
from fastapi.responses import JSONResponse
import time
from typing import Dict, Any
import os

router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check - returns if service is running.
    Used by Docker healthcheck and load balancers.
    """
    return {
        "status": "healthy",
        "service": "nebula-backend",
        "timestamp": int(time.time()),
    }


@router.get("/health/live")
async def liveness_check() -> Dict[str, Any]:
    """
    Kubernetes liveness probe.
    Returns 200 if the application is alive.
    """
    return {
        "status": "alive",
        "service": "nebula-backend",
    }


@router.get("/health/ready")
async def readiness_check() -> Dict[str, Any]:
    """
    Kubernetes readiness probe.
    Returns 200 if the application is ready to serve traffic.
    Checks database, redis, and other dependencies.
    """
    checks = {}
    overall_status = "ready"
    
    # Check database connection
    try:
        from app.database.engine import connect
        db = await connect()
        await db.execute("SELECT 1")
        await db.close()
        checks["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        checks["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
        overall_status = "not_ready"
    
    # Check Redis connection
    try:
        from app.services.cache import cache_service
        if cache_service._redis:
            await cache_service._redis.ping()
            checks["redis"] = {
                "status": "healthy",
                "message": "Redis connection successful"
            }
        else:
            checks["redis"] = {
                "status": "healthy",
                "message": "Redis not configured (in-memory cache)"
            }
    except Exception as e:
        checks["redis"] = {
            "status": "unhealthy",
            "message": f"Redis connection failed: {str(e)}"
        }
        overall_status = "not_ready"
    
    # Check disk space
    try:
        import shutil
        disk = shutil.disk_usage(os.getcwd())
        disk_free_percent = (disk.free / disk.total) * 100
        checks["disk"] = {
            "status": "healthy" if disk_free_percent > 10 else "warning",
            "free_percent": round(disk_free_percent, 2),
            "free_gb": round(disk.free / (1024**3), 2),
        }
        if disk_free_percent < 10:
            overall_status = "not_ready"
    except Exception as e:
        checks["disk"] = {
            "status": "unknown",
            "message": f"Could not check disk: {str(e)}"
        }
    
    response = {
        "status": overall_status,
        "service": "nebula-backend",
        "checks": checks,
        "timestamp": int(time.time()),
    }
    
    status_code = 200 if overall_status == "ready" else 503
    return JSONResponse(content=response, status_code=status_code)


@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """
    Comprehensive health check with all system details.
    Used for monitoring and debugging.
    """
    checks = {}
    
    # Database check
    try:
        from app.database.engine import connect
        db = await connect()
        await db.execute("SELECT 1")
        await db.close()
        checks["database"] = {"status": "healthy", "details": {}}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}
    
    # Redis check
    try:
        from app.services.cache import cache_service
        if cache_service._redis:
            redis_info = await cache_service._redis.info()
            checks["redis"] = {
                "status": "healthy",
                "connected_clients": redis_info.get("connected_clients", 0),
                "used_memory": redis_info.get("used_memory_human", "unknown"),
                "version": redis_info.get("redis_version", "unknown"),
            }
        else:
            checks["redis"] = {"status": "not_configured", "message": "Using in-memory cache"}
    except Exception as e:
        checks["redis"] = {"status": "unhealthy", "error": str(e)}
    
    # Storage check
    try:
        from app.config import get_settings
        settings = get_settings()
        storage_path = settings.storage_uploads
        os.makedirs(storage_path, exist_ok=True)
        test_file = os.path.join(storage_path, ".health_check")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        checks["storage"] = {"status": "healthy", "path": str(storage_path)}
    except Exception as e:
        checks["storage"] = {"status": "unhealthy", "error": str(e)}
    
    # Workers check (if applicable)
    try:
        from app.indexing.worker import worker_status
        checks["indexing_worker"] = worker_status()
    except ImportError:
        checks["indexing_worker"] = {"status": "not_configured"}
    
    # External AI providers check
    try:
        from app.services.ai_provider import check_ai_providers
        checks["ai_providers"] = check_ai_providers()
    except Exception as e:
        checks["ai_providers"] = {"status": "unknown", "error": str(e)}
    
    # Search indexes check
    try:
        from app.hybrid.services import check_search_indexes
        checks["search_indexes"] = check_search_indexes()
    except Exception as e:
        checks["search_indexes"] = {"status": "unknown", "error": str(e)}
    
    overall_status = "healthy" if all(
        c.get("status") in ["healthy", "not_configured"] for c in checks.values()
    ) else "unhealthy"
    
    return {
        "status": overall_status,
        "service": "nebula-backend",
        "version": os.getenv("APP_VERSION", "unknown"),
        "environment": os.getenv("APP_ENV", "unknown"),
        "checks": checks,
        "timestamp": int(time.time()),
    }
