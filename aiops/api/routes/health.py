"""Health Check Routes

Provides comprehensive health check endpoints for monitoring:
- Basic health check for simple status
- Kubernetes liveness/readiness probes
- Detailed health with service and system status
"""

from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import psutil
import os
import asyncio

from aiops.core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


class ServiceStatus(str, Enum):
    """Service health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ServiceHealth(BaseModel):
    """Individual service health."""
    status: ServiceStatus
    latency_ms: Optional[float] = None
    message: Optional[str] = None
    last_check: datetime = Field(default_factory=datetime.now)


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


async def check_database_health() -> ServiceHealth:
    """Check database connection health."""
    import time
    start = time.time()
    try:
        from aiops.database.base import get_db_manager
        db = get_db_manager()
        # Simple query to check connection
        with db.get_session() as session:
            session.execute("SELECT 1")
        latency = (time.time() - start) * 1000
        return ServiceHealth(
            status=ServiceStatus.HEALTHY,
            latency_ms=round(latency, 2),
            message="Database connection successful"
        )
    except Exception as e:
        latency = (time.time() - start) * 1000
        logger.warning(f"Database health check failed: {e}")
        return ServiceHealth(
            status=ServiceStatus.UNHEALTHY,
            latency_ms=round(latency, 2),
            message=f"Database error: {str(e)[:100]}"
        )


async def check_cache_health() -> ServiceHealth:
    """Check Redis cache health."""
    import time
    start = time.time()
    try:
        from aiops.cache.redis_cache import RedisCache
        cache = RedisCache()
        await cache.connect()
        # Ping Redis
        if cache.client:
            await cache.client.ping()
            latency = (time.time() - start) * 1000
            return ServiceHealth(
                status=ServiceStatus.HEALTHY,
                latency_ms=round(latency, 2),
                message="Redis connection successful"
            )
        else:
            return ServiceHealth(
                status=ServiceStatus.UNKNOWN,
                message="Redis client not initialized"
            )
    except Exception as e:
        latency = (time.time() - start) * 1000
        logger.warning(f"Cache health check failed: {e}")
        return ServiceHealth(
            status=ServiceStatus.DEGRADED,
            latency_ms=round(latency, 2),
            message=f"Cache unavailable: {str(e)[:100]}"
        )


async def check_llm_health() -> ServiceHealth:
    """Check LLM provider health."""
    import time
    start = time.time()
    try:
        from aiops.core.llm_factory import LLMFactory
        # Just check if we can create an LLM instance
        llm = LLMFactory.create()
        latency = (time.time() - start) * 1000
        return ServiceHealth(
            status=ServiceStatus.HEALTHY,
            latency_ms=round(latency, 2),
            message="LLM provider available"
        )
    except Exception as e:
        latency = (time.time() - start) * 1000
        logger.warning(f"LLM health check failed: {e}")
        return ServiceHealth(
            status=ServiceStatus.DEGRADED,
            latency_ms=round(latency, 2),
            message=f"LLM unavailable: {str(e)[:100]}"
        )


def get_overall_status(services: Dict[str, ServiceHealth]) -> ServiceStatus:
    """Determine overall health status from service statuses."""
    statuses = [s.status for s in services.values()]

    if all(s == ServiceStatus.HEALTHY for s in statuses):
        return ServiceStatus.HEALTHY
    elif any(s == ServiceStatus.UNHEALTHY for s in statuses):
        return ServiceStatus.UNHEALTHY
    elif any(s == ServiceStatus.DEGRADED for s in statuses):
        return ServiceStatus.DEGRADED
    else:
        return ServiceStatus.UNKNOWN


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

    # Check all services concurrently
    db_health, cache_health, llm_health = await asyncio.gather(
        check_database_health(),
        check_cache_health(),
        check_llm_health(),
        return_exceptions=True
    )

    # Handle exceptions in health checks
    if isinstance(db_health, Exception):
        db_health = ServiceHealth(status=ServiceStatus.UNHEALTHY, message=str(db_health))
    if isinstance(cache_health, Exception):
        cache_health = ServiceHealth(status=ServiceStatus.DEGRADED, message=str(cache_health))
    if isinstance(llm_health, Exception):
        llm_health = ServiceHealth(status=ServiceStatus.DEGRADED, message=str(llm_health))

    services_health = {
        "database": db_health,
        "cache": cache_health,
        "llm_providers": llm_health,
    }

    # System metrics
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    services = {
        name: {
            "status": health.status.value,
            "latency_ms": health.latency_ms,
            "message": health.message,
        }
        for name, health in services_health.items()
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
        "python_version": os.popen('python --version').read().strip(),
        "environment": os.getenv("ENVIRONMENT", "development"),
    }

    # Determine overall status
    overall_status = get_overall_status(services_health)

    return DetailedHealthResponse(
        status=overall_status.value,
        timestamp=datetime.now(),
        version="1.0.0",
        services=services,
        system=system,
    )


@router.get("/agents")
async def agents_health():
    """Check available agents status."""
    try:
        from aiops.agents.registry import agent_registry

        stats = agent_registry.get_stats()
        agents = agent_registry.list_agents()

        return {
            "status": "healthy",
            "total_registered": stats["registered"],
            "loaded": stats["loaded"],
            "cached_instances": stats["cached_instances"],
            "categories": stats["categories"],
            "agents": [
                {
                    "name": a.name,
                    "category": a.category,
                    "description": a.description,
                    "is_loaded": a.is_loaded,
                }
                for a in agents
            ],
        }
    except Exception as e:
        logger.error(f"Agents health check failed: {e}")
        return {
            "status": "error",
            "message": str(e),
        }
