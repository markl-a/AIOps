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
)
from aiops.core.exceptions import AIOpsException
from aiops.core.structured_logger import get_structured_logger
from aiops.observability.metrics import (
    http_requests_total,
    http_request_duration_seconds,
)


logger = get_structured_logger(__name__)


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
app = FastAPI(
    title="AIOps API",
    description="AI-powered DevOps automation platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


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


@app.get("/", tags=["Root"])
async def root() -> Dict[str, Any]:
    """Root endpoint."""
    return {
        "name": "AIOps API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
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
