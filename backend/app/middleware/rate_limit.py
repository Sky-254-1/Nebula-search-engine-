"""Rate limiter with Redis backing when available."""

import logging
import time

from fastapi import HTTPException, Request

from app.config import get_settings
from app.services.cache import cache_service

settings = get_settings()
logger = logging.getLogger("nebula.ratelimit")
_memory_store: dict[str, list[float]] = {}


async def rate_limit(request: Request, limit: int | None = None) -> None:
    """Reject requests that exceed the configured per-minute limit."""
    ip = request.client.host if request.client else "unknown"
    path = request.url.path
    # Use path-specific keys for granular rate limiting
    redis_key = f"ratelimit:{ip}:{path}"
    limit = limit or settings.rate_limit_per_minute

    if cache_service._redis:
        try:
            count = await cache_service._redis.incr(redis_key)
            if count == 1:
                await cache_service._redis.expire(redis_key, 60)
            if count > limit:
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
    window = _memory_store.setdefault(redis_key, [])
    _memory_store[redis_key] = [timestamp for timestamp in window if now - timestamp < 60]
    if len(_memory_store[redis_key]) >= limit:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again shortly.",
        )
    _memory_store[redis_key].append(now)


def rate_limit_auth(limit: int):
    async def limiter(request: Request):
        await rate_limit(request, limit=limit)

    return limiter


limit_signup = rate_limit_auth(settings.signup_rate_limit)
limit_login = rate_limit_auth(settings.login_rate_limit)
limit_refresh = rate_limit_auth(settings.refresh_rate_limit)
