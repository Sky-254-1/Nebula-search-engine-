"""Sliding-window rate limiter (in-memory, per-IP)."""

import time

from fastapi import HTTPException, Request

from app.config import get_settings

settings = get_settings()
_rate_store: dict[str, list[float]] = {}


async def rate_limit(request: Request) -> None:
    """Reject requests that exceed the configured per-minute limit."""
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = _rate_store.setdefault(ip, [])
    _rate_store[ip] = [timestamp for timestamp in window if now - timestamp < 60]
    if len(_rate_store[ip]) >= settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again shortly.",
        )
    _rate_store[ip].append(now)
