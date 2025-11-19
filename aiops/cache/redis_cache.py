"""Redis Cache System for AIOps

Provides caching for LLM responses, agent results, and other data.
"""

import asyncio
import json
import hashlib
from typing import Any, Optional, Union, Dict
from datetime import timedelta
import redis.asyncio as aioredis
from functools import wraps

from aiops.core.structured_logger import get_structured_logger


logger = get_structured_logger(__name__)


class RedisCache:
    """Redis-based caching system."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        default_ttl: int = 3600,
    ):
        """Initialize Redis cache.

        Args:
            redis_url: Redis connection URL
            default_ttl: Default TTL in seconds (1 hour)
        """
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.client: Optional[aioredis.Redis] = None

    async def connect(self):
        """Connect to Redis."""
        if self.client is None:
            self.client = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            logger.info("Connected to Redis", redis_url=self.redis_url)

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.client:
            await self.client.close()
            self.client = None
            logger.info("Disconnected from Redis")

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        await self.connect()
        
        try:
            value = await self.client.get(key)
            if value:
                logger.debug(f"Cache hit: {key}")
                return json.loads(value)
            else:
                logger.debug(f"Cache miss: {key}")
                return None
        except Exception as e:
            logger.error(f"Cache get error: {e}", key=key, error=str(e))
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """Set value in cache."""
        await self.connect()

        try:
            serialized = json.dumps(value)
            ttl = ttl or self.default_ttl
            await self.client.setex(key, ttl, serialized)
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}", key=key, error=str(e))
            return False


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


def cached(ttl: Optional[int] = None, key_prefix: str = ""):
    """Decorator to cache function results."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache()
            func_name = f"{func.__module__}.{func.__name__}"
            key_suffix = cache_key(*args, **kwargs)
            key = f"{key_prefix}:{func_name}:{key_suffix}" if key_prefix else f"{func_name}:{key_suffix}"
            
            cached_result = await cache.get(key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func_name}")
                return cached_result
            
            result = await func(*args, **kwargs)
            await cache.set(key, result, ttl=ttl)
            logger.debug(f"Cached result for {func_name}")
            
            return result
        return wrapper
    return decorator
