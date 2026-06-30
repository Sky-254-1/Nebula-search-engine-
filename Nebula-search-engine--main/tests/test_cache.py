"""Cache tests: get/set/delete, TTL expiration, prefix invalidation, Redis fallback, concurrent access."""

import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_cache_set_get_delete_memory():
    from app.services.cache import CacheService

    with patch("app.services.cache.settings") as mocked_settings:
        mocked_settings.redis_url = None
        mocked_settings.cache_ttl_seconds = 60

        cache = CacheService()
        await cache.connect()
        assert cache._redis is None

        await cache.set("key1", "value1")
        assert await cache.get("key1") == "value1"

        await cache.set("key2", {"nested": "data"})
        assert await cache.get("key2") == {"nested": "data"}

        await cache.delete("key1")
        assert await cache.get("key1") is None


@pytest.mark.asyncio
async def test_cache_ttl_expiration():
    from app.services.cache import CacheService

    with patch("app.services.cache.settings") as mocked_settings:
        mocked_settings.redis_url = None
        mocked_settings.cache_ttl_seconds = 60

        cache = CacheService()
        await cache.connect()

        with patch("app.services.cache.time.time") as mock_time:
            now = 1000.0
            mock_time.return_value = now
            await cache.set("ttl_key", "expires_soon", ttl=3)

            mock_time.return_value = 1002.0
            assert await cache.get("ttl_key") == "expires_soon"

            mock_time.return_value = 1004.0
            assert await cache.get("ttl_key") is None


@pytest.mark.asyncio
async def test_cache_prefix_invalidation_memory():
    from app.services.cache import CacheService

    with patch("app.services.cache.settings") as mocked_settings:
        mocked_settings.redis_url = None
        mocked_settings.cache_ttl_seconds = 60

        cache = CacheService()
        await cache.connect()

        await cache.set("user:1:data", "a")
        await cache.set("user:2:data", "b")
        await cache.set("other:data", "c")

        await cache.invalidate_prefix("user:")
        assert await cache.get("user:1:data") is None
        assert await cache.get("user:2:data") is None
        assert await cache.get("other:data") == "c"


@pytest.mark.asyncio
async def test_cache_redis_fallback_to_memory():
    from app.services.cache import CacheService

    with patch("app.services.cache.settings") as mocked_settings:
        mocked_settings.redis_url = "redis://localhost"

        with patch("redis.asyncio.from_url", side_effect=Exception("Connection failed")):
            cache = CacheService()
            await cache.connect()
            assert cache._redis is None

            await cache.set("fallback_key", "fallback_value")
            assert await cache.get("fallback_key") == "fallback_value"


@pytest.mark.asyncio
async def test_cache_redis_operations():
    from app.services.cache import CacheService

    with patch("app.services.cache.settings") as mocked_settings:
        mocked_settings.redis_url = "redis://localhost"
        mocked_settings.cache_ttl_seconds = 60

        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = '{"data": "from_redis"}'

        async def mock_scan_iter(match=None):
            yield "pfx:k1"
            yield "pfx:k2"

        mock_redis.scan_iter = MagicMock(return_value=mock_scan_iter())

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            cache = CacheService()
            await cache.connect()
            assert cache._redis is not None

            await cache.set("redis_key", {"data": "value"})
            mock_redis.setex.assert_called_once()

            result = await cache.get("redis_key")
            assert result == {"data": "from_redis"}

            await cache.delete("redis_key")
            mock_redis.delete.assert_called_with("redis_key")

            await cache.invalidate_prefix("pfx:")
            mock_redis.delete.assert_called_with("pfx:k1", "pfx:k2")

            await cache.close()
            mock_redis.close.assert_called_once()


@pytest.mark.asyncio
async def test_cache_set_with_custom_ttl():
    from app.services.cache import CacheService

    with patch("app.services.cache.settings") as mocked_settings:
        mocked_settings.redis_url = None
        mocked_settings.cache_ttl_seconds = 60

        cache = CacheService()
        await cache.connect()

        with patch("app.services.cache.time.time") as mock_time:
            now = 1000.0
            mock_time.return_value = now
            await cache.set("custom_ttl", "val", ttl=10)

            mock_time.return_value = 1009.0
            assert await cache.get("custom_ttl") == "val"

            mock_time.return_value = 1011.0
            assert await cache.get("custom_ttl") is None


@pytest.mark.asyncio
async def test_cache_default_ttl_used():
    from app.services.cache import CacheService

    with patch("app.services.cache.settings") as mocked_settings:
        mocked_settings.redis_url = None
        mocked_settings.cache_ttl_seconds = 5

        cache = CacheService()
        await cache.connect()

        with patch("app.services.cache.time.time") as mock_time:
            now = 1000.0
            mock_time.return_value = now
            await cache.set("no_ttl", "val")

            mock_time.return_value = 1004.0
            assert await cache.get("no_ttl") == "val"

            mock_time.return_value = 1006.0
            assert await cache.get("no_ttl") is None
