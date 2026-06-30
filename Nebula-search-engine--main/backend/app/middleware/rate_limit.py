"""Rate limiter with Redis backing, slowapi integration, and tier-based limits."""

import logging
import time
from typing import Optional

from fastapi import HTTPException, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.config import get_settings
from app.services.cache import cache_service

settings = get_settings()
logger = logging.getLogger("nebula.ratelimit")
_memory_store: dict[str, list[float]] = {}

# ---- slowapi integration ----

_limiter = Limiter(key_func=get_remote_address, default_limits=[])

slowapi_middleware = SlowAPIMiddleware


def get_limiter() -> Limiter:
    """Return the shared slowapi Limiter instance."""
    return _limiter


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Override default slowapi handler to match existing JSON style."""
    return _rate_limit_exceeded_handler(request, exc)


# ---- Tier maps ----

TIER_LIMITS: dict[str, int] = {
    "basic": settings.rate_limit_tier_basic,
    "pro": settings.rate_limit_tier_pro,
    "enterprise": settings.rate_limit_tier_enterprise,
}

DEFAULT_TIER = "basic"

# In-memory burst tracking
_burst_store: dict[str, tuple[int, float]] = {}


def _get_user_tier(user_payload: Optional[dict] = None) -> str:
    """Extract rate-limit tier from an authenticated user payload."""
    if user_payload is None:
        return DEFAULT_TIER
    return user_payload.get("tier", user_payload.get("role", DEFAULT_TIER))


# ---- Existing in-memory/Redis rate limit (preserved & enhanced) ----

async def rate_limit(
    request: Request,
    limit: int | None = None,
    user_payload: Optional[dict] = None,
    burst: bool = False,
) -> None:
    """Reject requests that exceed the configured per-minute limit.

    Supports:
    - IP + path scoped limits (original behaviour)
    - User-based limits (when *user_payload* is passed)
    - Tier-based limits (auto-detected from *user_payload*)
    - Burst mode (allows short spikes before hard limit)
    """
    # Determine key
    if user_payload:
        user_id = user_payload.get("sub") or user_payload.get("user_id", "unknown")
        tier = _get_user_tier(user_payload)
        tier_limit = TIER_LIMITS.get(tier, TIER_LIMITS[DEFAULT_TIER])
        effective_limit = limit or tier_limit
        scope = user_id
    else:
        effective_limit = limit or settings.rate_limit_per_minute
        scope = request.client.host if request.client else "unknown"

    ip = request.client.host if request.client else "unknown"
    path = request.url.path
    redis_key = f"ratelimit:{scope}:{path}"

    # --- Burst ---
    if burst:
        burst_key = f"burst:{redis_key}"
        burst_limit = effective_limit * settings.rate_limit_burst_multiplier
        now = time.time()

        if cache_service._redis:
            try:
                bcount = await cache_service._redis.incr(burst_key)
                if bcount == 1:
                    await cache_service._redis.expire(burst_key, 2)
                if bcount > burst_limit:
                    raise HTTPException(
                        status_code=429,
                        detail="Burst rate limit exceeded. Slow down.",
                    )
            except HTTPException:
                raise
            except Exception as exc:
                logger.debug("Redis burst fallback: %s", exc)
        else:
            bcount_raw, btime = _burst_store.get(burst_key, (0, 0.0))
            if now - btime > 2:
                bcount_raw = 0
            bcount_raw += 1
            _burst_store[burst_key] = (bcount_raw, now)
            if bcount_raw > burst_limit:
                raise HTTPException(
                    status_code=429,
                    detail="Burst rate limit exceeded. Slow down.",
                )

    # --- Steady-state limit (original sliding window) ---
    if cache_service._redis:
        try:
            count = await cache_service._redis.incr(redis_key)
            if count == 1:
                await cache_service._redis.expire(redis_key, 60)
            if count > effective_limit:
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
    _memory_store[redis_key] = [
        ts for ts in window if now - ts < 60
    ]
    if len(_memory_store[redis_key]) >= effective_limit:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again shortly.",
        )
    _memory_store[redis_key].append(now)


# ---- Backward-compatible auth helpers ----

def rate_limit_auth(limit: int):
    async def limiter(request: Request):
        await rate_limit(request, limit=limit)

    return limiter


limit_signup = rate_limit_auth(settings.signup_rate_limit)
limit_login = rate_limit_auth(settings.login_rate_limit)
limit_refresh = rate_limit_auth(settings.refresh_rate_limit)
