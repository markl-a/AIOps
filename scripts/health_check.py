#!/usr/bin/env python3
"""
Quick Health Check Script

Performs a quick health check of the AIOps system.
Useful for monitoring and CI/CD pipelines.
"""

import sys
import os
import asyncio
import json
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def check_api_health() -> Dict[str, Any]:
    """Check API health endpoint"""
    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "healthy",
                        "api_running": True,
                        "data": data,
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "api_running": False,
                        "error": f"HTTP {response.status}",
                    }

    except Exception as e:
        return {
            "status": "unhealthy",
            "api_running": False,
            "error": str(e),
        }


async def check_database() -> Dict[str, Any]:
    """Check database connectivity"""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        return {
            "status": "skipped",
            "message": "DATABASE_URL not configured",
        }

    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.pool import NullPool

        engine = create_engine(database_url, poolclass=NullPool)

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        engine.dispose()

        return {
            "status": "healthy",
            "connected": True,
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "connected": False,
            "error": str(e),
        }


async def check_redis() -> Dict[str, Any]:
    """Check Redis connectivity"""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    try:
        import redis.asyncio as aioredis

        redis_client = await aioredis.from_url(redis_url)
        await redis_client.ping()
        await redis_client.close()

        return {
            "status": "healthy",
            "connected": True,
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "connected": False,
            "error": str(e),
        }


def check_llm_providers() -> Dict[str, Any]:
    """Check LLM provider configuration"""
    providers = {
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        "google": bool(os.getenv("GOOGLE_API_KEY")),
    }

    configured_count = sum(providers.values())

    return {
        "status": "healthy" if configured_count > 0 else "warning",
        "providers": providers,
        "configured_count": configured_count,
    }


async def main():
    """Run health checks"""
    print("🏥 AIOps Health Check")
    print("=" * 50)

    # Run checks
    results = {
        "timestamp": asyncio.get_event_loop().time(),
        "checks": {
            "api": await check_api_health(),
            "database": await check_database(),
            "redis": await check_redis(),
            "llm_providers": check_llm_providers(),
        }
    }

    # Determine overall health
    all_healthy = True

    for check_name, check_result in results["checks"].items():
        status = check_result.get("status", "unknown")
        symbol = "✓" if status == "healthy" else ("⚠" if status == "warning" else ("⊘" if status == "skipped" else "✗"))

        print(f"\n{symbol} {check_name.upper()}: {status}")

        if status == "unhealthy":
            all_healthy = False
            if "error" in check_result:
                print(f"  Error: {check_result['error']}")

        if status == "warning":
            if "message" in check_result:
                print(f"  {check_result['message']}")

    # Summary
    print("\n" + "=" * 50)

    if all_healthy:
        print("✓ Overall Status: HEALTHY")
        print("\nAll critical components are operational.")
        return 0
    else:
        print("✗ Overall Status: UNHEALTHY")
        print("\nSome components have issues. Check errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
