"""Caching system for AIOps framework with Redis and file-based backends."""

import hashlib
import json
import time
import pickle
import os
from typing import Any, Optional, Callable
from pathlib import Path
from functools import wraps
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class CacheBackend:
    """Base cache backend interface."""

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        raise NotImplementedError

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache."""
        raise NotImplementedError

    def delete(self, key: str):
        """Delete key from cache."""
        raise NotImplementedError

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        raise NotImplementedError

    def clear(self):
        """Clear all cache entries."""
        raise NotImplementedError


class RedisBackend(CacheBackend):
    """Redis cache backend."""

    def __init__(self, redis_url: str, prefix: str = "aiops"):
        """Initialize Redis backend."""
        try:
            import redis
            self.client = redis.from_url(redis_url, decode_responses=False)
            self.prefix = prefix
            self.enabled = True
            # Test connection
            self.client.ping()
            logger.info(f"Redis cache backend initialized: {redis_url}")
        except ImportError:
            logger.warning("redis package not installed. Install with: pip install redis")
            self.enabled = False
            self.client = None
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.enabled = False
            self.client = None

    def _make_key(self, key: str) -> str:
        """Create prefixed key."""
        return f"{self.prefix}:{key}"

    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis."""
        if not self.enabled:
            return None
        try:
            value = self.client.get(self._make_key(key))
            if value:
                return pickle.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in Redis."""
        if not self.enabled:
            return
        try:
            serialized = pickle.dumps(value)
            if ttl:
                self.client.setex(self._make_key(key), ttl, serialized)
            else:
                self.client.set(self._make_key(key), serialized)
        except Exception as e:
            logger.error(f"Redis set error: {e}")

    def delete(self, key: str):
        """Delete key from Redis."""
        if not self.enabled:
            return
        try:
            self.client.delete(self._make_key(key))
        except Exception as e:
            logger.error(f"Redis delete error: {e}")

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self.enabled:
            return False
        try:
            return self.client.exists(self._make_key(key)) > 0
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False

    def clear(self):
        """Clear all keys with prefix."""
        if not self.enabled:
            return
        try:
            keys = self.client.keys(f"{self.prefix}:*")
            if keys:
                self.client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis clear error: {e}")


class FileBackend(CacheBackend):
    """File-based cache backend."""

    def __init__(self, cache_dir: Path):
        """Initialize file backend."""
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path."""
        return self.cache_dir / f"{key}.cache"

    def get(self, key: str) -> Optional[Any]:
        """Get value from file cache."""
        cache_path = self._get_cache_path(key)
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "rb") as f:
                data = pickle.load(f)

            # Check expiration
            if "expires_at" in data and data["expires_at"]:
                if time.time() > data["expires_at"]:
                    cache_path.unlink()
                    return None

            return data["value"]
        except Exception as e:
            logger.error(f"File cache get error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in file cache."""
        cache_path = self._get_cache_path(key)

        try:
            data = {
                "value": value,
                "created_at": time.time(),
                "expires_at": time.time() + ttl if ttl else None,
            }

            with open(cache_path, "wb") as f:
                pickle.dump(data, f)
        except Exception as e:
            logger.error(f"File cache set error: {e}")

    def delete(self, key: str):
        """Delete key from file cache."""
        cache_path = self._get_cache_path(key)
        try:
            if cache_path.exists():
                cache_path.unlink()
        except Exception as e:
            logger.error(f"File cache delete error: {e}")

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        return self._get_cache_path(key).exists()

    def clear(self):
        """Clear all file cache entries."""
        try:
            for cache_file in self.cache_dir.glob("*.cache"):
                cache_file.unlink()
        except Exception as e:
            logger.error(f"File cache clear error: {e}")


class Cache:
    """Unified cache with Redis and file-based backends."""

    def __init__(self, cache_dir: str = ".aiops_cache", ttl: int = 3600, enable_redis: bool = None):
        """
        Initialize cache.

        Args:
            cache_dir: Directory to store cache files
            ttl: Time-to-live in seconds (default: 1 hour)
            enable_redis: Enable Redis backend (auto-detect if None)
        """
        self.ttl = ttl
        self.hits = 0
        self.misses = 0

        # Determine if Redis should be used
        if enable_redis is None:
            enable_redis = os.getenv("ENABLE_REDIS", "false").lower() == "true"

        # Initialize backend
        if enable_redis:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self.backend = RedisBackend(redis_url)
            if not self.backend.enabled:
                logger.warning("Redis unavailable, falling back to file cache")
                self.backend = FileBackend(Path(cache_dir))
        else:
            self.backend = FileBackend(Path(cache_dir))

        logger.info(f"Cache initialized with {self.backend.__class__.__name__}")

    def _get_cache_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = {
            "args": str(args),
            "kwargs": str(sorted(kwargs.items())),
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        value = self.backend.get(key)
        if value is not None:
            self.hits += 1
            logger.debug(f"Cache hit: {key[:8]}...")
            return value
        else:
            self.misses += 1
            logger.debug(f"Cache miss: {key[:8]}...")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache."""
        ttl = ttl or self.ttl
        self.backend.set(key, value, ttl)
        logger.debug(f"Cached value: {key[:8]}... (TTL: {ttl}s)")

    def delete(self, key: str):
        """Delete key from cache."""
        self.backend.delete(key)

    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        return self.backend.exists(key)

    def clear(self):
        """Clear all cache entries."""
        self.backend.clear()
        self.hits = 0
        self.misses = 0
        logger.info("Cache cleared")

    def get_stats(self) -> dict:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0

        return {
            "backend": self.backend.__class__.__name__,
            "hits": self.hits,
            "misses": self.misses,
            "total": total,
            "hit_rate": f"{hit_rate:.2f}%",
        }


# Global cache instance
_cache: Optional[Cache] = None


def get_cache(ttl: int = 3600) -> Cache:
    """Get or create global cache instance."""
    global _cache
    if _cache is None:
        _cache = Cache(ttl=ttl)
    return _cache


def cached(ttl: Optional[int] = None):
    """
    Decorator to cache function results.

    Args:
        ttl: Time-to-live in seconds (uses global default if None)

    Example:
        @cached(ttl=3600)
        async def expensive_operation(arg1, arg2):
            # ... expensive computation
            return result
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache(ttl=ttl) if ttl else get_cache()

            # Generate cache key
            cache_key = cache._get_cache_key(func.__name__, *args, **kwargs)

            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Returning cached result for {func.__name__}")
                return cached_result

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            cache.set(cache_key, result)

            return result

        # Add cache management methods
        wrapper.clear_cache = lambda: get_cache().clear()
        wrapper.get_cache_stats = lambda: get_cache().get_stats()

        return wrapper

    return decorator


class RateLimiter:
    """Rate limiter for API calls."""

    def __init__(self, max_calls: int = 60, time_window: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_calls: Maximum number of calls allowed
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []

    def is_allowed(self) -> bool:
        """Check if a new call is allowed."""
        now = time.time()

        # Remove old calls outside time window
        self.calls = [call_time for call_time in self.calls if now - call_time < self.time_window]

        # Check if under limit
        if len(self.calls) < self.max_calls:
            self.calls.append(now)
            return True

        return False

    def wait_time(self) -> float:
        """Get wait time until next call is allowed."""
        if len(self.calls) < self.max_calls:
            return 0.0

        oldest_call = min(self.calls)
        return max(0.0, self.time_window - (time.time() - oldest_call))

    def get_stats(self) -> dict:
        """Get rate limiter statistics."""
        now = time.time()
        active_calls = len([c for c in self.calls if now - c < self.time_window])

        return {
            "active_calls": active_calls,
            "max_calls": self.max_calls,
            "time_window": self.time_window,
            "utilization": f"{active_calls / self.max_calls * 100:.1f}%",
        }


def rate_limited(max_calls: int = 60, time_window: int = 60):
    """
    Decorator to rate limit function calls.

    Args:
        max_calls: Maximum calls allowed in time window
        time_window: Time window in seconds

    Example:
        @rate_limited(max_calls=10, time_window=60)
        async def api_call():
            # ... API call
    """
    limiter = RateLimiter(max_calls, time_window)

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            while not limiter.is_allowed():
                wait_time = limiter.wait_time()
                logger.warning(f"Rate limit reached. Waiting {wait_time:.2f}s...")
                await asyncio.sleep(wait_time)

            return await func(*args, **kwargs)

        wrapper.get_limiter_stats = lambda: limiter.get_stats()

        return wrapper

    return decorator


import asyncio
