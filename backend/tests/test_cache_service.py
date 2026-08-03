"""Tests for backend/app/services/cache.py.

Coverage areas:
- Redis cache operations (get, set, delete, ping)
- In-memory fallback operations
- TTL handling
- Stats reporting
- Pattern invalidation
- Error handling
"""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.cache import CacheService


class TestCacheServiceInitialization:
    """Test cache service initialization."""

    def test_cache_service_initialization(self):
        """Should initialize cache service with empty memory and no Redis."""
        service = CacheService()
        assert service._memory == {}
        assert service._redis is None

    @pytest.mark.asyncio
    async def test_cache_service_connect_no_redis_config(self):
        """Should not connect to Redis when redis_url is not configured."""
        service = CacheService()

        with patch("app.services.cache.settings") as mock_settings:
            mock_settings.redis_url = None

            await service.connect()
            assert service._redis is None

    @pytest.mark.asyncio
    async def test_cache_service_connect_with_redis(self):
        """Should connect to Redis when redis_url is configured."""
        service = CacheService()

        with patch("app.services.cache.settings") as mock_settings:
            mock_settings.redis_url = "redis://localhost:6379"
            mock_settings.cache_ttl_seconds = 3600

            # Mock redis module
            mock_redis = MagicMock()
            mock_redis.ping = AsyncMock(return_value=True)

            with patch("app.services.cache.redis") as mock_redis_module:
                mock_redis_module.from_url.return_value = mock_redis

                await service.connect()
                assert service._redis is not None
                mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_service_connect_redis_failure(self):
        """Should handle Redis connection failure gracefully."""
        service = CacheService()

        with patch("app.services.cache.settings") as mock_settings:
            mock_settings.redis_url = "redis://localhost:6379"

            with patch("app.services.cache.redis") as mock_redis_module:
                mock_redis_module.from_url.side_effect = Exception("Redis unavailable")

                with patch("app.services.cache.logger") as mock_logger:
                    await service.connect()
                    assert service._redis is None
                    mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_cache_service_close_redis(self):
        """Should close Redis connection."""
        service = CacheService()
        service._redis = MagicMock()
        service._redis.close = AsyncMock()

        await service.close()
        service._redis.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_service_close_no_redis(self):
        """Should handle close when no Redis connection."""
        service = CacheService()
        service._redis = None

        # Should not raise
        await service.close()


class TestGetOperations:
    """Test cache get operations."""

    @pytest.mark.asyncio
    async def test_get_redis_happy(self):
        """Should get value from Redis cache."""
        service = CacheService()
        service._redis = MagicMock()
        service._redis.get = AsyncMock(return_value='{"key": "value"}')

        result = await service.get("test_key")
        assert result == {"key": "value"}
        service._redis.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_redis_not_found(self):
        """Should return None when key not in Redis."""
        service = CacheService()
        service._redis = MagicMock()
        service._redis.get = AsyncMock(return_value=None)

        result = await service.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_memory_happy(self):
        """Should get value from in-memory cache."""
        service = CacheService()
        service._memory["test_key"] = ("value", time.time() + 3600)

        result = await service.get("test_key")
        assert result == "value"

    @pytest.mark.asyncio
    async def test_get_memory_expired(self):
        """Should return None when memory cache entry is expired."""
        service = CacheService()
        service._memory["expired_key"] = ("value", time.time() - 3600)

        result = await service.get("expired_key")
        assert result is None
        assert "expired_key" not in service._memory

    @pytest.mark.asyncio
    async def test_get_memory_not_found(self):
        """Should return None when key not in memory."""
        service = CacheService()
        service._memory = {}

        result = await service.get("nonexistent")
        assert result is None


class TestSetOperations:
    """Test cache set operations."""

    @pytest.mark.asyncio
    async def test_set_redis(self):
        """Should set value in Redis cache."""
        service = CacheService()
        service._redis = MagicMock()
        service._redis.setex = AsyncMock()

        with patch("app.services.cache.settings") as mock_settings:
            mock_settings.cache_ttl_seconds = 3600

            await service.set("test_key", {"key": "value"})

            service._redis.setex.assert_called_once_with(
                "test_key", 3600, '{"key": "value"}'
            )

    @pytest.mark.asyncio
    async def test_set_redis_custom_ttl(self):
        """Should use custom TTL when provided."""
        service = CacheService()
        service._redis = MagicMock()
        service._redis.setex = AsyncMock()

        await service.set("test_key", {"key": "value"}, ttl=7200)

        service._redis.setex.assert_called_once_with(
            "test_key", 7200, '{"key": "value"}'
        )

    @pytest.mark.asyncio
    async def test_set_memory(self):
        """Should set value in in-memory cache."""
        service = CacheService()
        service._memory = {}

        with patch("app.services.cache.settings") as mock_settings:
            mock_settings.cache_ttl_seconds = 3600

            await service.set("test_key", {"key": "value"})

            assert "test_key" in service._memory
            value, expires = service._memory["test_key"]
            assert value == {"key": "value"}
            assert expires > time.time()

    @pytest.mark.asyncio
    async def test_set_memory_custom_ttl(self):
        """Should use custom TTL for memory cache."""
        service = CacheService()
        service._memory = {}

        await service.set("test_key", {"key": "value"}, ttl=7200)

        value, expires = service._memory["test_key"]
        expected_ttl = 7200
        assert abs(expires - time.time() - expected_ttl) < 1

    @pytest.mark.asyncio
    async def test_set_memory_overwrite(self):
        """Should overwrite existing key in memory."""
        service = CacheService()
        service._memory["test_key"] = ("old_value", time.time() + 3600)

        await service.set("test_key", "new_value")

        value, _ = service._memory["test_key"]
        assert value == "new_value"


class TestDeleteOperations:
    """Test cache delete operations."""

    @pytest.mark.asyncio
    async def test_delete_redis(self):
        """Should delete key from Redis cache."""
        service = CacheService()
        service._redis = MagicMock()
        service._redis.delete = AsyncMock()

        await service.delete("test_key")

        service._redis.delete.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_delete_memory(self):
        """Should delete key from memory cache."""
        service = CacheService()
        service._memory["test_key"] = ("value", time.time() + 3600)

        await service.delete("test_key")

        assert "test_key" not in service._memory

    @pytest.mark.asyncio
    async def test_delete_memory_nonexistent(self):
        """Should handle deletion of non-existent key in memory."""
        service = CacheService()
        service._memory = {}

        # Should not raise
        await service.delete("nonexistent")


class TestStatsOperations:
    """Test cache stats operations."""

    @pytest.mark.asyncio
    async def test_get_stats_redis(self):
        """Should get stats from Redis cache."""
        service = CacheService()
        service._redis = MagicMock()
        service._redis.info = AsyncMock(return_value={"used_memory": 1048576})
        service._redis.dbsize = AsyncMock(return_value=100)

        stats = await service.get_stats()

        assert stats["connected"] is True
        assert stats["keys_count"] == 100
        assert stats["memory_usage_mb"] == 1.0

    @pytest.mark.asyncio
    async def test_get_stats_memory(self):
        """Should get stats from in-memory cache."""
        service = CacheService()
        service._memory = {
            "key1": ("value1", time.time() + 3600),
            "key2": ("value2", time.time() + 7200),
        }

        stats = await service.get_stats()

        assert stats["connected"] is False
        assert stats["keys_count"] == 2
        assert stats["memory_usage_mb"] == 0.0

    @pytest.mark.asyncio
    async def test_get_stats_redis_empty(self):
        """Should handle empty Redis stats."""
        service = CacheService()
        service._redis = MagicMock()
        service._redis.info = AsyncMock(return_value={})
        service._redis.dbsize = AsyncMock(return_value=0)

        stats = await service.get_stats()

        assert stats["connected"] is True
        assert stats["keys_count"] == 0
        assert stats["memory_usage_mb"] == 0.0


class TestInvalidateOperations:
    """Test cache invalidation operations."""

    @pytest.mark.asyncio
    async def test_invalidate_prefix_redis(self):
        """Should invalidate keys by prefix in Redis."""
        service = CacheService()
        service._redis = MagicMock()
        # scan_iter is an async generator, not a coroutine
        async def mock_scan_iter(match=None):
            yield "prefix:key1"
            yield "prefix:key2"
            yield "other:key3"
        
        # Configure scan_iter to be an async generator when called
        type(service._redis).scan_iter = MagicMock(side_effect=mock_scan_iter)
        service._redis.delete = AsyncMock()

        await service.invalidate_prefix("prefix:")

        service._redis.scan_iter.assert_called_once_with(match="prefix:*")
        service._redis.delete.assert_called_once_with("prefix:key1", "prefix:key2")

    @pytest.mark.asyncio
    async def test_invalidate_prefix_memory(self):
        """Should invalidate keys by prefix in memory."""
        service = CacheService()
        service._memory = {
            "prefix:key1": ("value1", time.time() + 3600),
            "prefix:key2": ("value2", time.time() + 7200),
            "other:key3": ("value3", time.time() + 3600),
        }

        await service.invalidate_prefix("prefix:")

        assert "prefix:key1" not in service._memory
        assert "prefix:key2" not in service._memory
        assert "other:key3" in service._memory

    @pytest.mark.asyncio
    async def test_invalidate_pattern_redis(self):
        """Should invalidate keys by pattern in Redis."""
        service = CacheService()
        service._redis = MagicMock()
        # scan_iter is an async generator, not a coroutine
        async def mock_scan_iter(match=None):
            yield "prefix:key1"
        service._redis.scan_iter = mock_scan_iter
        service._redis.delete = AsyncMock()

        await service.invalidate_pattern("prefix:")

        service._redis.delete.assert_called_once_with("prefix:key1")

    @pytest.mark.asyncio
    async def test_invalidate_pattern_memory(self):
        """Should invalidate keys by pattern in memory."""
        service = CacheService()
        service._memory = {
            "prefix:key1": ("value1", time.time() + 3600),
            "other:key2": ("value2", time.time() + 7200),
        }

        await service.invalidate_pattern("prefix:")

        assert "prefix:key1" not in service._memory
        assert "other:key2" in service._memory

    @pytest.mark.asyncio
    async def test_invalidate_prefix_no_matches(self):
        """Should handle prefix invalidation with no matches."""
        service = CacheService()
        service._redis = MagicMock()
        service._redis.scan_iter = AsyncMock(return_value=[])

        await service.invalidate_prefix("nonexistent:")

        service._redis.delete.assert_not_called()


class TestDataSerialization:
    """Test data serialization in cache."""

    @pytest.mark.asyncio
    async def test_set_dict(self):
        """Should serialize dict to JSON."""
        service = CacheService()
        service._memory = {}

        await service.set("test_key", {"nested": {"data": [1, 2, 3]}})

        value, _ = service._memory["test_key"]
        assert value == {"nested": {"data": [1, 2, 3]}}

    @pytest.mark.asyncio
    async def test_set_list(self):
        """Should serialize list to JSON."""
        service = CacheService()
        service._memory = {}

        await service.set("test_key", [1, 2, 3, 4, 5])

        value, _ = service._memory["test_key"]
        assert value == [1, 2, 3, 4, 5]

    @pytest.mark.asyncio
    async def test_set_string(self):
        """Should serialize string."""
        service = CacheService()
        service._memory = {}

        await service.set("test_key", "hello world")

        value, _ = service._memory["test_key"]
        assert value == "hello world"

    @pytest.mark.asyncio
    async def test_set_number(self):
        """Should serialize numbers."""
        service = CacheService()
        service._memory = {}

        await service.set("test_key", 42)

        value, _ = service._memory["test_key"]
        assert value == 42

    @pytest.mark.asyncio
    async def test_set_boolean(self):
        """Should serialize boolean."""
        service = CacheService()
        service._memory = {}

        await service.set("test_key", True)

        value, _ = service._memory["test_key"]
        assert value is True


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_get_empty_string(self):
        """Should handle empty string value."""
        service = CacheService()
        service._memory["empty"] = ("", time.time() + 3600)

        result = await service.get("empty")
        assert result == ""

    @pytest.mark.asyncio
    async def test_set_none_value(self):
        """Should handle None value."""
        service = CacheService()
        service._memory = {}

        await service.set("none_key", None)

        value, _ = service._memory["none_key"]
        assert value is None

    @pytest.mark.asyncio
    async def test_memory_ttl_exact(self):
        """Should handle TTL precisely."""
        service = CacheService()
        service._memory = {}

        # Set with very short TTL
        await service.set("short_ttl", "value", ttl=1)

        # Should exist immediately
        result = await service.get("short_ttl")
        assert result == "value"

        # Wait for expiration
        time.sleep(1.1)

        result = await service.get("short_ttl")
        assert result is None
        assert "short_ttl" not in service._memory

    @pytest.mark.asyncio
    async def test_multiple_operations_same_key(self):
        """Should handle multiple operations on same key."""
        service = CacheService()
        service._memory = {}

        await service.set("key", "value1")
        await service.set("key", "value2")
        await service.delete("key")
        await service.set("key", "value3")

        result = await service.get("key")
        assert result == "value3"