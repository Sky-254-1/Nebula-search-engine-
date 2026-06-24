"""Rate limiter with Redis backing when available."""

import logging
import time

from fastapi import HTTPException, Request

from app.config import get_settings
from app.services.cache import cache_service

settings = get_settings()
logger = logging.getLogger("nebula.ratelimit")
_memory_store: dict[str, list[float]] = {}


async def rate_limit(request: Request) -> None:
    """Reject requests that exceed the configured per-minute limit."""
    ip = request.client.host if request.client else "unknown"
    redis_key = f"ratelimit:{ip}"

    if cache_service._redis:
        try:
            count = await cache_service._redis.incr(redis_key)
            if count == 1:
                await cache_service._redis.expire(redis_key, 60)
            if count > settings.rate_limit_per_minute:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Try again shortly.",
                )
            return
        except HTTPException:
            raise
        except Exception as exc:
            logger.debug("Redis rate limit fallback: %s", exc)

    now = time.time()
    window = _memory_store.setdefault(ip, [])
    _memory_store[ip] = [timestamp for timestamp in window if now - timestamp < 60]
    if len(_memory_store[ip]) >= settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again shortly.",
        )
    _memory_store[ip].append(now)
