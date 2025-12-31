"""System Status and Configuration Routes

Provides endpoints for:
- System configuration view (non-sensitive)
- Runtime statistics
- Feature flags status
- Environment information
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
import os
import sys
import platform

from aiops.core.logger import get_logger
from aiops.core.config import get_config
from aiops.api.auth import require_readonly, require_admin

logger = get_logger(__name__)
router = APIRouter()


class SystemInfo(BaseModel):
    """System information response."""
    version: str
    python_version: str
    platform: str
    environment: str
    debug_mode: bool
    start_time: datetime


class FeatureFlags(BaseModel):
    """Feature flags status."""
    code_review: bool
    test_generation: bool
    log_analysis: bool
    anomaly_detection: bool
    auto_fix: bool


class ConfigurationView(BaseModel):
    """Non-sensitive configuration view."""
    default_llm_provider: str
    default_model: str
    log_level: str
    metrics_enabled: bool
    cors_origins: List[str]
    feature_flags: FeatureFlags


# Track application start time
APP_START_TIME = datetime.now()


@router.get("/info")
async def system_info(
    current_user: Dict[str, Any] = Depends(require_readonly),
) -> SystemInfo:
    """Get basic system information."""
    return SystemInfo(
        version="0.1.0",
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        platform=platform.platform(),
        environment=os.getenv("ENVIRONMENT", "development"),
        debug_mode=os.getenv("DEBUG", "false").lower() == "true",
        start_time=APP_START_TIME,
    )


@router.get("/config")
async def get_configuration(
    current_user: Dict[str, Any] = Depends(require_readonly),
) -> ConfigurationView:
    """Get non-sensitive configuration settings."""
    config = get_config()

    return ConfigurationView(
        default_llm_provider=config.default_llm_provider,
        default_model=config.default_model,
        log_level=config.log_level,
        metrics_enabled=config.enable_metrics,
        cors_origins=config.get_cors_origins(),
        feature_flags=FeatureFlags(
            code_review=config.enable_code_review,
            test_generation=config.enable_test_generation,
            log_analysis=config.enable_log_analysis,
            anomaly_detection=config.enable_anomaly_detection,
            auto_fix=config.enable_auto_fix,
        ),
    )


@router.get("/stats")
async def get_statistics(
    current_user: Dict[str, Any] = Depends(require_readonly),
) -> Dict[str, Any]:
    """Get runtime statistics."""
    import psutil

    process = psutil.Process()
    memory_info = process.memory_info()

    # Get agent stats
    try:
        from aiops.agents.registry import agent_registry
        agent_stats = agent_registry.get_stats()
    except Exception:
        agent_stats = {"error": "Unable to get agent stats"}

    # Get cache stats
    try:
        from aiops.core.cache import get_cache
        cache = get_cache()
        cache_stats = cache.get_stats()
    except Exception:
        cache_stats = {"error": "Unable to get cache stats"}

    # Get token usage
    try:
        from aiops.core.token_tracker import get_token_tracker
        tracker = get_token_tracker()
        token_stats = {
            "total_requests": tracker.get_stats().total_requests if hasattr(tracker.get_stats(), 'total_requests') else 0,
        }
    except Exception:
        token_stats = {"error": "Unable to get token stats"}

    uptime_seconds = (datetime.now() - APP_START_TIME).total_seconds()

    return {
        "uptime": {
            "seconds": uptime_seconds,
            "human": _format_uptime(uptime_seconds),
        },
        "process": {
            "pid": process.pid,
            "memory_mb": round(memory_info.rss / (1024 * 1024), 2),
            "cpu_percent": process.cpu_percent(),
            "threads": process.num_threads(),
        },
        "agents": agent_stats,
        "cache": cache_stats,
        "tokens": token_stats,
    }


@router.get("/env")
async def get_environment(
    current_user: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, Any]:
    """Get environment variable status (admin only).

    Returns which required environment variables are set (not their values).
    """
    required_vars = [
        "JWT_SECRET_KEY",
        "ADMIN_PASSWORD",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "DATABASE_URL",
        "REDIS_URL",
    ]

    optional_vars = [
        "ENVIRONMENT",
        "LOG_LEVEL",
        "ENABLE_METRICS",
        "SLACK_WEBHOOK_URL",
        "GITHUB_TOKEN",
        "SENTRY_DSN",
    ]

    return {
        "required": {
            var: os.getenv(var) is not None
            for var in required_vars
        },
        "optional": {
            var: os.getenv(var) is not None
            for var in optional_vars
        },
        "environment": os.getenv("ENVIRONMENT", "development"),
    }


@router.post("/cache/clear")
async def clear_cache(
    current_user: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, str]:
    """Clear all caches (admin only)."""
    try:
        from aiops.core.cache import get_cache
        cache = get_cache()
        cache.clear()

        from aiops.core.semantic_cache import get_semantic_cache
        semantic_cache = get_semantic_cache()
        semantic_cache.clear()

        from aiops.agents.registry import agent_registry
        agent_registry.clear_cache()

        logger.info(f"All caches cleared by {current_user.get('username')}")

        return {"status": "success", "message": "All caches cleared"}
    except Exception as e:
        logger.error(f"Failed to clear caches: {e}")
        return {"status": "error", "message": str(e)}


def _format_uptime(seconds: float) -> str:
    """Format uptime in human-readable format."""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")

    return " ".join(parts)
