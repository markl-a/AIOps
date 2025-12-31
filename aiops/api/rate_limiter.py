"""Advanced rate limiting for AIOps API with per-endpoint and per-user limits."""

import time
import asyncio
from typing import Dict, Optional, Any, List, Callable
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import threading
import json

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from aiops.core.logger import get_logger

logger = get_logger(__name__)


class RateLimitAlgorithm(Enum):
    """Rate limiting algorithms."""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


@dataclass
class RateLimitRule:
    """Configuration for a rate limit rule."""
    requests: int              # Maximum requests allowed
    window: int                # Time window in seconds
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.SLIDING_WINDOW
    burst: Optional[int] = None  # Maximum burst size (for token bucket)

    def __post_init__(self):
        if self.burst is None:
            self.burst = self.requests


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    # Global defaults
    default_limit: int = 100
    default_window: int = 60

    # Per-endpoint limits
    endpoint_limits: Dict[str, RateLimitRule] = field(default_factory=dict)

    # Per-user tier limits
    user_tier_limits: Dict[str, RateLimitRule] = field(default_factory=dict)

    # Paths to exclude from rate limiting
    excluded_paths: List[str] = field(default_factory=lambda: [
        "/health",
        "/metrics",
        "/docs",
        "/openapi.json",
        "/redoc",
    ])

    # Redis configuration
    use_redis: bool = False
    redis_url: str = "redis://localhost:6379/0"


# Default endpoint-specific limits
DEFAULT_ENDPOINT_LIMITS = {
    "/api/v1/agents/execute": RateLimitRule(requests=20, window=60),
    "/api/v1/agents/batch": RateLimitRule(requests=5, window=60),
    "/api/v1/llm/complete": RateLimitRule(requests=30, window=60),
    "/api/v1/auth/login": RateLimitRule(requests=5, window=300),
    "/api/v1/auth/register": RateLimitRule(requests=3, window=3600),
    "/api/v1/webhooks": RateLimitRule(requests=100, window=60),
}

# Default user tier limits
DEFAULT_USER_TIER_LIMITS = {
    "free": RateLimitRule(requests=50, window=60),
    "basic": RateLimitRule(requests=200, window=60),
    "pro": RateLimitRule(requests=500, window=60),
    "enterprise": RateLimitRule(requests=2000, window=60),
    "unlimited": RateLimitRule(requests=100000, window=60),
}


class SlidingWindowCounter:
    """Sliding window rate limiter using sub-windows."""

    def __init__(self, limit: int, window: int, sub_windows: int = 10):
        self.limit = limit
        self.window = window
        self.sub_windows = sub_windows
        self.sub_window_size = window / sub_windows

        # Storage: {identifier: {sub_window_id: count}}
        self._counters: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
        self._lock = threading.Lock()

    def _get_current_window(self) -> int:
        """Get current sub-window ID."""
        return int(time.time() / self.sub_window_size)

    def _clean_old_windows(self, identifier: str, current_window: int):
        """Remove expired sub-windows."""
        expired = current_window - self.sub_windows
        self._counters[identifier] = {
            k: v for k, v in self._counters[identifier].items()
            if k > expired
        }

    def is_allowed(self, identifier: str) -> tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed.

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        with self._lock:
            current_window = self._get_current_window()
            self._clean_old_windows(identifier, current_window)

            # Calculate current rate
            total = sum(self._counters[identifier].values())

            # Calculate weight for partial window
            current_sub_window_weight = (time.time() % self.sub_window_size) / self.sub_window_size

            # Weighted count
            weighted_total = total
            if current_window in self._counters[identifier]:
                # Reduce weight of current window based on elapsed time
                current_count = self._counters[identifier][current_window]
                weighted_total = total - current_count + (current_count * current_sub_window_weight)

            is_allowed = weighted_total < self.limit

            if is_allowed:
                # Increment counter for current window (defaultdict handles missing keys)
                if current_window not in self._counters[identifier]:
                    self._counters[identifier][current_window] = 0
                self._counters[identifier][current_window] += 1

            # Calculate reset time
            oldest_window = min(self._counters[identifier].keys(), default=current_window)
            reset_time = int((oldest_window + self.sub_windows + 1) * self.sub_window_size)

            return is_allowed, {
                "limit": self.limit,
                "remaining": max(0, int(self.limit - weighted_total - 1)),
                "reset": reset_time,
                "window": self.window,
            }


class TokenBucket:
    """Token bucket rate limiter for smooth rate limiting with bursts."""

    def __init__(self, rate: float, capacity: int):
        """
        Initialize token bucket.

        Args:
            rate: Tokens added per second
            capacity: Maximum bucket capacity
        """
        self.rate = rate
        self.capacity = capacity

        # State per identifier
        self._buckets: Dict[str, Dict[str, float]] = {}
        self._lock = threading.Lock()

    def _get_bucket(self, identifier: str) -> Dict[str, float]:
        """Get or create bucket for identifier."""
        if identifier not in self._buckets:
            self._buckets[identifier] = {
                "tokens": float(self.capacity),
                "last_update": time.time(),
            }
        return self._buckets[identifier]

    def _refill(self, bucket: Dict[str, float]):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - bucket["last_update"]
        bucket["tokens"] = min(
            self.capacity,
            bucket["tokens"] + elapsed * self.rate
        )
        bucket["last_update"] = now

    def is_allowed(self, identifier: str, tokens: int = 1) -> tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed.

        Args:
            identifier: Unique identifier for rate limiting
            tokens: Number of tokens to consume

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        with self._lock:
            bucket = self._get_bucket(identifier)
            self._refill(bucket)

            is_allowed = bucket["tokens"] >= tokens

            if is_allowed:
                bucket["tokens"] -= tokens

            return is_allowed, {
                "limit": self.capacity,
                "remaining": int(bucket["tokens"]),
                "reset": int(time.time() + (self.capacity - bucket["tokens"]) / self.rate),
            }


class RedisRateLimiter:
    """Redis-based sliding window rate limiter with in-memory fallback."""

    def __init__(self, limit: int, window: int, redis_client=None, key_prefix: str = "rl"):
        """
        Initialize Redis rate limiter.

        Args:
            limit: Maximum requests allowed
            window: Time window in seconds
            redis_client: Redis client (optional)
            key_prefix: Prefix for Redis keys
        """
        self.limit = limit
        self.window = window
        self._redis = redis_client
        self.key_prefix = key_prefix

        # Fallback to in-memory when Redis unavailable
        self._fallback = SlidingWindowCounter(limit=limit, window=window)
        self._redis_available = redis_client is not None

    def _get_redis_key(self, identifier: str) -> str:
        """Get Redis key for identifier."""
        return f"{self.key_prefix}:{identifier}"

    def is_allowed(self, identifier: str) -> tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed using Redis or fallback.

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        # Try Redis first if available
        if self._redis_available and self._redis:
            try:
                return self._check_redis(identifier)
            except Exception as e:
                logger.warning(f"Redis rate limit check failed, using fallback: {e}")
                self._redis_available = False

        # Fall back to in-memory
        return self._fallback.is_allowed(identifier)

    def _check_redis(self, identifier: str) -> tuple[bool, Dict[str, Any]]:
        """Check rate limit using Redis sorted set (sliding window)."""
        now = time.time()
        key = self._get_redis_key(identifier)
        window_start = now - self.window

        # Use Redis pipeline for atomic operations
        pipe = self._redis.pipeline()

        # Remove old entries outside the window
        pipe.zremrangebyscore(key, 0, window_start)

        # Count current requests in window
        pipe.zcard(key)

        # Execute pipeline
        results = pipe.execute()
        current_count = results[1]

        # Check if allowed
        is_allowed = current_count < self.limit

        if is_allowed:
            # Add current request with timestamp as score
            self._redis.zadd(key, {f"{now}:{id(identifier)}": now})
            # Set expiration to window + buffer
            self._redis.expire(key, self.window + 10)

        # Calculate reset time (when oldest request expires)
        try:
            oldest = self._redis.zrange(key, 0, 0, withscores=True)
            if oldest:
                reset_time = int(oldest[0][1] + self.window)
            else:
                reset_time = int(now + self.window)
        except Exception:
            reset_time = int(now + self.window)

        return is_allowed, {
            "limit": self.limit,
            "remaining": max(0, self.limit - current_count - (1 if is_allowed else 0)),
            "reset": reset_time,
            "window": self.window,
        }


class RateLimiter:
    """
    Advanced rate limiter with multiple algorithms and strategies.

    Supports:
    - Per-endpoint rate limits
    - Per-user rate limits with tiers
    - Multiple algorithms (sliding window, token bucket)
    - Redis backend for distributed rate limiting
    - Automatic fallback to in-memory when Redis unavailable
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        """Initialize rate limiter."""
        self.config = config or RateLimitConfig()

        # Redis client (if enabled)
        self._redis = None
        self._redis_available = False
        if self.config.use_redis:
            self._init_redis()

        # Initialize endpoint limiters
        self._endpoint_limiters: Dict[str, Any] = {}
        for path, rule in {**DEFAULT_ENDPOINT_LIMITS, **self.config.endpoint_limits}.items():
            if self._redis_available:
                self._endpoint_limiters[path] = RedisRateLimiter(
                    limit=rule.requests,
                    window=rule.window,
                    redis_client=self._redis,
                    key_prefix=f"rl:endpoint:{path}",
                )
            else:
                self._endpoint_limiters[path] = SlidingWindowCounter(
                    limit=rule.requests,
                    window=rule.window,
                )

        # Initialize tier limiters
        self._tier_limiters: Dict[str, Any] = {}
        for tier, rule in {**DEFAULT_USER_TIER_LIMITS, **self.config.user_tier_limits}.items():
            if self._redis_available:
                self._tier_limiters[tier] = RedisRateLimiter(
                    limit=rule.requests,
                    window=rule.window,
                    redis_client=self._redis,
                    key_prefix=f"rl:tier:{tier}",
                )
            else:
                self._tier_limiters[tier] = SlidingWindowCounter(
                    limit=rule.requests,
                    window=rule.window,
                )

        # Default limiter
        if self._redis_available:
            self._default_limiter = RedisRateLimiter(
                limit=self.config.default_limit,
                window=self.config.default_window,
                redis_client=self._redis,
                key_prefix="rl:default",
            )
        else:
            self._default_limiter = SlidingWindowCounter(
                limit=self.config.default_limit,
                window=self.config.default_window,
            )

        logger.info(
            "Rate limiter initialized",
            redis_enabled=self._redis_available,
            backend="redis" if self._redis_available else "in-memory",
        )

    def _init_redis(self):
        """Initialize Redis connection."""
        try:
            import redis
            self._redis = redis.from_url(
                self.config.redis_url,
                socket_timeout=2,
                socket_connect_timeout=2,
                decode_responses=True,
            )
            self._redis.ping()
            self._redis_available = True
            logger.info("Redis rate limiter backend connected", url=self.config.redis_url)
        except Exception as e:
            logger.warning(f"Redis connection failed, using in-memory fallback: {e}")
            self._redis = None
            self._redis_available = False

    def _get_identifier(self, request: Request) -> str:
        """Extract identifier from request."""
        # Try user from state
        if hasattr(request.state, "user"):
            user = request.state.user
            if isinstance(user, dict):
                return f"user:{user.get('id', user.get('username', 'unknown'))}"

        # Try API key
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"apikey:{api_key[:16]}"

        # Fallback to IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        return f"ip:{client_ip}"

    def _get_user_tier(self, request: Request) -> str:
        """Get user tier from request."""
        if hasattr(request.state, "user"):
            user = request.state.user
            if isinstance(user, dict):
                return user.get("tier", "free")
        return "free"

    def check_rate_limit(
        self,
        request: Request,
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Check if request is within rate limits.

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        path = request.url.path

        # Check if path is excluded
        if path in self.config.excluded_paths:
            return True, {"limit": -1, "remaining": -1, "reset": -1}

        identifier = self._get_identifier(request)

        # Check endpoint-specific limit
        if path in self._endpoint_limiters:
            endpoint_allowed, endpoint_info = self._endpoint_limiters[path].is_allowed(
                f"{identifier}:{path}"
            )
            if not endpoint_allowed:
                return False, endpoint_info

        # Check user tier limit
        tier = self._get_user_tier(request)
        if tier in self._tier_limiters:
            tier_allowed, tier_info = self._tier_limiters[tier].is_allowed(identifier)
            if not tier_allowed:
                return False, tier_info
            return True, tier_info

        # Fall back to default limit
        return self._default_limiter.is_allowed(identifier)


class AdvancedRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Advanced rate limiting middleware.

    Features:
    - Per-endpoint rate limits
    - Per-user tier rate limits
    - Sliding window algorithm
    - Rate limit headers in response
    - Configurable exclusions
    """

    def __init__(
        self,
        app: ASGIApp,
        config: Optional[RateLimitConfig] = None,
        enabled: bool = True,
    ):
        """
        Initialize middleware.

        Args:
            app: ASGI application
            config: Rate limit configuration
            enabled: Enable/disable rate limiting
        """
        super().__init__(app)
        self.enabled = enabled
        self.limiter = RateLimiter(config)

    async def dispatch(self, request: Request, call_next: Callable):
        """Process request with rate limiting."""
        if not self.enabled:
            return await call_next(request)

        # Check rate limit
        is_allowed, limit_info = self.limiter.check_rate_limit(request)

        if not is_allowed:
            logger.warning(
                f"Rate limit exceeded: {request.method} {request.url.path} "
                f"from {self.limiter._get_identifier(request)}"
            )

            retry_after = max(1, limit_info.get("reset", 60) - int(time.time()))

            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": retry_after,
                    "limit": limit_info.get("limit"),
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit_info.get("limit", 0)),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(limit_info.get("reset", 0)),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        if limit_info.get("limit", -1) > 0:
            response.headers["X-RateLimit-Limit"] = str(limit_info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(limit_info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(limit_info["reset"])

        return response


def create_rate_limit_config(
    default_limit: int = 100,
    default_window: int = 60,
    endpoint_limits: Optional[Dict[str, tuple]] = None,
    user_tier_limits: Optional[Dict[str, tuple]] = None,
) -> RateLimitConfig:
    """
    Helper to create rate limit configuration.

    Args:
        default_limit: Default requests per window
        default_window: Default window in seconds
        endpoint_limits: Dict of {path: (requests, window)}
        user_tier_limits: Dict of {tier: (requests, window)}

    Returns:
        RateLimitConfig instance
    """
    config = RateLimitConfig(
        default_limit=default_limit,
        default_window=default_window,
    )

    if endpoint_limits:
        for path, (requests, window) in endpoint_limits.items():
            config.endpoint_limits[path] = RateLimitRule(requests=requests, window=window)

    if user_tier_limits:
        for tier, (requests, window) in user_tier_limits.items():
            config.user_tier_limits[tier] = RateLimitRule(requests=requests, window=window)

    return config
