"""Middleware for AIOps API."""

import time
from typing import Callable, Optional, Dict
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from aiops.core.logger import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with sliding window algorithm.

    Supports both global and per-user rate limits.
    """

    def __init__(
        self,
        app: ASGIApp,
        default_limit: int = 100,
        window_seconds: int = 60,
        enabled: bool = True,
    ):
        """
        Initialize rate limiter.

        Args:
            app: ASGI application
            default_limit: Default requests per window
            window_seconds: Time window in seconds
            enabled: Enable/disable rate limiting
        """
        super().__init__(app)
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self.enabled = enabled

        # Storage: {identifier: [(timestamp, count)]}
        self.requests: Dict[str, list] = defaultdict(list)

        # Clean up old entries periodically
        self._cleanup_task = None

    async def dispatch(self, request: Request, call_next: Callable):
        """Process request with rate limiting."""
        if not self.enabled:
            return await call_next(request)

        # Skip health checks and metrics
        if request.url.path in ["/health", "/metrics", "/", "/docs", "/openapi.json"]:
            return await call_next(request)

        # Get identifier (IP or API key or username)
        identifier = self._get_identifier(request)

        # Check rate limit
        if not self._check_rate_limit(identifier, request):
            logger.warning(f"Rate limit exceeded for {identifier}")
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": self.window_seconds,
                },
                headers={"Retry-After": str(self.window_seconds)},
            )

        # Record request
        self._record_request(identifier)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        limit_info = self._get_limit_info(identifier)
        response.headers["X-RateLimit-Limit"] = str(limit_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(limit_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(limit_info["reset"])

        return response

    def _get_identifier(self, request: Request) -> str:
        """Get unique identifier for rate limiting."""
        # Try to get from auth context
        if hasattr(request.state, "user"):
            user = request.state.user
            if isinstance(user, dict):
                return f"user:{user.get('username', 'unknown')}"

        # Try API key
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"apikey:{api_key[:16]}"

        # Fallback to IP
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    def _check_rate_limit(self, identifier: str, request: Request) -> bool:
        """Check if request is within rate limit."""
        # Get custom limit from user context if available
        limit = self.default_limit
        if hasattr(request.state, "user"):
            user = request.state.user
            if isinstance(user, dict) and "rate_limit" in user:
                limit = user["rate_limit"]

        # Clean old requests
        now = time.time()
        cutoff = now - self.window_seconds
        self.requests[identifier] = [
            (ts, count) for ts, count in self.requests[identifier] if ts > cutoff
        ]

        # Count requests in window
        total = sum(count for _, count in self.requests[identifier])

        return total < limit

    def _record_request(self, identifier: str):
        """Record a request."""
        now = time.time()
        self.requests[identifier].append((now, 1))

    def _get_limit_info(self, identifier: str) -> dict:
        """Get current limit information."""
        now = time.time()
        cutoff = now - self.window_seconds

        # Clean old requests
        self.requests[identifier] = [
            (ts, count) for ts, count in self.requests[identifier] if ts > cutoff
        ]

        total = sum(count for _, count in self.requests[identifier])

        # Calculate reset time
        oldest_ts = min([ts for ts, _ in self.requests[identifier]], default=now)
        reset_time = int(oldest_ts + self.window_seconds)

        return {
            "limit": self.default_limit,
            "remaining": max(0, self.default_limit - total),
            "reset": reset_time,
        }


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next: Callable):
        """Add security headers."""
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests with timing information."""

    async def dispatch(self, request: Request, call_next: Callable):
        """Log request and response."""
        start_time = time.time()

        # Get client info
        client_ip = request.client.host if request.client else "unknown"

        # Log request
        logger.info(
            f"Request started: {request.method} {request.url.path} from {client_ip}"
        )

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # Log response
            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"status={response.status_code} duration={duration:.3f}s"
            )

            # Add timing header
            response.headers["X-Process-Time"] = f"{duration:.3f}"

            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"error={str(e)} duration={duration:.3f}s"
            )
            raise


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Validate and sanitize requests."""

    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB
    ALLOWED_CONTENT_TYPES = {
        "application/json",
        "application/x-www-form-urlencoded",
        "multipart/form-data",
    }

    async def dispatch(self, request: Request, call_next: Callable):
        """Validate request."""
        # Skip validation for GET requests and health checks
        if request.method == "GET" or request.url.path in ["/health", "/metrics", "/"]:
            return await call_next(request)

        # Check content length
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > self.MAX_CONTENT_LENGTH:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": f"Request too large. Max size: {self.MAX_CONTENT_LENGTH} bytes"
                        },
                    )
            except ValueError:
                return JSONResponse(
                    status_code=400, content={"detail": "Invalid Content-Length header"}
                )

        # Check content type for POST/PUT/PATCH
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "").split(";")[0].strip()
            if content_type and content_type not in self.ALLOWED_CONTENT_TYPES:
                return JSONResponse(
                    status_code=415,
                    content={
                        "detail": f"Unsupported content type: {content_type}",
                        "allowed_types": list(self.ALLOWED_CONTENT_TYPES),
                    },
                )

        return await call_next(request)


class CORSMiddleware(BaseHTTPMiddleware):
    """Custom CORS middleware with configurable origins."""

    def __init__(
        self,
        app: ASGIApp,
        allow_origins: list = None,
        allow_methods: list = None,
        allow_headers: list = None,
        allow_credentials: bool = True,
    ):
        """
        Initialize CORS middleware.

        Args:
            app: ASGI application
            allow_origins: List of allowed origins (default: localhost only)
            allow_methods: List of allowed methods
            allow_headers: List of allowed headers
            allow_credentials: Allow credentials
        """
        super().__init__(app)
        self.allow_origins = allow_origins or [
            "http://localhost:3000",
            "http://localhost:8000",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000",
        ]
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allow_headers = allow_headers or ["*"]
        self.allow_credentials = allow_credentials

    async def dispatch(self, request: Request, call_next: Callable):
        """Handle CORS."""
        origin = request.headers.get("origin")

        # Handle preflight requests
        if request.method == "OPTIONS":
            response = JSONResponse(content={})
        else:
            response = await call_next(request)

        # Add CORS headers if origin is allowed
        if origin in self.allow_origins or "*" in self.allow_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = ", ".join(
                self.allow_methods
            )
            response.headers["Access-Control-Allow-Headers"] = ", ".join(
                self.allow_headers
            )
            if self.allow_credentials:
                response.headers["Access-Control-Allow-Credentials"] = "true"

        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Collect basic metrics for monitoring."""

    def __init__(self, app: ASGIApp):
        """Initialize metrics middleware."""
        super().__init__(app)
        self.request_count = defaultdict(int)
        self.request_duration = defaultdict(list)
        self.error_count = defaultdict(int)

    async def dispatch(self, request: Request, call_next: Callable):
        """Collect metrics."""
        start_time = time.time()
        path = request.url.path
        method = request.method

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # Record metrics
            key = f"{method}:{path}"
            self.request_count[key] += 1
            self.request_duration[key].append(duration)

            if response.status_code >= 400:
                self.error_count[key] += 1

            return response

        except Exception as e:
            duration = time.time() - start_time
            key = f"{method}:{path}"
            self.error_count[key] += 1
            raise

    def get_metrics(self) -> dict:
        """Get collected metrics."""
        return {
            "request_count": dict(self.request_count),
            "request_duration": {
                k: {
                    "count": len(v),
                    "mean": sum(v) / len(v) if v else 0,
                    "min": min(v) if v else 0,
                    "max": max(v) if v else 0,
                }
                for k, v in self.request_duration.items()
            },
            "error_count": dict(self.error_count),
        }
