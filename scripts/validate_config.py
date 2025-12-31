#!/usr/bin/env python3
"""Configuration validation script for AIOps.

This script validates the configuration for production readiness
and provides recommendations for improvements.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aiops.core.config import get_config
from aiops.core.logger import get_logger

logger = get_logger(__name__)


def validate_config():
    """Validate configuration and print report."""
    print("=" * 60)
    print("AIOps Configuration Validation")
    print("=" * 60)
    print()

    try:
        config = get_config()
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        return False

    # Display environment
    print(f"Environment: {config.environment}")
    print(f"Debug Mode: {config.debug}")
    print()

    # Validate for production if needed
    if config.is_production():
        print("🔍 Running production validation checks...")
        print()

        errors = config.validate_production_config()

        if errors:
            print("❌ Production validation failed with the following errors:")
            print()
            for i, error in enumerate(errors, 1):
                print(f"  {i}. {error}")
            print()
            print("Please fix these issues before deploying to production.")
            return False
        else:
            print("✅ Production validation passed!")
            print()
    else:
        print("ℹ️  Development/staging environment detected.")
        print("   Production validation checks will not be enforced.")
        print()

    # Display configuration summary
    print("Configuration Summary:")
    print("-" * 60)

    # LLM Configuration
    print("\n📊 LLM Configuration:")
    print(f"  - OpenAI API Key: {'✅ Set' if config.openai_api_key else '❌ Not set'}")
    print(f"  - Anthropic API Key: {'✅ Set' if config.anthropic_api_key else '❌ Not set'}")
    print(f"  - Default Provider: {config.default_llm_provider}")
    print(f"  - Default Model: {config.default_model}")
    print(f"  - Max Retries: {config.llm_max_retries}")
    print(f"  - Timeout: {config.llm_timeout}s")

    # Database Configuration
    print("\n🗄️  Database Configuration:")
    print(f"  - Database Host: {config.database_host}:{config.database_port}")
    print(f"  - Database Name: {config.database_name}")
    print(f"  - SSL Mode: {config.database_ssl_mode}")
    print(f"  - Pool Size: {config.database_pool_size}")
    print(f"  - Max Overflow: {config.database_max_overflow}")
    print(f"  - Slow Query Threshold: {config.database_slow_query_threshold_ms}ms")

    # Redis Configuration
    print("\n🔴 Redis Configuration:")
    print(f"  - Enabled: {config.enable_redis}")
    print(f"  - Redis URL: {config.redis_url}")
    print(f"  - Max Connections: {config.redis_max_connections}")
    print(f"  - SSL: {config.redis_ssl}")

    # API Configuration
    print("\n🌐 API Configuration:")
    print(f"  - Host: {config.api_host}")
    print(f"  - Port: {config.api_port}")
    print(f"  - Workers: {config.api_workers}")
    print(f"  - Docs Enabled: {config.api_docs_enabled}")

    # Security Configuration
    print("\n🔒 Security Configuration:")
    print(f"  - Secret Key Length: {len(config.secret_key)} chars")
    print(f"  - JWT Expiration: {config.jwt_expiration_minutes} minutes")
    print(f"  - Session Timeout: {config.session_timeout_minutes} minutes")
    print(f"  - Max Upload Size: {config.max_upload_size_mb} MB")

    # CORS Configuration
    print("\n🌍 CORS Configuration:")
    cors_origins = config.get_cors_origins()
    if cors_origins == ["*"]:
        print("  - Origins: * (⚠️  WARNING: Allows all origins)")
    elif cors_origins:
        print(f"  - Origins: {', '.join(cors_origins)}")
    else:
        print("  - Origins: None (CORS disabled)")

    # Rate Limiting
    print("\n⏱️  Rate Limiting:")
    print(f"  - Enabled: {config.rate_limiting_enabled}")
    print(f"  - Default Limit: {config.rate_limit_default_requests} requests / {config.rate_limit_default_window}s")

    # Cache Configuration
    print("\n💾 Cache Configuration:")
    print(f"  - Enabled: {config.cache_enabled}")
    print(f"  - Default TTL: {config.cache_default_ttl}s")
    print(f"  - Cache Directory: {config.cache_dir}")

    # Monitoring & Observability
    print("\n📈 Monitoring & Observability:")
    print(f"  - Metrics Enabled: {config.enable_metrics}")
    print(f"  - Metrics Port: {config.metrics_port}")
    print(f"  - Sentry DSN: {'✅ Set' if config.sentry_dsn else '❌ Not set'}")
    print(f"  - OpenTelemetry: {config.otel_traces_enabled}")

    # Feature Flags
    print("\n🚩 Feature Flags:")
    print(f"  - Code Review: {config.enable_code_review}")
    print(f"  - Test Generation: {config.enable_test_generation}")
    print(f"  - Log Analysis: {config.enable_log_analysis}")
    print(f"  - Anomaly Detection: {config.enable_anomaly_detection}")
    print(f"  - Auto Fix: {config.enable_auto_fix} {'⚠️  (Enabled - use with caution)' if config.enable_auto_fix else ''}")

    print()
    print("=" * 60)

    # Warnings and recommendations
    warnings = []

    if config.debug and config.environment == "production":
        warnings.append("DEBUG mode is enabled in production")

    if config.cors_origins == "*":
        warnings.append("CORS is set to allow all origins (*)")

    if not config.enable_redis and config.environment == "production":
        warnings.append("Redis is disabled - consider enabling for production caching")

    if config.database_ssl_mode == "disable" and config.environment == "production":
        warnings.append("Database SSL is disabled in production")

    if not config.sentry_dsn and config.environment == "production":
        warnings.append("Sentry DSN not configured - consider adding error tracking")

    if warnings:
        print("\n⚠️  Warnings:")
        for i, warning in enumerate(warnings, 1):
            print(f"  {i}. {warning}")
        print()

    # Recommendations
    recommendations = []

    if config.environment == "development":
        recommendations.append("Enable Redis (ENABLE_REDIS=true) for realistic caching behavior")

    if not config.otel_traces_enabled:
        recommendations.append("Consider enabling OpenTelemetry for distributed tracing")

    if config.database_pool_size < 10 and config.environment == "production":
        recommendations.append("Consider increasing DATABASE_POOL_SIZE for production workloads")

    if recommendations:
        print("💡 Recommendations:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")
        print()

    return True


if __name__ == "__main__":
    success = validate_config()
    sys.exit(0 if success else 1)
