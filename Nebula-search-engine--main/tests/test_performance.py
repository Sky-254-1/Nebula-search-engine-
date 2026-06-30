"""Performance and load tests: response times, concurrent API calls, database query speed, cache performance."""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_health_response_time(client: AsyncClient):
    t0 = time.monotonic()
    for _ in range(10):
        resp = await client.get("/health")
        assert resp.status_code == 200
    elapsed = time.monotonic() - t0
    avg = elapsed / 10
    assert avg < 0.5


@pytest.mark.asyncio
async def test_concurrent_health_checks(client: AsyncClient):
    async def health_check():
        resp = await client.get("/health")
        return resp.status_code

    results = await asyncio.gather(*[health_check() for _ in range(20)])
    assert all(r == 200 for r in results)


@pytest.mark.asyncio
async def test_concurrent_auth_and_search(client: AsyncClient, auth_headers: dict):
    async def search_call():
        with patch("app.routes.search.run_web_search", new=AsyncMock(return_value=[])):
            resp = await client.get(
                "/api/v1/search/web?q=concurrent&backend=wikipedia",
                headers=auth_headers,
            )
        return resp.status_code

    results = await asyncio.gather(*[search_call() for _ in range(10)])
    successful = [r for r in results if r == 200]
    assert len(successful) >= 8


@pytest.mark.asyncio
async def test_database_query_performance(client: AsyncClient):
    from app.database.engine import connect

    db = await connect()
    try:
        t0 = time.monotonic()
        for _ in range(50):
            await db.execute("SELECT 1")
        elapsed = time.monotonic() - t0
        avg = elapsed / 50
        assert avg < 0.1
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_cache_get_performance():
    from app.services.cache import CacheService

    with patch("app.services.cache.settings") as mocked_settings:
        mocked_settings.redis_url = None
        mocked_settings.cache_ttl_seconds = 60

        cache = CacheService()
        await cache.connect()

        for i in range(100):
            await cache.set(f"perf_key_{i}", f"value_{i}")

        t0 = time.monotonic()
        for i in range(100):
            await cache.get(f"perf_key_{i}")
        elapsed = time.monotonic() - t0
        avg = elapsed / 100
        assert avg < 0.01


@pytest.mark.asyncio
async def test_cache_set_performance():
    from app.services.cache import CacheService

    with patch("app.services.cache.settings") as mocked_settings:
        mocked_settings.redis_url = None
        mocked_settings.cache_ttl_seconds = 60

        cache = CacheService()
        await cache.connect()

        t0 = time.monotonic()
        for i in range(100):
            await cache.set(f"bulk_key_{i}", f"bulk_value_{i}")
        elapsed = time.monotonic() - t0
        avg = elapsed / 100
        assert avg < 0.01


@pytest.mark.asyncio
async def test_signup_response_time(client: AsyncClient):
    t0 = time.monotonic()
    resp = await client.post(
        "/api/v1/auth/signup",
        json={"email": "perf@test.com", "password": "ValidPass1!"},
    )
    elapsed = time.monotonic() - t0
    assert resp.status_code == 201
    assert elapsed < 5.0
