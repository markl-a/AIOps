"""Configuration management for AIOps framework."""

from typing import Optional, Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Main configuration class for AIOps framework."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )

    # LLM Settings
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    default_llm_provider: Literal["openai", "anthropic"] = "openai"
    default_model: str = "gpt-4-turbo-preview"
    default_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, gt=0)

    # Application Settings
    log_level: str = "INFO"
    enable_metrics: bool = True
    metrics_port: int = 9090

    # GitHub Integration
    github_token: Optional[str] = None
    github_repo: Optional[str] = None

    # Monitoring
    slack_webhook_url: Optional[str] = None
    discord_webhook_url: Optional[str] = None

    # Feature Flags
    enable_code_review: bool = True
    enable_test_generation: bool = True
    enable_log_analysis: bool = True
    enable_anomaly_detection: bool = True
    enable_auto_fix: bool = False  # Disabled by default for safety

    def get_llm_config(self, provider: Optional[str] = None) -> dict:
        """Get LLM configuration for specified provider."""
        provider = provider or self.default_llm_provider

        config = {
            "temperature": self.default_temperature,
            "max_tokens": self.max_tokens,
        }

        if provider == "openai":
            config["api_key"] = self.openai_api_key
            config["model"] = self.default_model
        elif provider == "anthropic":
            config["api_key"] = self.anthropic_api_key
            config["model"] = self.default_model

        return config


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
