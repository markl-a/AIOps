"""Caching system for AIOps framework."""

import hashlib
import json
import time
from typing import Any, Optional, Callable
from pathlib import Path
from functools import wraps
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class Cache:
    """Simple file-based cache for LLM responses."""

    def __init__(self, cache_dir: str = ".aiops_cache", ttl: int = 3600):
        """
        Initialize cache.

        Args:
            cache_dir: Directory to store cache files
            ttl: Time-to-live in seconds (default: 1 hour)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl
        self.hits = 0
        self.misses = 0

    def _get_cache_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        # Create a deterministic key from args and kwargs
        key_data = {
            "args": str(args),
            "kwargs": str(sorted(kwargs.items())),
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()

    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for a key."""
        return self.cache_dir / f"{key}.json"

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            self.misses += 1
            return None

        try:
            with open(cache_path, "r") as f:
                cached = json.load(f)

            # Check if expired
            if time.time() - cached["timestamp"] > self.ttl:
                cache_path.unlink()  # Delete expired cache
                self.misses += 1
                logger.debug(f"Cache expired for key: {key[:8]}...")
                return None

            self.hits += 1
            logger.debug(f"Cache hit for key: {key[:8]}...")
            return cached["value"]

        except Exception as e:
            logger.warning(f"Error reading cache: {e}")
            self.misses += 1
            return None

    def set(self, key: str, value: Any):
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        cache_path = self._get_cache_path(key)

        try:
            cached = {
                "timestamp": time.time(),
                "value": value,
            }

            with open(cache_path, "w") as f:
                json.dump(cached, f)

            logger.debug(f"Cached value for key: {key[:8]}...")

        except Exception as e:
            logger.warning(f"Error writing cache: {e}")

    def clear(self):
        """Clear all cache files."""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()

        self.hits = 0
        self.misses = 0
        logger.info("Cache cleared")

    def get_stats(self) -> dict:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "total": total,
            "hit_rate": f"{hit_rate:.2f}%",
            "cache_size": sum(f.stat().st_size for f in self.cache_dir.glob("*.json")),
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
