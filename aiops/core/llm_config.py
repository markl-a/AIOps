"""LLM Provider Configuration Management

This module manages configuration for multiple LLM providers with priority
and fallback settings.
"""

import os
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator
from enum import Enum

from aiops.core.llm_providers import (
    LLMProvider,
    LLMProviderManager,
    OpenAIProvider,
    AnthropicProvider,
    GoogleProvider,
)


class ProviderType(str, Enum):
    """Supported LLM provider types."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


class ProviderConfig(BaseModel):
    """Configuration for a single LLM provider."""

    type: ProviderType
    api_key: Optional[str] = None
    api_key_env: Optional[str] = None  # Environment variable name
    priority: int = Field(default=0, ge=0)
    enabled: bool = True
    max_retries: int = Field(default=3, ge=0, le=10)
    timeout: float = Field(default=30.0, gt=0, le=300)
    default_model: Optional[str] = None

    @validator('api_key', always=True)
    def validate_api_key(cls, v, values):
        """Validate that API key is provided either directly or via env var."""
        if v:
            return v

        api_key_env = values.get('api_key_env')
        if api_key_env:
            key = os.getenv(api_key_env)
            if not key:
                raise ValueError(
                    f"API key environment variable {api_key_env} not set"
                )
            return key

        # If neither is provided, that's okay - it will be disabled
        return None

    class Config:
        use_enum_values = True


class LLMConfig(BaseModel):
    """Complete LLM configuration."""

    providers: List[ProviderConfig] = Field(default_factory=list)
    failover_enabled: bool = True
    health_check_interval: int = Field(default=60, ge=10, le=3600)
    default_max_tokens: int = Field(default=4000, ge=1, le=32000)
    default_temperature: float = Field(default=0.7, ge=0.0, le=2.0)

    @validator('providers')
    def validate_providers(cls, v):
        """Ensure at least one provider is configured."""
        if not v:
            raise ValueError("At least one provider must be configured")

        # Ensure at least one provider is enabled
        if not any(p.enabled and p.api_key for p in v):
            raise ValueError("At least one enabled provider with API key required")

        return v

    def get_sorted_providers(self) -> List[ProviderConfig]:
        """Get providers sorted by priority (higher priority first)."""
        return sorted(
            [p for p in self.providers if p.enabled and p.api_key],
            key=lambda x: x.priority,
            reverse=True,
        )

    class Config:
        use_enum_values = True


def create_provider_instance(config: ProviderConfig) -> LLMProvider:
    """Create a provider instance from configuration.

    Args:
        config: Provider configuration

    Returns:
        LLMProvider instance

    Raises:
        ValueError: If provider type is not supported
    """
    provider_classes = {
        ProviderType.OPENAI: OpenAIProvider,
        ProviderType.ANTHROPIC: AnthropicProvider,
        ProviderType.GOOGLE: GoogleProvider,
    }

    provider_class = provider_classes.get(config.type)
    if not provider_class:
        raise ValueError(f"Unsupported provider type: {config.type}")

    return provider_class(
        api_key=config.api_key,
        max_retries=config.max_retries,
        timeout=config.timeout,
    )


def create_llm_manager_from_config(config: LLMConfig) -> LLMProviderManager:
    """Create LLM provider manager from configuration.

    Args:
        config: LLM configuration

    Returns:
        Configured LLMProviderManager instance
    """
    # Get sorted providers
    sorted_configs = config.get_sorted_providers()

    # Create provider instances
    providers = []
    for provider_config in sorted_configs:
        try:
            provider = create_provider_instance(provider_config)
            providers.append(provider)
        except Exception as e:
            # Log but continue - we need at least one working provider
            print(f"Warning: Failed to create provider {provider_config.type}: {e}")

    if not providers:
        raise ValueError("No valid providers could be created")

    # Create manager
    manager = LLMProviderManager(providers)
    manager.health_check_interval = config.health_check_interval

    return manager


def load_config_from_env() -> LLMConfig:
    """Load LLM configuration from environment variables.

    Environment variables:
    - OPENAI_API_KEY: OpenAI API key
    - ANTHROPIC_API_KEY: Anthropic API key
    - GOOGLE_API_KEY: Google API key
    - LLM_PROVIDER_PRIORITY: Comma-separated provider order (e.g., "openai,anthropic")
    - LLM_FAILOVER_ENABLED: Enable failover (default: true)

    Returns:
        LLM configuration
    """
    providers = []

    # Default priority order
    priority_str = os.getenv("LLM_PROVIDER_PRIORITY", "openai,anthropic,google")
    priority_list = [p.strip() for p in priority_str.split(",")]

    # Create provider configs based on priority
    for idx, provider_type in enumerate(priority_list):
        priority = len(priority_list) - idx  # Higher index = higher priority

        if provider_type == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                providers.append(ProviderConfig(
                    type=ProviderType.OPENAI,
                    api_key=api_key,
                    priority=priority,
                    enabled=True,
                ))

        elif provider_type == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                providers.append(ProviderConfig(
                    type=ProviderType.ANTHROPIC,
                    api_key=api_key,
                    priority=priority,
                    enabled=True,
                ))

        elif provider_type == "google":
            api_key = os.getenv("GOOGLE_API_KEY")
            if api_key:
                providers.append(ProviderConfig(
                    type=ProviderType.GOOGLE,
                    api_key=api_key,
                    priority=priority,
                    enabled=True,
                ))

    if not providers:
        # If no API keys in env, create a default config
        # (will fail validation if user tries to use it)
        providers.append(ProviderConfig(
            type=ProviderType.OPENAI,
            api_key_env="OPENAI_API_KEY",
            priority=1,
            enabled=False,
        ))

    failover_enabled = os.getenv("LLM_FAILOVER_ENABLED", "true").lower() == "true"

    return LLMConfig(
        providers=providers,
        failover_enabled=failover_enabled,
    )


# Example configurations
EXAMPLE_CONFIGS = {
    "openai_only": LLMConfig(
        providers=[
            ProviderConfig(
                type=ProviderType.OPENAI,
                api_key_env="OPENAI_API_KEY",
                priority=1,
            )
        ],
        failover_enabled=False,
    ),
    "openai_anthropic_failover": LLMConfig(
        providers=[
            ProviderConfig(
                type=ProviderType.OPENAI,
                api_key_env="OPENAI_API_KEY",
                priority=2,  # Primary
            ),
            ProviderConfig(
                type=ProviderType.ANTHROPIC,
                api_key_env="ANTHROPIC_API_KEY",
                priority=1,  # Fallback
            ),
        ],
        failover_enabled=True,
    ),
    "multi_provider": LLMConfig(
        providers=[
            ProviderConfig(
                type=ProviderType.OPENAI,
                api_key_env="OPENAI_API_KEY",
                priority=3,  # Highest priority
                max_retries=3,
                timeout=30.0,
            ),
            ProviderConfig(
                type=ProviderType.ANTHROPIC,
                api_key_env="ANTHROPIC_API_KEY",
                priority=2,  # Second priority
                max_retries=3,
                timeout=30.0,
            ),
            ProviderConfig(
                type=ProviderType.GOOGLE,
                api_key_env="GOOGLE_API_KEY",
                priority=1,  # Last resort
                max_retries=2,
                timeout=20.0,
            ),
        ],
        failover_enabled=True,
        health_check_interval=60,
    ),
}


def get_example_config(name: str) -> LLMConfig:
    """Get an example configuration by name.

    Args:
        name: Configuration name (e.g., "openai_only", "multi_provider")

    Returns:
        LLM configuration

    Raises:
        KeyError: If configuration name not found
    """
    if name not in EXAMPLE_CONFIGS:
        available = ", ".join(EXAMPLE_CONFIGS.keys())
        raise KeyError(
            f"Configuration '{name}' not found. Available: {available}"
        )

    return EXAMPLE_CONFIGS[name]
