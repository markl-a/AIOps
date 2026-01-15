"""Redis Cache System for AIOps

Provides caching for LLM responses, agent results, and other data.
Includes automatic reconnection, stampede protection, and health monitoring.
"""

import asyncio
import json
import hashlib
import time
from typing import Any, Optional, Union, Dict
from datetime import timedelta
import redis.asyncio as aioredis
from functools import wraps

from aiops.core.structured_logger import get_structured_logger


logger = get_structured_logger(__name__)

# Global lock manager for async cache stampede prevention
_async_stampede_locks: Dict[str, asyncio.Lock] = {}
_async_stampede_locks_lock = asyncio.Lock()


class RedisCache:
    """Redis-based caching system with automatic reconnection and stampede protection."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        default_ttl: int = 3600,
        max_retries: int = 3,
        retry_backoff: float = 0.5,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
        max_connections: int = 50,
        enable_stampede_protection: bool = True,
    ):
        """Initialize Redis cache.

        Args:
            redis_url: Redis connection URL
            default_ttl: Default TTL in seconds (1 hour)
            max_retries: Maximum connection retry attempts
            retry_backoff: Base backoff time in seconds (exponential)
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Socket connect timeout in seconds
            max_connections: Maximum connections in pool
            enable_stampede_protection: Enable cache stampede protection
        """
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.max_connections = max_connections
        self.enable_stampede_protection = enable_stampede_protection
        self.client: Optional[aioredis.Redis] = None
        self._connected: bool = False
        self._connection_lock = asyncio.Lock()

        # Statistics
        self.hits = 0
        self.misses = 0

    async def connect(self):
        """Connect to Redis with retry logic."""
        if self._connected and self.client:
            # Already connected
            return

        async with self._connection_lock:
            if self._connected and self.client:
                return

            for attempt in range(self.max_retries):
                try:
                    self.client = await aioredis.from_url(
                        self.redis_url,
                        encoding="utf-8",
                        decode_responses=True,
                        socket_timeout=self.socket_timeout,
                        socket_connect_timeout=self.socket_connect_timeout,
                        max_connections=self.max_connections,
                        socket_keepalive=True,
                        retry_on_timeout=True,
                    )

                    # Test connection
                    await self.client.ping()
                    self._connected = True

                    if attempt > 0:
                        logger.info(
                            f"Redis reconnected successfully after {attempt + 1} attempts",
                            redis_url=self.redis_url
                        )
                    else:
                        logger.info(
                            "Connected to Redis",
                            redis_url=self.redis_url,
                            max_connections=self.max_connections
                        )
                    return

                except Exception as e:
                    backoff_time = self.retry_backoff * (2 ** attempt)
                    if attempt < self.max_retries - 1:
                        logger.warning(
                            f"Redis connection attempt {attempt + 1}/{self.max_retries} failed: {e}. "
                            f"Retrying in {backoff_time:.2f}s..."
                        )
                        await asyncio.sleep(backoff_time)
                    else:
                        logger.error(
                            f"Redis connection failed after {self.max_retries} attempts",
                            error=str(e)
                        )
                        raise

    async def _ensure_connection(self) -> bool:
        """Ensure Redis connection is alive, reconnect if needed.

        Returns:
            True if connected, False otherwise
        """
        if not self._connected or not self.client:
            try:
                await self.connect()
                return True
            except Exception as e:
                logger.debug(f"Redis initial connection failed: {e}")
                return False

        try:
            # Quick ping to verify connection
            await self.client.ping()
            return True
        except Exception as e:
            logger.warning(f"Redis connection lost: {e}. Attempting reconnection...")
            self._connected = False
            try:
                await self.connect()
                return True
            except Exception as e:
                logger.debug(f"Redis reconnection failed: {e}")
                return False

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.client:
            await self.client.close()
            self.client = None
            self._connected = False
            logger.info("Disconnected from Redis")

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache with automatic reconnection."""
        if not await self._ensure_connection():
            logger.warning("Redis unavailable, returning cache miss")
            self.misses += 1
            return None

        try:
            value = await self.client.get(key)
            if value:
                self.hits += 1
                logger.debug(f"Cache hit: {key}")
                return json.loads(value)
            else:
                self.misses += 1
                logger.debug(f"Cache miss: {key}")
                return None
        except Exception as e:
            logger.error(f"Cache get error: {e}", key=key, error=str(e))
            self._connected = False
            self.misses += 1
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """Set value in cache with automatic reconnection."""
        if not await self._ensure_connection():
            logger.warning("Redis unavailable, skipping cache set")
            return False

        try:
            serialized = json.dumps(value)
            ttl = ttl or self.default_ttl
            await self.client.setex(key, ttl, serialized)
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}", key=key, error=str(e))
            self._connected = False
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache.

        Args:
            key: Key to delete

        Returns:
            True if successful, False otherwise
        """
        if not await self._ensure_connection():
            return False

        try:
            await self.client.delete(key)
            logger.debug(f"Cache delete: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}", key=key, error=str(e))
            self._connected = False
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern.

        Args:
            pattern: Pattern to match (e.g., "user:*", "session:123:*")

        Returns:
            Number of keys deleted
        """
        if not await self._ensure_connection():
            return 0

        try:
            # Use SCAN instead of KEYS for production safety
            cursor = 0
            deleted_count = 0

            while True:
                cursor, keys = await self.client.scan(cursor, match=pattern, count=100)
                if keys:
                    deleted_count += await self.client.delete(*keys)
                if cursor == 0:
                    break

            logger.info(f"Deleted {deleted_count} keys matching pattern: {pattern}")
            return deleted_count
        except Exception as e:
            logger.error(f"Cache delete_pattern error: {e}", pattern=pattern, error=str(e))
            self._connected = False
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Key to check

        Returns:
            True if exists, False otherwise
        """
        if not await self._ensure_connection():
            return False

        try:
            return await self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists error: {e}", key=key, error=str(e))
            self._connected = False
            return False

    async def clear(self, pattern: str = "*") -> int:
        """Clear cache entries matching pattern.

        Args:
            pattern: Pattern to match (default: all keys)

        Returns:
            Number of keys deleted
        """
        return await self.delete_pattern(pattern)

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics and health information.

        Returns:
            Statistics dictionary
        """
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0

        stats = {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total,
            "hit_rate": f"{hit_rate:.2f}%",
            "connected": self._connected,
            "stampede_protection": self.enable_stampede_protection,
        }

        if await self._ensure_connection():
            try:
                start = time.time()
                info = await self.client.info()
                latency = (time.time() - start) * 1000

                stats.update({
                    "redis_health": "healthy",
                    "latency_ms": round(latency, 2),
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory_human": info.get("used_memory_human", "unknown"),
                    "uptime_days": info.get("uptime_in_days", 0),
                })
            except Exception as e:
                stats["redis_health"] = f"error: {str(e)}"
        else:
            stats["redis_health"] = "disconnected"

        return stats

    async def _get_stampede_lock(self, key: str) -> asyncio.Lock:
        """Get or create a lock for cache stampede prevention.

        Args:
            key: Cache key to lock

        Returns:
            Lock for the given key
        """
        async with _async_stampede_locks_lock:
            if key not in _async_stampede_locks:
                _async_stampede_locks[key] = asyncio.Lock()
            return _async_stampede_locks[key]

    async def _cleanup_stampede_lock(self, key: str):
        """Clean up stampede lock after use.

        Args:
            key: Cache key to unlock
        """
        async with _async_stampede_locks_lock:
            if key in _async_stampede_locks:
                # Only delete if not locked by anyone
                lock = _async_stampede_locks[key]
                if not lock.locked():
                    del _async_stampede_locks[key]


_cache: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    """Get global cache instance."""
    global _cache
    if _cache is None:
        import os
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _cache = RedisCache(redis_url=redis_url)
    return _cache


def cache_key(*args, **kwargs) -> str:
    """Generate cache key from arguments."""
    key_parts = [str(arg) for arg in args]
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    key_string = "|".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


def cached(ttl: Optional[int] = None, key_prefix: str = "", enable_stampede_protection: bool = True):
    """Decorator to cache function results with stampede protection.

    Args:
        ttl: Time-to-live in seconds
        key_prefix: Prefix for cache keys
        enable_stampede_protection: Prevent cache stampede (default: True)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache()
            func_name = f"{func.__module__}.{func.__name__}"
            key_suffix = cache_key(*args, **kwargs)
            key = f"{key_prefix}:{func_name}:{key_suffix}" if key_prefix else f"{func_name}:{key_suffix}"

            # Try to get from cache (first attempt without lock)
            cached_result = await cache.get(key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func_name}")
                return cached_result

            # Cache miss - use stampede protection if enabled
            if enable_stampede_protection and cache.enable_stampede_protection:
                # Acquire lock to prevent multiple coroutines from computing same value
                lock = await cache._get_stampede_lock(key)

                # Check if another coroutine is already computing
                if lock.locked():
                    logger.debug(f"Waiting for another coroutine to compute {func_name}")
                    async with lock:
                        # Once we acquire lock, check cache again
                        cached_result = await cache.get(key)
                        if cached_result is not None:
                            return cached_result

                # We got the lock first, compute the value
                async with lock:
                    # Double-check cache (another coroutine might have filled it)
                    cached_result = await cache.get(key)
                    if cached_result is not None:
                        return cached_result

                    # Execute function
                    logger.debug(f"Computing fresh result for {func_name}")
                    result = await func(*args, **kwargs)

                    # Cache result
                    await cache.set(key, result, ttl=ttl)

                # Cleanup lock
                await cache._cleanup_stampede_lock(key)

                return result
            else:
                # No stampede protection - just execute
                result = await func(*args, **kwargs)
                await cache.set(key, result, ttl=ttl)
                logger.debug(f"Cached result for {func_name}")
                return result

        return wrapper
    return decorator
