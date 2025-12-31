"""System Status and Configuration Routes

Provides endpoints for:
- System configuration view (non-sensitive)
- Runtime statistics
- Feature flags status
- Environment information
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
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
    version: str = Field(..., description="API version")
    python_version: str = Field(..., description="Python runtime version")
    platform: str = Field(..., description="Operating system platform")
    environment: str = Field(..., description="Environment name (development, staging, production)")
    debug_mode: bool = Field(..., description="Whether debug mode is enabled")
    start_time: datetime = Field(..., description="Server start timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "version": "0.1.0",
                "python_version": "3.11.5",
                "platform": "Linux-5.15.0-x86_64",
                "environment": "production",
                "debug_mode": False,
                "start_time": "2024-01-15T09:00:00Z"
            }
        }


class FeatureFlags(BaseModel):
    """Feature flags status."""
    code_review: bool = Field(..., description="Code review feature enabled")
    test_generation: bool = Field(..., description="Test generation feature enabled")
    log_analysis: bool = Field(..., description="Log analysis feature enabled")
    anomaly_detection: bool = Field(..., description="Anomaly detection feature enabled")
    auto_fix: bool = Field(..., description="Automatic fix feature enabled")


class ConfigurationView(BaseModel):
    """Non-sensitive configuration view."""
    default_llm_provider: str = Field(..., description="Default LLM provider (openai, anthropic, etc.)")
    default_model: str = Field(..., description="Default LLM model name")
    log_level: str = Field(..., description="Logging level (DEBUG, INFO, WARNING, ERROR)")
    metrics_enabled: bool = Field(..., description="Whether metrics collection is enabled")
    cors_origins: List[str] = Field(..., description="Allowed CORS origins")
    feature_flags: FeatureFlags = Field(..., description="Feature flag status")

    class Config:
        json_schema_extra = {
            "example": {
                "default_llm_provider": "openai",
                "default_model": "gpt-4-turbo-preview",
                "log_level": "INFO",
                "metrics_enabled": True,
                "cors_origins": ["https://example.com"],
                "feature_flags": {
                    "code_review": True,
                    "test_generation": True,
                    "log_analysis": True,
                    "anomaly_detection": True,
                    "auto_fix": False
                }
            }
        }


# Track application start time
APP_START_TIME = datetime.now()


@router.get("/info")
async def system_info(
    current_user: Dict[str, Any] = Depends(require_readonly),
) -> SystemInfo:
    """Get basic system information."""
    try:
        return SystemInfo(
            version="0.1.0",
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            platform=platform.platform(),
            environment=os.getenv("ENVIRONMENT", "development"),
            debug_mode=os.getenv("DEBUG", "false").lower() == "true",
            start_time=APP_START_TIME,
        )
    except Exception as e:
        logger.error(f"Failed to get system info: {e}", exc_info=True)
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve system information: {str(e)}"
        )


@router.get("/config")
async def get_configuration(
    current_user: Dict[str, Any] = Depends(require_readonly),
) -> ConfigurationView:
    """Get non-sensitive configuration settings."""
    try:
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
    except Exception as e:
        logger.error(f"Failed to get configuration: {e}", exc_info=True)
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve configuration: {str(e)}"
        )


@router.get("/stats")
async def get_statistics(
    current_user: Dict[str, Any] = Depends(require_readonly),
) -> Dict[str, Any]:
    """Get runtime statistics."""
    try:
        import psutil

        process = psutil.Process()
        memory_info = process.memory_info()

        # Get agent stats
        try:
            from aiops.agents.registry import agent_registry
            agent_stats = agent_registry.get_stats()
        except Exception as e:
            logger.warning(f"Unable to get agent stats: {e}")
            agent_stats = {"error": "Unable to get agent stats"}

        # Get cache stats
        try:
            from aiops.core.cache import get_cache
            cache = get_cache()
            cache_stats = cache.get_stats()
        except Exception as e:
            logger.warning(f"Unable to get cache stats: {e}")
            cache_stats = {"error": "Unable to get cache stats"}

        # Get token usage
        try:
            from aiops.core.token_tracker import get_token_tracker
            tracker = get_token_tracker()
            token_stats = {
                "total_requests": tracker.get_stats().total_requests if hasattr(tracker.get_stats(), 'total_requests') else 0,
            }
        except Exception as e:
            logger.warning(f"Unable to get token stats: {e}")
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

    except Exception as e:
        logger.error(f"Failed to get statistics: {e}", exc_info=True)
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve statistics: {str(e)}"
        )


@router.get("/env")
async def get_environment(
    current_user: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, Any]:
    """Get environment variable status (admin only).

    Returns which required environment variables are set (not their values).
    """
    try:
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

    except Exception as e:
        logger.error(f"Failed to get environment info: {e}", exc_info=True)
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve environment information: {str(e)}"
        )


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
        logger.error(f"Failed to clear caches: {e}", exc_info=True)
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear caches: {str(e)}"
        )


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
