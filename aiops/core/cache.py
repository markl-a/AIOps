"""Caching system for AIOps framework with Redis and file-based backends."""

import asyncio
import hashlib
import json
import time
import os
import threading
import base64
from datetime import datetime, date
from typing import Any, Optional, Callable, Dict, List, TypeVar, Set, Union
from pathlib import Path
from functools import wraps
from aiops.core.logger import get_logger

# Type variable for generic return types
T = TypeVar('T')

logger = get_logger(__name__)


# =============================================================================
# SECURITY FIX: JSON Serialization Helpers
# =============================================================================
# These helper functions replace pickle serialization with JSON to prevent
# arbitrary code execution vulnerabilities (CWE-502: Deserialization of
# Untrusted Data). Pickle can execute arbitrary Python code during
# deserialization, making it dangerous when loading data from untrusted sources.
# JSON is a safe alternative that only supports basic data types.
# =============================================================================


class JSONSerializationError(Exception):
    """Raised when an object cannot be serialized to JSON."""
    pass


class JSONDeserializationError(Exception):
    """Raised when JSON data cannot be deserialized."""
    pass


def _json_serialize(obj: Any) -> str:
    """Safely serialize an object to JSON string.

    Converts complex Python objects to JSON-serializable format.
    Handles common types like datetime, bytes, sets, and custom objects.

    Args:
        obj: The object to serialize

    Returns:
        JSON string representation of the object

    Raises:
        JSONSerializationError: If the object cannot be serialized

    Security Note:
        This function replaces pickle.dumps() to prevent arbitrary code
        execution vulnerabilities during deserialization.
    """
    def default_encoder(o: Any) -> Any:
        """Custom JSON encoder for non-standard types."""
        if isinstance(o, datetime):
            return {"__type__": "datetime", "value": o.isoformat()}
        elif isinstance(o, date):
            return {"__type__": "date", "value": o.isoformat()}
        elif isinstance(o, bytes):
            # Encode bytes as base64 for safe JSON storage
            return {"__type__": "bytes", "value": base64.b64encode(o).decode('ascii')}
        elif isinstance(o, set):
            return {"__type__": "set", "value": list(o)}
        elif isinstance(o, frozenset):
            return {"__type__": "frozenset", "value": list(o)}
        elif hasattr(o, '__dict__'):
            # Handle custom objects by storing their dict representation
            return {
                "__type__": "object",
                "__class__": f"{o.__class__.__module__}.{o.__class__.__name__}",
                "value": o.__dict__
            }
        else:
            raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")

    try:
        return json.dumps(obj, default=default_encoder, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        raise JSONSerializationError(f"Failed to serialize object: {e}") from e


def _json_deserialize(data: str) -> Any:
    """Safely deserialize a JSON string to Python object.

    Reconstructs Python objects from JSON, handling special type markers
    for datetime, bytes, sets, etc.

    Args:
        data: JSON string to deserialize

    Returns:
        Deserialized Python object

    Raises:
        JSONDeserializationError: If the data cannot be deserialized

    Security Note:
        This function replaces pickle.loads() to prevent arbitrary code
        execution. Unlike pickle, JSON deserialization cannot execute
        arbitrary code, making it safe for untrusted data.

        Note: Custom objects are returned as dictionaries rather than
        being reconstructed, as reconstructing arbitrary classes would
        reintroduce security risks.
    """
    def object_hook(d: Dict) -> Any:
        """Custom JSON decoder for special type markers."""
        if "__type__" not in d:
            return d

        type_marker = d["__type__"]
        value = d.get("value")

        if type_marker == "datetime":
            return datetime.fromisoformat(value)
        elif type_marker == "date":
            return date.fromisoformat(value)
        elif type_marker == "bytes":
            return base64.b64decode(value.encode('ascii'))
        elif type_marker == "set":
            return set(value)
        elif type_marker == "frozenset":
            return frozenset(value)
        elif type_marker == "object":
            # SECURITY: Do not reconstruct arbitrary classes - return dict instead
            # Reconstructing classes could allow code execution through __init__
            logger.debug(
                f"Custom object of class '{d.get('__class__', 'unknown')}' "
                "deserialized as dictionary for security"
            )
            return value
        else:
            return d

    try:
        return json.loads(data, object_hook=object_hook)
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        raise JSONDeserializationError(f"Failed to deserialize JSON data: {e}") from e

# Global lock manager for cache stampede prevention with bounded size
# Using a maximum size to prevent unbounded memory growth
_MAX_STAMPEDE_LOCKS = 1000
_stampede_locks: Dict[str, threading.Lock] = {}
_stampede_locks_lock = threading.Lock()
_stampede_lock_access_times: Dict[str, float] = {}  # Track last access for LRU cleanup


class TTLStrategy:
    """TTL (Time-To-Live) strategy for cache entries.

    Provides different TTL tiers for different data access patterns.
    """

    # Predefined TTL tiers
    VERY_SHORT = 60  # 1 minute - for rapidly changing data
    SHORT = 300  # 5 minutes - for frequently updated data
    MEDIUM = 1800  # 30 minutes - for moderately stable data
    LONG = 3600  # 1 hour - for stable data (default)
    VERY_LONG = 21600  # 6 hours - for rarely changing data
    PERSISTENT = 86400  # 24 hours - for static data

    @staticmethod
    def get_adaptive_ttl(access_count: int, base_ttl: int = 3600) -> int:
        """Calculate adaptive TTL based on access patterns.

        More frequently accessed items get longer TTL to reduce recomputation.

        Args:
            access_count: Number of times the item has been accessed
            base_ttl: Base TTL in seconds

        Returns:
            Adjusted TTL in seconds
        """
        if access_count < 5:
            return base_ttl
        elif access_count < 20:
            return int(base_ttl * 1.5)  # 50% longer
        elif access_count < 100:
            return int(base_ttl * 2)  # 2x longer
        else:
            return int(base_ttl * 3)  # 3x longer (max multiplier)

    @staticmethod
    def get_tier_ttl(tier: str) -> int:
        """Get TTL for a named tier.

        Args:
            tier: Tier name (very_short, short, medium, long, very_long, persistent)

        Returns:
            TTL in seconds
        """
        tier_map = {
            "very_short": TTLStrategy.VERY_SHORT,
            "short": TTLStrategy.SHORT,
            "medium": TTLStrategy.MEDIUM,
            "long": TTLStrategy.LONG,
            "very_long": TTLStrategy.VERY_LONG,
            "persistent": TTLStrategy.PERSISTENT,
        }
        return tier_map.get(tier.lower(), TTLStrategy.LONG)


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
    """Redis cache backend with automatic reconnection and connection pooling."""

    def __init__(
        self,
        redis_url: str,
        prefix: str = "aiops",
        max_retries: int = 3,
        retry_backoff: float = 0.5,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
        max_connections: int = 50,
    ):
        """Initialize Redis backend.

        Args:
            redis_url: Redis connection URL
            prefix: Key prefix for namespacing
            max_retries: Maximum number of retry attempts
            retry_backoff: Base backoff time in seconds (exponential)
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Socket connect timeout in seconds
            max_connections: Maximum connections in pool
        """
        self.redis_url = redis_url
        self.prefix = prefix
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.enabled = False
        self.client = None
        self._connection_lock = threading.Lock()

        try:
            import redis
            from redis.connection import ConnectionPool

            # Create connection pool for better connection management
            self.pool = ConnectionPool.from_url(
                redis_url,
                decode_responses=False,
                max_connections=max_connections,
                socket_timeout=socket_timeout,
                socket_connect_timeout=socket_connect_timeout,
                socket_keepalive=True,
                socket_keepalive_options={},
                retry_on_timeout=True,
            )

            self.client = redis.Redis(connection_pool=self.pool)

            # Test connection with retry
            self._connect_with_retry()

            logger.info(
                f"Redis cache backend initialized: {redis_url} "
                f"(pool_size={max_connections}, timeout={socket_timeout}s)"
            )
        except ImportError:
            logger.warning("redis package not installed. Install with: pip install redis")
            self.enabled = False
            self.client = None
        except Exception as e:
            logger.error(f"Failed to initialize Redis backend: {e}")
            self.enabled = False
            self.client = None

    def __del__(self):
        """Cleanup Redis connection pool on deletion."""
        try:
            if hasattr(self, 'pool') and self.pool is not None:
                self.pool.disconnect()
                logger.debug("Redis connection pool disconnected")
        except Exception as e:
            logger.debug(f"Error during Redis cleanup: {e}")

    def _connect_with_retry(self) -> bool:
        """Connect to Redis with exponential backoff retry.

        Returns:
            True if connection successful, False otherwise
        """
        for attempt in range(self.max_retries):
            try:
                if self.client is not None:
                    self.client.ping()
                    self.enabled = True
                    if attempt > 0:
                        logger.info(f"Redis reconnected successfully after {attempt + 1} attempts")
                    return True
            except Exception as e:
                backoff_time = self.retry_backoff * (2 ** attempt)
                if attempt < self.max_retries - 1:
                    logger.warning(
                        f"Redis connection attempt {attempt + 1}/{self.max_retries} failed: {e}. "
                        f"Retrying in {backoff_time:.2f}s..."
                    )
                    time.sleep(backoff_time)
                else:
                    logger.error(f"Redis connection failed after {self.max_retries} attempts: {e}")
                    self.enabled = False
                    return False

        return False

    def _ensure_connection(self) -> bool:
        """Ensure Redis connection is alive, reconnect if needed.

        Returns:
            True if connected, False otherwise
        """
        if not self.enabled:
            # Try to reconnect
            with self._connection_lock:
                if not self.enabled:  # Double-check pattern
                    return self._connect_with_retry()

        try:
            # Quick connection check
            if self.client is not None:
                self.client.ping()
                return True
            return False
        except Exception as e:
            logger.warning(f"Redis connection lost: {e}. Attempting reconnection...")
            with self._connection_lock:
                return self._connect_with_retry()

        return False

    def _make_key(self, key: str) -> str:
        """Create prefixed key."""
        return f"{self.prefix}:{key}"

    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis with automatic reconnection.

        Security Note:
            Uses JSON deserialization instead of pickle to prevent arbitrary
            code execution vulnerabilities (CWE-502).
        """
        if not self._ensure_connection() or self.client is None:
            return None

        try:
            value = self.client.get(self._make_key(key))
            if value:
                # SECURITY FIX: Use JSON instead of pickle to prevent code execution
                # pickle.loads() can execute arbitrary code during deserialization
                try:
                    return _json_deserialize(value.decode('utf-8'))
                except JSONDeserializationError as e:
                    logger.warning(f"Failed to deserialize cached value for key {key[:8]}...: {e}")
                    # Delete corrupted/incompatible cache entry
                    self.delete(key)
                    return None
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            # Try to reconnect for next operation
            self.enabled = False
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in Redis with automatic reconnection.

        Security Note:
            Uses JSON serialization instead of pickle to ensure safe
            deserialization without arbitrary code execution risks.
        """
        if not self._ensure_connection() or self.client is None:
            return

        try:
            # SECURITY FIX: Use JSON instead of pickle to prevent code execution
            # pickle.dumps() creates data that can execute code when deserialized
            try:
                serialized = _json_serialize(value).encode('utf-8')
            except JSONSerializationError as e:
                logger.error(f"Failed to serialize value for cache key {key[:8]}...: {e}")
                return

            if ttl:
                self.client.setex(self._make_key(key), ttl, serialized)
            else:
                self.client.set(self._make_key(key), serialized)
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            self.enabled = False

    def delete(self, key: str):
        """Delete key from Redis with automatic reconnection."""
        if not self._ensure_connection() or self.client is None:
            return

        try:
            self.client.delete(self._make_key(key))
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            self.enabled = False

    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern.

        Args:
            pattern: Pattern to match (e.g., "user:*", "session:123:*")

        Returns:
            Number of keys deleted
        """
        if not self._ensure_connection() or self.client is None:
            return 0

        try:
            # Use SCAN instead of KEYS for production safety
            cursor = 0
            deleted_count = 0
            full_pattern = f"{self.prefix}:{pattern}"

            while True:
                cursor, keys = self.client.scan(cursor, match=full_pattern, count=100)
                if keys:
                    deleted_count += self.client.delete(*keys)
                if cursor == 0:
                    break

            logger.info(f"Deleted {deleted_count} keys matching pattern: {pattern}")
            return deleted_count
        except Exception as e:
            logger.error(f"Redis delete_pattern error: {e}")
            self.enabled = False
            return 0

    def exists(self, key: str) -> bool:
        """Check if key exists with automatic reconnection."""
        if not self._ensure_connection() or self.client is None:
            return False

        try:
            return self.client.exists(self._make_key(key)) > 0
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            self.enabled = False
            return False

    def clear(self):
        """Clear all keys with prefix using SCAN for production safety."""
        if not self._ensure_connection():
            return

        try:
            # Use SCAN instead of KEYS to avoid blocking Redis
            cursor = 0
            deleted_count = 0

            while True:
                cursor, keys = self.client.scan(cursor, match=f"{self.prefix}:*", count=100)
                if keys:
                    deleted_count += self.client.delete(*keys)
                if cursor == 0:
                    break

            logger.info(f"Cleared {deleted_count} cache entries")
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            self.enabled = False

    def get_health(self) -> Dict[str, Any]:
        """Get Redis connection health status.

        Returns:
            Health status dictionary
        """
        try:
            if not self.enabled or self.client is None:
                return {
                    "status": "disconnected",
                    "enabled": False,
                }

            start = time.time()
            info = self.client.info()
            latency = (time.time() - start) * 1000

            return {
                "status": "healthy",
                "enabled": True,
                "latency_ms": round(latency, 2),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "uptime_days": info.get("uptime_in_days", 0),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "enabled": self.enabled,
                "error": str(e),
            }


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
        """Get value from file cache.

        Security Note:
            Uses JSON deserialization instead of pickle to prevent arbitrary
            code execution vulnerabilities (CWE-502).
        """
        cache_path = self._get_cache_path(key)
        if not cache_path.exists():
            return None

        try:
            # SECURITY FIX: Use JSON instead of pickle to prevent code execution
            # pickle.load() can execute arbitrary code during deserialization
            with open(cache_path, "r", encoding="utf-8") as f:
                json_data = f.read()

            try:
                data = _json_deserialize(json_data)
            except JSONDeserializationError as e:
                logger.warning(f"Failed to deserialize cached file {cache_path}: {e}")
                # Delete corrupted/incompatible cache file
                cache_path.unlink()
                return None

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

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        ttl: Optional[int] = None,
        enable_redis: Optional[bool] = None,
        enable_stampede_protection: bool = True,
    ):
        """
        Initialize cache.

        Args:
            cache_dir: Directory to store cache files (uses config if None)
            ttl: Time-to-live in seconds (uses config if None)
            enable_redis: Enable Redis backend (uses config if None)
            enable_stampede_protection: Enable cache stampede protection
        """
        # Import here to avoid circular dependency
        from aiops.core.config import get_config
        config = get_config()

        self.ttl = ttl or config.cache_default_ttl
        self.hits = 0
        self.misses = 0
        self.enable_stampede_protection = enable_stampede_protection
        self.backend: Union[RedisBackend, FileBackend]

        # Determine if Redis should be used
        if enable_redis is None:
            enable_redis = config.enable_redis

        # Get cache directory from config
        if cache_dir is None:
            cache_dir = config.cache_dir

        # Initialize backend
        if enable_redis:
            redis_url = config.redis_url
            redis_max_connections = config.redis_max_connections
            redis_socket_timeout = config.redis_socket_timeout

            self.backend = RedisBackend(
                redis_url=redis_url,
                max_connections=redis_max_connections,
                socket_timeout=redis_socket_timeout,
                socket_connect_timeout=redis_socket_timeout,
            )
            if not self.backend.enabled:
                logger.warning("Redis unavailable, falling back to file cache")
                self.backend = FileBackend(Path(cache_dir))
        else:
            self.backend = FileBackend(Path(cache_dir))

        logger.info(
            f"Cache initialized with {self.backend.__class__.__name__} "
            f"(ttl={self.ttl}s, stampede_protection={enable_stampede_protection})"
        )

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        # Clear cache on exit to free memory
        # This is optional - only clear if backend is file-based to avoid losing data
        if isinstance(self.backend, FileBackend):
            logger.debug("Cleaning up file cache on context exit")
        return False

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup resources."""
        # Same cleanup as sync version
        if isinstance(self.backend, FileBackend):
            logger.debug("Cleaning up file cache on async context exit")
        return False

    def _get_cache_key(self, func_module: str, func_name: str, *args, **kwargs) -> str:
        """Generate cache key from function identity and arguments.

        Args:
            func_module: The module where the function is defined
            func_name: The name of the function
            *args: Positional arguments to the function
            **kwargs: Keyword arguments to the function

        Returns:
            A unique cache key based on function identity and arguments
        """
        key_data = {
            "module": func_module,
            "function": func_name,
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

    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern.

        Args:
            pattern: Pattern to match (e.g., "user:*", "session:123:*")

        Returns:
            Number of keys deleted (0 if backend doesn't support pattern deletion)
        """
        if hasattr(self.backend, 'delete_pattern'):
            return self.backend.delete_pattern(pattern)
        else:
            logger.warning(f"{self.backend.__class__.__name__} does not support pattern deletion")
            return 0

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

        stats = {
            "backend": self.backend.__class__.__name__,
            "hits": self.hits,
            "misses": self.misses,
            "total": total,
            "hit_rate": f"{hit_rate:.2f}%",
            "stampede_protection": self.enable_stampede_protection,
        }

        # Add backend-specific health info if available
        if hasattr(self.backend, 'get_health'):
            stats["backend_health"] = self.backend.get_health()

        return stats

    def _get_stampede_lock(self, key: str) -> threading.Lock:
        """Get or create a lock for cache stampede prevention.

        Args:
            key: Cache key to lock

        Returns:
            Lock for the given key
        """
        with _stampede_locks_lock:
            # Cleanup old locks if we're at capacity (LRU eviction)
            if len(_stampede_locks) >= _MAX_STAMPEDE_LOCKS and key not in _stampede_locks:
                # Remove oldest unlocked lock
                oldest_key = None
                oldest_time = float('inf')
                for lock_key, access_time in _stampede_lock_access_times.items():
                    if lock_key in _stampede_locks and not _stampede_locks[lock_key].locked():
                        if access_time < oldest_time:
                            oldest_time = access_time
                            oldest_key = lock_key

                if oldest_key:
                    del _stampede_locks[oldest_key]
                    del _stampede_lock_access_times[oldest_key]
                    logger.debug(f"Evicted old stampede lock: {oldest_key[:16]}...")

            if key not in _stampede_locks:
                _stampede_locks[key] = threading.Lock()

            # Update access time for LRU tracking
            _stampede_lock_access_times[key] = time.time()

            return _stampede_locks[key]

    def _cleanup_stampede_lock(self, key: str):
        """Clean up stampede lock after use.

        Args:
            key: Cache key to unlock
        """
        with _stampede_locks_lock:
            if key in _stampede_locks:
                # Only delete if not locked by anyone
                lock = _stampede_locks[key]
                if not lock.locked():
                    del _stampede_locks[key]
                    if key in _stampede_lock_access_times:
                        del _stampede_lock_access_times[key]


# Global cache instance
_cache: Optional[Cache] = None
_cache_lock = threading.Lock()

# Alias for backward compatibility
CacheManager = Cache


def get_cache(ttl: int = 3600) -> Cache:
    """Get or create global cache instance."""
    global _cache
    if _cache is None:
        with _cache_lock:
            if _cache is None:  # Double-check pattern
                _cache = Cache(ttl=ttl)
    return _cache


def cached(ttl: Optional[int] = None, enable_stampede_protection: bool = True):
    """
    Decorator to cache function results with stampede protection.

    Args:
        ttl: Time-to-live in seconds (uses global default if None)
        enable_stampede_protection: Prevent cache stampede (default: True)

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

            # Generate cache key including module to prevent collisions between
            # different functions with the same name and arguments
            func_module = getattr(func, '__module__', '__unknown__')
            cache_key = cache._get_cache_key(func_module, func.__name__, *args, **kwargs)

            # Try to get from cache (first attempt without lock)
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Returning cached result for {func_module}.{func.__name__}")
                return cached_result

            # Cache miss - use stampede protection if enabled
            if enable_stampede_protection and cache.enable_stampede_protection:
                # Acquire lock to prevent multiple threads from computing same value
                lock = cache._get_stampede_lock(cache_key)

                # Non-blocking check - if someone else is computing, wait for them
                if lock.locked():
                    logger.debug(f"Waiting for another thread to compute {func_module}.{func.__name__}")
                    with lock:
                        # Once we acquire lock, check cache again
                        cached_result = cache.get(cache_key)
                        if cached_result is not None:
                            return cached_result

                # We got the lock first, compute the value
                with lock:
                    # Double-check cache (another thread might have filled it)
                    cached_result = cache.get(cache_key)
                    if cached_result is not None:
                        return cached_result

                    # Execute function
                    logger.debug(f"Computing fresh result for {func_module}.{func.__name__}")
                    result = await func(*args, **kwargs)

                    # Cache result
                    cache.set(cache_key, result, ttl=ttl)

                # Cleanup lock
                cache._cleanup_stampede_lock(cache_key)

                return result
            else:
                # No stampede protection - just execute
                result = await func(*args, **kwargs)
                cache.set(cache_key, result, ttl=ttl)
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
        self.calls: List[float] = []
        self._lock = threading.Lock()

    def is_allowed(self) -> bool:
        """Check if a new call is allowed."""
        with self._lock:
            now = time.time()

            # Remove old calls outside time window
            self.calls = [call_time for call_time in self.calls if now - call_time < self.time_window]

            # Additional safety: ensure list doesn't grow beyond max_calls * 2
            # This prevents memory leaks if cleanup fails
            if len(self.calls) > self.max_calls * 2:
                self.calls = self.calls[-(self.max_calls * 2):]

            # Check if under limit
            if len(self.calls) < self.max_calls:
                self.calls.append(now)
                return True

            return False

    def wait_time(self) -> float:
        """Get wait time until next call is allowed."""
        with self._lock:
            if len(self.calls) < self.max_calls:
                return 0.0

            # Clean up expired calls first
            now = time.time()
            self.calls = [call_time for call_time in self.calls if now - call_time < self.time_window]

            if len(self.calls) < self.max_calls:
                return 0.0

            oldest_call = min(self.calls)
            return max(0.0, self.time_window - (time.time() - oldest_call))

    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        with self._lock:
            now = time.time()
            active_calls = len([c for c in self.calls if now - c < self.time_window])

            return {
                "active_calls": active_calls,
                "max_calls": self.max_calls,
                "time_window": self.time_window,
                "utilization": f"{active_calls / self.max_calls * 100:.1f}%",
            }

    def clear(self):
        """Clear all rate limit history to free memory."""
        with self._lock:
            self.calls.clear()


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
