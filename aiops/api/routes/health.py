"""Health Check Routes"""

from fastapi import APIRouter, status
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime
import psutil
import os

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    timestamp: datetime
    version: str
    uptime_seconds: Optional[float] = None


class DetailedHealthResponse(BaseModel):
    """Detailed health check response."""

    status: str
    timestamp: datetime
    version: str
    services: Dict[str, Any]
    system: Dict[str, Any]


# Track start time
START_TIME = datetime.now()


@router.get("/", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint."""
    uptime = (datetime.now() - START_TIME).total_seconds()

    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="1.0.0",
        uptime_seconds=uptime,
    )


@router.get("/liveness")
async def liveness():
    """Kubernetes liveness probe."""
    return {"status": "alive"}


@router.get("/readiness")
async def readiness():
    """Kubernetes readiness probe."""
    # Check if service is ready to handle requests
    # Add checks for database, cache, etc.

    return {"status": "ready"}


@router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health():
    """Detailed health check with system information."""
    uptime = (datetime.now() - START_TIME).total_seconds()

    # System metrics
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    services = {
        "database": {"status": "unknown"},  # Check actual DB connection
        "cache": {"status": "unknown"},  # Check Redis connection
        "llm_providers": {"status": "unknown"},  # Check LLM providers
    }

    system = {
        "cpu_percent": cpu_percent,
        "memory": {
            "total_gb": round(memory.total / (1024 ** 3), 2),
            "available_gb": round(memory.available / (1024 ** 3), 2),
            "percent": memory.percent,
        },
        "disk": {
            "total_gb": round(disk.total / (1024 ** 3), 2),
            "free_gb": round(disk.free / (1024 ** 3), 2),
            "percent": disk.percent,
        },
        "uptime_seconds": uptime,
    }

    return DetailedHealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="1.0.0",
        services=services,
        system=system,
    )
