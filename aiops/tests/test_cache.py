"""Comprehensive tests for cache module."""

import pytest
import time
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from aiops.core.cache import (
    Cache,
    CacheBackend,
    FileBackend,
    RedisBackend,
    RateLimiter,
    get_cache,
    cached,
    rate_limited,
)


class TestCacheBackend:
    """Tests for CacheBackend base class."""

    def test_get_not_implemented(self):
        """Test that get raises NotImplementedError."""
        backend = CacheBackend()
        with pytest.raises(NotImplementedError):
            backend.get("key")

    def test_set_not_implemented(self):
        """Test that set raises NotImplementedError."""
        backend = CacheBackend()
        with pytest.raises(NotImplementedError):
            backend.set("key", "value")

    def test_delete_not_implemented(self):
        """Test that delete raises NotImplementedError."""
        backend = CacheBackend()
        with pytest.raises(NotImplementedError):
            backend.delete("key")

    def test_exists_not_implemented(self):
        """Test that exists raises NotImplementedError."""
        backend = CacheBackend()
        with pytest.raises(NotImplementedError):
            backend.exists("key")

    def test_clear_not_implemented(self):
        """Test that clear raises NotImplementedError."""
        backend = CacheBackend()
        with pytest.raises(NotImplementedError):
            backend.clear()


class TestFileBackend:
    """Tests for FileBackend."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def file_backend(self, temp_cache_dir):
        """Create FileBackend instance."""
        return FileBackend(temp_cache_dir)

    def test_init_creates_directory(self, temp_cache_dir):
        """Test that init creates cache directory."""
        cache_dir = temp_cache_dir / "new_cache"
        FileBackend(cache_dir)
        assert cache_dir.exists()

    def test_set_and_get(self, file_backend):
        """Test basic set and get operations."""
        file_backend.set("test_key", {"data": "value"})
        result = file_backend.get("test_key")
        assert result == {"data": "value"}

    def test_get_nonexistent_key(self, file_backend):
        """Test getting a key that doesn't exist."""
        result = file_backend.get("nonexistent")
        assert result is None

    def test_set_with_ttl(self, file_backend):
        """Test set with TTL."""
        file_backend.set("ttl_key", "value", ttl=2)
        result = file_backend.get("ttl_key")
        assert result == "value"

    def test_ttl_expiration(self, file_backend):
        """Test that TTL causes expiration."""
        file_backend.set("expire_key", "value", ttl=1)
        time.sleep(1.5)
        result = file_backend.get("expire_key")
        assert result is None

    def test_delete(self, file_backend):
        """Test delete operation."""
        file_backend.set("delete_key", "value")
        file_backend.delete("delete_key")
        result = file_backend.get("delete_key")
        assert result is None

    def test_delete_nonexistent(self, file_backend):
        """Test deleting nonexistent key doesn't raise."""
        file_backend.delete("nonexistent")  # Should not raise

    def test_exists(self, file_backend):
        """Test exists check."""
        file_backend.set("exists_key", "value")
        assert file_backend.exists("exists_key") is True
        assert file_backend.exists("nonexistent") is False

    def test_clear(self, file_backend):
        """Test clear removes all entries."""
        file_backend.set("key1", "value1")
        file_backend.set("key2", "value2")
        file_backend.clear()
        assert file_backend.get("key1") is None
        assert file_backend.get("key2") is None

    def test_complex_data_types(self, file_backend):
        """Test caching complex data types."""
        data = {
            "list": [1, 2, 3],
            "nested": {"a": {"b": "c"}},
            "tuple_as_list": [1, 2],
            "number": 42.5,
            "boolean": True,
            "none": None,
        }
        file_backend.set("complex", data)
        result = file_backend.get("complex")
        assert result["list"] == [1, 2, 3]
        assert result["nested"]["a"]["b"] == "c"

    def test_large_value(self, file_backend):
        """Test caching large values."""
        large_data = "x" * 1_000_000  # 1MB string
        file_backend.set("large", large_data)
        result = file_backend.get("large")
        assert result == large_data

    def test_special_characters_in_key(self, file_backend):
        """Test keys with special characters work when hashed."""
        file_backend.set("key/with/slashes", "value")
        # Note: This may fail if key is used directly as filename


class TestRedisBackend:
    """Tests for RedisBackend."""

    def test_init_without_redis_package(self):
        """Test initialization when redis package not installed."""
        with patch.dict('sys.modules', {'redis': None}):
            with patch('builtins.__import__', side_effect=ImportError):
                backend = RedisBackend("redis://localhost:6379")
                assert backend.enabled is False

    def test_init_connection_failure(self):
        """Test initialization with connection failure."""
        with patch('redis.from_url') as mock_from_url:
            mock_client = Mock()
            mock_client.ping.side_effect = Exception("Connection refused")
            mock_from_url.return_value = mock_client

            backend = RedisBackend("redis://localhost:6379")
            assert backend.enabled is False

    def test_make_key(self):
        """Test key prefixing."""
        with patch('redis.from_url') as mock_from_url:
            mock_client = Mock()
            mock_from_url.return_value = mock_client

            backend = RedisBackend("redis://localhost:6379", prefix="test")
            assert backend._make_key("mykey") == "test:mykey"

    def test_get_when_disabled(self):
        """Test get returns None when disabled."""
        backend = RedisBackend.__new__(RedisBackend)
        backend.enabled = False
        assert backend.get("key") is None

    def test_set_when_disabled(self):
        """Test set does nothing when disabled."""
        backend = RedisBackend.__new__(RedisBackend)
        backend.enabled = False
        backend.set("key", "value")  # Should not raise


class TestCache:
    """Tests for unified Cache class."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def cache(self, temp_cache_dir):
        """Create Cache instance."""
        return Cache(cache_dir=temp_cache_dir, ttl=3600, enable_redis=False)

    def test_init_with_file_backend(self, temp_cache_dir):
        """Test initialization with file backend."""
        cache = Cache(cache_dir=temp_cache_dir, enable_redis=False)
        assert isinstance(cache.backend, FileBackend)

    def test_init_redis_fallback(self, temp_cache_dir):
        """Test Redis fallback to file backend."""
        with patch.dict('os.environ', {'REDIS_URL': 'redis://invalid:6379'}):
            cache = Cache(cache_dir=temp_cache_dir, enable_redis=True)
            # Should fall back to FileBackend
            assert isinstance(cache.backend, FileBackend)

    def test_get_cache_key(self, cache):
        """Test cache key generation."""
        key1 = cache._get_cache_key("func", "arg1", kwarg="value")
        key2 = cache._get_cache_key("func", "arg1", kwarg="value")
        key3 = cache._get_cache_key("func", "arg1", kwarg="different")

        assert key1 == key2  # Same args = same key
        assert key1 != key3  # Different args = different key

    def test_get_and_set(self, cache):
        """Test basic get and set with stats tracking."""
        cache.set("key", "value")
        result = cache.get("key")
        assert result == "value"
        assert cache.hits == 1

    def test_cache_miss(self, cache):
        """Test cache miss tracking."""
        result = cache.get("nonexistent")
        assert result is None
        assert cache.misses == 1

    def test_get_stats(self, cache):
        """Test statistics retrieval."""
        cache.set("key", "value")
        cache.get("key")  # Hit
        cache.get("nonexistent")  # Miss

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["total"] == 2
        assert stats["hit_rate"] == "50.00%"

    def test_get_stats_empty(self, cache):
        """Test statistics with no requests."""
        stats = cache.get_stats()
        assert stats["hit_rate"] == "0.00%"

    def test_clear_resets_stats(self, cache):
        """Test that clear resets statistics."""
        cache.set("key", "value")
        cache.get("key")
        cache.clear()

        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0

    def test_delete(self, cache):
        """Test delete operation."""
        cache.set("key", "value")
        cache.delete("key")
        assert cache.get("key") is None


class TestRateLimiter:
    """Tests for RateLimiter."""

    def test_init(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(max_calls=10, time_window=60)
        assert limiter.max_calls == 10
        assert limiter.time_window == 60

    def test_is_allowed_under_limit(self):
        """Test that calls under limit are allowed."""
        limiter = RateLimiter(max_calls=5, time_window=60)
        for _ in range(5):
            assert limiter.is_allowed() is True

    def test_is_allowed_over_limit(self):
        """Test that calls over limit are blocked."""
        limiter = RateLimiter(max_calls=2, time_window=60)
        limiter.is_allowed()
        limiter.is_allowed()
        assert limiter.is_allowed() is False

    def test_window_expiration(self):
        """Test that old calls expire."""
        limiter = RateLimiter(max_calls=1, time_window=1)
        limiter.is_allowed()
        time.sleep(1.1)
        assert limiter.is_allowed() is True

    def test_wait_time_under_limit(self):
        """Test wait time when under limit."""
        limiter = RateLimiter(max_calls=5, time_window=60)
        assert limiter.wait_time() == 0.0

    def test_wait_time_at_limit(self):
        """Test wait time when at limit."""
        limiter = RateLimiter(max_calls=1, time_window=60)
        limiter.is_allowed()
        wait = limiter.wait_time()
        assert wait > 0
        assert wait <= 60

    def test_get_stats(self):
        """Test statistics retrieval."""
        limiter = RateLimiter(max_calls=10, time_window=60)
        limiter.is_allowed()
        limiter.is_allowed()

        stats = limiter.get_stats()
        assert stats["active_calls"] == 2
        assert stats["max_calls"] == 10
        assert stats["utilization"] == "20.0%"


class TestCachedDecorator:
    """Tests for @cached decorator."""

    @pytest.fixture(autouse=True)
    def reset_global_cache(self):
        """Reset global cache before each test."""
        import aiops.core.cache as cache_module
        cache_module._cache = None
        yield
        cache_module._cache = None

    @pytest.mark.asyncio
    async def test_cached_function(self):
        """Test that cached decorator caches results."""
        call_count = 0

        @cached(ttl=3600)
        async def expensive_operation(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = await expensive_operation(5)
        result2 = await expensive_operation(5)

        assert result1 == 10
        assert result2 == 10
        assert call_count == 1  # Should only be called once

    @pytest.mark.asyncio
    async def test_cached_different_args(self):
        """Test that different args create different cache entries."""
        call_count = 0

        @cached(ttl=3600)
        async def func(x):
            nonlocal call_count
            call_count += 1
            return x

        await func(1)
        await func(2)

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_cached_clear_cache(self):
        """Test clearing cache via wrapper method."""
        @cached(ttl=3600)
        async def func():
            return "value"

        await func()
        func.clear_cache()

        stats = func.get_cache_stats()
        assert stats["hits"] == 0


class TestRateLimitedDecorator:
    """Tests for @rate_limited decorator."""

    @pytest.mark.asyncio
    async def test_rate_limited_allows_calls(self):
        """Test that rate limited decorator allows calls under limit."""
        @rate_limited(max_calls=10, time_window=60)
        async def func():
            return "success"

        result = await func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_rate_limited_stats(self):
        """Test rate limiter stats access."""
        @rate_limited(max_calls=10, time_window=60)
        async def func():
            return "success"

        await func()
        stats = func.get_limiter_stats()
        assert stats["active_calls"] == 1


class TestEdgeCases:
    """Edge case tests."""

    def test_cache_with_none_value(self):
        """Test caching None values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(cache_dir=tmpdir, enable_redis=False)
            cache.set("none_key", None)
            # Note: This tests the current behavior - None is a valid cached value

    def test_empty_string_key(self):
        """Test empty string as key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FileBackend(Path(tmpdir))
            backend.set("", "value")
            result = backend.get("")
            assert result == "value"

    def test_very_long_key(self):
        """Test very long key handling."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(cache_dir=tmpdir, enable_redis=False)
            long_key = "x" * 10000
            cache.set(long_key, "value")
            # Key should be hashed, so this should work

    def test_unicode_in_values(self):
        """Test Unicode values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FileBackend(Path(tmpdir))
            backend.set("unicode", "Hello, 世界! 🌍")
            result = backend.get("unicode")
            assert result == "Hello, 世界! 🌍"

    def test_concurrent_access(self):
        """Test thread safety of cache operations."""
        import threading

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(cache_dir=tmpdir, enable_redis=False)
            errors = []

            def worker(n):
                try:
                    for i in range(10):
                        cache.set(f"key_{n}_{i}", f"value_{n}_{i}")
                        cache.get(f"key_{n}_{i}")
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert len(errors) == 0
