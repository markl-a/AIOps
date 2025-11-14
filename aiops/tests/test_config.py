"""Tests for configuration management."""

import pytest
from aiops.core.config import Config, get_config, set_config


def test_config_creation():
    """Test configuration creation."""
    config = Config(
        openai_api_key="test_key",
        default_llm_provider="openai",
    )

    assert config.openai_api_key == "test_key"
    assert config.default_llm_provider == "openai"
    assert config.log_level == "INFO"  # Default value


def test_config_get_llm_config():
    """Test LLM configuration retrieval."""
    config = Config(
        openai_api_key="test_openai_key",
        anthropic_api_key="test_anthropic_key",
        default_temperature=0.5,
        max_tokens=2048,
    )

    openai_config = config.get_llm_config("openai")
    assert openai_config["api_key"] == "test_openai_key"
    assert openai_config["temperature"] == 0.5
    assert openai_config["max_tokens"] == 2048

    anthropic_config = config.get_llm_config("anthropic")
    assert anthropic_config["api_key"] == "test_anthropic_key"


def test_global_config():
    """Test global configuration singleton."""
    config = Config(openai_api_key="global_test_key")
    set_config(config)

    retrieved_config = get_config()
    assert retrieved_config.openai_api_key == "global_test_key"


def test_config_validation():
    """Test configuration validation."""
    # Temperature should be between 0 and 2
    with pytest.raises(ValueError):
        Config(default_temperature=3.0)

    with pytest.raises(ValueError):
        Config(default_temperature=-0.5)

    # Max tokens should be positive
    with pytest.raises(ValueError):
        Config(max_tokens=-100)
