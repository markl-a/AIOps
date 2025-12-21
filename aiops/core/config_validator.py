"""Configuration validator to ensure all required settings are present."""
import os
import logging
from typing import List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration validation fails."""
    pass


class ConfigValidator:
    """Validates application configuration at startup."""

    REQUIRED_ENV_VARS = [
        "DATABASE_URL",
    ]

    REQUIRED_IN_PRODUCTION = [
        "JWT_SECRET_KEY",
        "CORS_ORIGINS",
    ]

    @classmethod
    def validate(cls) -> bool:
        """Validate all configuration.

        Returns:
            True if validation passes

        Raises:
            ConfigurationError: If validation fails
        """
        errors: List[str] = []

        # Check required environment variables
        for var in cls.REQUIRED_ENV_VARS:
            if not os.getenv(var):
                errors.append(f"Missing required environment variable: {var}")

        # Production-specific checks
        if os.getenv("ENVIRONMENT") == "production":
            for var in cls.REQUIRED_IN_PRODUCTION:
                if not os.getenv(var):
                    errors.append(f"Missing required production variable: {var}")

            # Check for insecure defaults
            if os.getenv("JWT_SECRET_KEY") == "changeme":
                errors.append("JWT_SECRET_KEY must be changed from default value")

        # Validate DATABASE_URL format
        db_url = os.getenv("DATABASE_URL", "")
        if db_url:
            try:
                parsed = urlparse(db_url)
                if not parsed.scheme or not parsed.netloc:
                    errors.append("Invalid DATABASE_URL format")
            except Exception:
                errors.append("Could not parse DATABASE_URL")

        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            logger.error(error_msg)
            raise ConfigurationError(error_msg)

        logger.info("Configuration validation passed")
        return True
