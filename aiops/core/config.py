"""Configuration management for AIOps framework."""

from typing import Optional, Literal
from pydantic import Field, field_validator, ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict
import os
import secrets


class Config(BaseSettings):
    """Main configuration class for AIOps framework."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )

    # Environment
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = Field(default=False, description="Enable debug mode")

    # LLM Settings
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    default_llm_provider: Literal["openai", "anthropic"] = "openai"
    default_model: str = "gpt-4-turbo-preview"
    default_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, gt=0, le=128000)

    # LLM Retry and Timeout Settings
    llm_max_retries: int = Field(default=3, ge=0, le=10)
    llm_timeout: float = Field(default=30.0, gt=0, le=300)

    # Application Settings
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_file: Optional[str] = None
    log_rotation: str = "500 MB"
    log_retention: str = "30 days"
    enable_metrics: bool = True
    metrics_port: int = Field(default=9090, ge=1024, le=65535)

    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1024, le=65535)
    api_workers: int = Field(default=4, ge=1, le=32)
    api_reload: bool = False
    api_docs_enabled: bool = True  # Disabled in production by environment check

    # Security
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    jwt_secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = Field(default=60, ge=1, le=1440)
    webhook_signature_secret: Optional[str] = None
    session_timeout_minutes: int = Field(default=60, ge=5, le=1440)
    max_upload_size_mb: int = Field(default=10, ge=1, le=100)

    # Database Configuration
    database_url: Optional[str] = None
    database_user: str = "aiops"
    database_password: str = "aiops"  # CHANGE IN PRODUCTION
    database_host: str = "localhost"
    database_port: int = Field(default=5432, ge=1024, le=65535)
    database_name: str = "aiops"
    database_ssl_mode: Literal["disable", "require", "verify-ca", "verify-full"] = "disable"
    database_pool_size: int = Field(default=5, ge=1, le=100)
    database_max_overflow: int = Field(default=10, ge=0, le=100)
    database_pool_timeout: int = Field(default=30, ge=1, le=300)
    database_pool_recycle: int = Field(default=3600, ge=60, le=86400)
    database_echo: bool = False
    database_slow_query_threshold_ms: int = Field(default=1000, ge=100, le=10000)

    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    redis_ssl: bool = False
    redis_max_connections: int = Field(default=50, ge=10, le=200)
    redis_socket_timeout: int = Field(default=5, ge=1, le=60)
    enable_redis: bool = False

    # Celery Configuration
    celery_broker_url: Optional[str] = None  # Defaults to redis_url
    celery_result_backend: Optional[str] = None  # Defaults to redis_url
    celery_task_time_limit: int = Field(default=600, ge=60, le=3600)
    celery_task_soft_time_limit: int = Field(default=540, ge=50, le=3500)
    celery_worker_max_tasks_per_child: int = Field(default=1000, ge=100, le=10000)

    # Cache Configuration
    cache_enabled: bool = True
    cache_default_ttl: int = Field(default=3600, ge=60, le=86400)
    cache_dir: str = ".aiops_cache"

    # GitHub Integration
    github_token: Optional[str] = None
    github_repo: Optional[str] = None

    # Monitoring
    slack_webhook_url: Optional[str] = None
    slack_bot_token: Optional[str] = None
    discord_webhook_url: Optional[str] = None
    teams_webhook_url: Optional[str] = None

    # Observability
    sentry_dsn: Optional[str] = None
    otel_exporter_otlp_endpoint: Optional[str] = None
    otel_service_name: str = "aiops"
    otel_traces_enabled: bool = False

    # CORS Settings
    cors_origins: str = ""  # Empty by default for security
    cors_allow_credentials: bool = True
    cors_allow_methods: str = "GET,POST,PUT,DELETE,OPTIONS,PATCH"
    cors_allow_headers: str = "Content-Type,Authorization,X-API-Key,X-Request-ID,Accept,Origin"

    # Rate Limiting
    rate_limiting_enabled: bool = True
    rate_limit_default_requests: int = Field(default=100, ge=1, le=10000)
    rate_limit_default_window: int = Field(default=60, ge=1, le=3600)

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str, info: ValidationInfo) -> str:
        """Validate secret key strength in production."""
        environment = info.data.get("environment", "development")
        if environment == "production" and len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters in production")
        return v

    @field_validator("database_password")
    @classmethod
    def validate_database_password(cls, v: str, info: ValidationInfo) -> str:
        """Validate database password in production."""
        environment = info.data.get("environment", "development")
        if environment == "production" and v in ("aiops", "password", "admin", "root"):
            raise ValueError(
                "Database password is too weak for production. "
                "Set DATABASE_PASSWORD environment variable."
            )
        return v

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v: str, info: ValidationInfo) -> str:
        """Validate CORS origins in production."""
        environment = info.data.get("environment", "development")
        if environment == "production" and not v:
            import logging
            logging.getLogger(__name__).warning(
                "CORS_ORIGINS is empty in production. Set explicitly if needed."
            )
        if environment == "development" and not v:
            # Provide sensible defaults for development
            return "http://localhost:3000,http://localhost:8080"
        return v

    @field_validator("jwt_secret_key", mode="before")
    @classmethod
    def set_jwt_secret(cls, v: Optional[str], info: ValidationInfo) -> str:
        """Set JWT secret to main secret if not provided."""
        if v is None:
            return info.data.get("secret_key", secrets.token_urlsafe(32))
        return v

    def get_cors_origins(self) -> list:
        """Get CORS origins as a list."""
        import logging
        if self.cors_origins == "*":
            logging.getLogger(__name__).warning(
                "SECURITY WARNING: CORS origins set to '*' - this allows all origins. "
                "Consider restricting to specific domains in production."
            )
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def get_cors_methods(self) -> list:
        """Get CORS methods as a list."""
        import logging
        if self.cors_allow_methods == "*":
            logging.getLogger(__name__).warning(
                "SECURITY WARNING: CORS methods set to '*' - consider using explicit methods."
            )
            return ["*"]
        return [method.strip() for method in self.cors_allow_methods.split(",") if method.strip()]

    def get_cors_headers(self) -> list:
        """Get CORS headers as a list."""
        import logging
        if self.cors_allow_headers == "*":
            logging.getLogger(__name__).warning(
                "SECURITY WARNING: CORS headers set to '*' - consider using explicit headers."
            )
            return ["*"]
        return [header.strip() for header in self.cors_allow_headers.split(",") if header.strip()]

    # Feature Flags
    enable_code_review: bool = True
    enable_test_generation: bool = True
    enable_log_analysis: bool = True
    enable_anomaly_detection: bool = True
    enable_auto_fix: bool = False  # Disabled by default for safety

    def get_celery_broker_url(self) -> str:
        """Get Celery broker URL, defaulting to Redis URL."""
        return self.celery_broker_url or self.redis_url

    def get_celery_result_backend(self) -> str:
        """Get Celery result backend URL, defaulting to Redis URL."""
        return self.celery_result_backend or self.redis_url

    def get_database_url(self) -> str:
        """Get complete database URL."""
        if self.database_url:
            return self.database_url

        # Build from components
        ssl_param = f"?sslmode={self.database_ssl_mode}" if self.database_ssl_mode != "disable" else ""
        return (
            f"postgresql://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}{ssl_param}"
        )

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    def get_llm_config(self, provider: Optional[str] = None) -> dict:
        """Get LLM configuration for specified provider."""
        from typing import Any
        provider = provider or self.default_llm_provider

        config: dict[str, Any] = {
            "temperature": self.default_temperature,
            "max_tokens": self.max_tokens,
            "max_retries": self.llm_max_retries,
            "timeout": self.llm_timeout,
        }

        if provider == "openai":
            config["api_key"] = self.openai_api_key
            config["model"] = self.default_model
        elif provider == "anthropic":
            config["api_key"] = self.anthropic_api_key
            config["model"] = self.default_model

        return config

    def validate_production_config(self) -> list[str]:
        """Validate configuration for production deployment.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check required API keys
        if not self.openai_api_key and not self.anthropic_api_key:
            errors.append("At least one LLM API key (OpenAI or Anthropic) must be set in production")

        # Check secret key
        if len(self.secret_key) < 32:
            errors.append("SECRET_KEY must be at least 32 characters")

        # Check database SSL in production
        if self.database_ssl_mode == "disable":
            errors.append("Database SSL should be enabled in production (set DATABASE_SSL_MODE)")

        # Check Redis SSL in production
        if self.redis_url.startswith("redis://") and not self.redis_ssl:
            errors.append("Redis SSL should be enabled in production (use rediss:// or set REDIS_SSL=true)")

        # Check CORS origins
        if self.cors_origins == "*":
            errors.append("CORS_ORIGINS should not be '*' in production")

        # Check debug mode
        if self.debug:
            errors.append("DEBUG mode should be disabled in production")

        # Check weak database password
        if self.database_password in ("aiops", "password", "admin", "root"):
            errors.append("Database password is too weak for production")

        return errors


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def set_config(config: Config) -> None:
    """Set global configuration instance."""
    global _config
    _config = config
