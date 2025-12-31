"""FastAPI Application Entry Point

Main FastAPI application with all routes and middleware.
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import time
from typing import Dict, Any

from aiops.api.routes import (
    agents,
    health,
    llm,
    notifications,
    analytics,
    webhooks,
    system,
)
from aiops.api.rate_limiter import (
    AdvancedRateLimitMiddleware,
    RateLimitConfig,
    RateLimitRule,
)
from aiops.core.exceptions import AIOpsException
from aiops.core.structured_logger import get_structured_logger
from aiops.core.config import get_config
from aiops.observability.metrics import (
    http_requests_total,
    http_request_duration_seconds,
)
import os


logger = get_structured_logger(__name__)


def _is_production() -> bool:
    """Check if running in production environment."""
    env = os.environ.get("ENVIRONMENT", "development").lower()
    return env in ("production", "prod")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting AIOps API server")

    # Initialize services here
    # e.g., database connections, cache, etc.

    yield

    # Shutdown
    logger.info("Shutting down AIOps API server")

    # Cleanup here
    # e.g., close database connections, cleanup resources


# Create FastAPI app
# Disable API documentation in production for security
_in_production = _is_production()
if _in_production:
    logger.info("Running in production mode - API documentation disabled")

# Define OpenAPI tags with descriptions
tags_metadata = [
    {
        "name": "Root",
        "description": "Root endpoint providing API information and status",
    },
    {
        "name": "Health",
        "description": "Health check endpoints for monitoring service availability and dependencies. "
                      "Includes liveness/readiness probes for Kubernetes deployments.",
    },
    {
        "name": "Agents",
        "description": "Agent execution and management endpoints. Execute AI agents for various DevOps tasks "
                      "including code review, security scanning, test generation, and more. "
                      "Supports both synchronous and asynchronous execution with configurable timeouts and retries.",
    },
    {
        "name": "LLM",
        "description": "LLM (Large Language Model) provider management. Generate text using various LLM providers "
                      "with automatic failover, health monitoring, and cost tracking.",
    },
    {
        "name": "Notifications",
        "description": "Multi-channel notification system. Send notifications to Slack, Teams, email, and other channels. "
                      "Track notification history and test channel configurations.",
    },
    {
        "name": "Analytics",
        "description": "Analytics and metrics endpoints. Retrieve system-wide metrics, agent performance data, "
                      "cost breakdowns, usage trends, and error analytics.",
    },
    {
        "name": "Webhooks",
        "description": "Webhook endpoints for receiving events from external systems (GitHub, GitLab, Jira, PagerDuty). "
                      "Automatically triggers workflows based on incoming events.",
    },
    {
        "name": "System",
        "description": "System configuration and status endpoints. View system information, runtime statistics, "
                      "feature flags, and manage caches. Requires authentication.",
    },
]

app = FastAPI(
    title="AIOps API",
    description="""
# AIOps - AI-Powered DevOps Automation Platform

The AIOps API provides comprehensive DevOps automation capabilities powered by AI agents and LLMs.

## Key Features

* **AI Agent Execution**: Execute specialized AI agents for code review, security scanning, test generation, and more
* **Multi-LLM Support**: Automatic failover between OpenAI, Anthropic, Google, and other LLM providers
* **Workflow Orchestration**: Chain multiple agents together in sequential, parallel, or waterfall execution modes
* **Multi-Channel Notifications**: Send alerts to Slack, Teams, email, and other channels
* **Webhook Integration**: Receive and process webhooks from GitHub, GitLab, Jira, and PagerDuty
* **Analytics & Metrics**: Comprehensive tracking of costs, performance, and usage patterns
* **Health Monitoring**: Detailed health checks for all system components and dependencies

## Authentication

Most endpoints require authentication using JWT tokens or API keys. See the Security section for details.

## Rate Limiting

API endpoints are rate-limited to ensure fair usage. Rate limit information is included in response headers.

## Error Handling

All errors follow a standardized format with error codes, messages, and optional details for debugging.
    """,
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None if _in_production else "/docs",
    redoc_url=None if _in_production else "/redoc",
    openapi_url=None if _in_production else "/openapi.json",
    openapi_tags=tags_metadata,
    contact={
        "name": "AIOps Team",
        "email": "support@aiops.example.com",
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
)


# Middleware
config = get_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.get_cors_origins(),
    allow_credentials=config.cors_allow_credentials,
    allow_methods=config.get_cors_methods(),
    allow_headers=config.get_cors_headers(),
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Rate limiting middleware with Redis support
rate_limit_config = RateLimitConfig(
    default_limit=100,
    default_window=60,
    use_redis=os.getenv("REDIS_URL") is not None,
    redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    excluded_paths=[
        "/health",
        "/health/liveness",
        "/health/readiness",
        "/metrics",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/",
    ],
)

# Add custom endpoint limits for high-cost operations
rate_limit_config.endpoint_limits.update({
    "/api/v1/agents/execute": RateLimitRule(requests=20, window=60),
    "/api/v1/agents/workflows/execute": RateLimitRule(requests=10, window=60),
    "/api/v1/llm/generate": RateLimitRule(requests=30, window=60),
})

app.add_middleware(
    AdvancedRateLimitMiddleware,
    config=rate_limit_config,
    enabled=True,
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header and metrics."""
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    # Record metrics
    http_requests_total.labels(
        method=request.method,
        endpoint=request.url.path,
        status_code=response.status_code,
    ).inc()

    http_request_duration_seconds.labels(
        method=request.method,
        endpoint=request.url.path,
    ).observe(process_time)

    return response


# Exception handlers
@app.exception_handler(AIOpsException)
async def aiops_exception_handler(request: Request, exc: AIOpsException):
    """Handle AIOps custom exceptions."""
    logger.error(
        f"AIOps exception: {exc.message}",
        error_code=exc.error_code,
        details=exc.details,
        path=request.url.path,
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=exc.to_dict(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    logger.warning(
        "Request validation error",
        errors=exc.errors(),
        path=request.url.path,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "ValidationError",
            "message": "Request validation failed",
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(
        f"Unexpected error: {str(exc)}",
        exception_type=type(exc).__name__,
        path=request.url.path,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
        },
    )


# Include routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents"])
app.include_router(llm.router, prefix="/api/v1/llm", tags=["LLM"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["Notifications"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(webhooks.router, prefix="/api/v1", tags=["Webhooks"])
app.include_router(system.router, prefix="/api/v1/system", tags=["System"])


@app.get("/", tags=["Root"])
async def root() -> Dict[str, Any]:
    """Root endpoint."""
    return {
        "name": "AIOps API",
        "version": "0.1.0",
        "status": "running",
        "environment": "production" if _in_production else "development",
        "docs": None if _in_production else "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "aiops.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
