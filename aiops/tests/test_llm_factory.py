"""Tests for LLM Factory."""

import pytest
from unittest.mock import patch, AsyncMock
from aiops.core.llm_factory import LLMFactory, OpenAILLM, AnthropicLLM
from aiops.core.config import Config, set_config


@pytest.fixture
def setup_config():
    """Setup test configuration."""
    config = Config(
        openai_api_key="test_openai_key",
        anthropic_api_key="test_anthropic_key",
        default_llm_provider="openai",
    )
    set_config(config)
    yield config
    LLMFactory.clear_cache()


def test_create_openai_llm(setup_config):
    """Test OpenAI LLM creation."""
    llm = LLMFactory.create(provider="openai")

    assert isinstance(llm, OpenAILLM)
    assert llm.config["api_key"] == "test_openai_key"


def test_create_anthropic_llm(setup_config):
    """Test Anthropic LLM creation."""
    llm = LLMFactory.create(provider="anthropic")

    assert isinstance(llm, AnthropicLLM)
    assert llm.config["api_key"] == "test_anthropic_key"


def test_llm_caching(setup_config):
    """Test LLM instance caching."""
    llm1 = LLMFactory.create(provider="openai")
    llm2 = LLMFactory.create(provider="openai")

    # Should return the same cached instance
    assert llm1 is llm2


def test_llm_cache_clearing(setup_config):
    """Test LLM cache clearing."""
    llm1 = LLMFactory.create(provider="openai")

    LLMFactory.clear_cache()

    llm2 = LLMFactory.create(provider="openai")

    # Should be different instances after cache clear
    assert llm1 is not llm2


def test_invalid_provider(setup_config):
    """Test invalid LLM provider."""
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        LLMFactory.create(provider="invalid_provider")


def test_custom_model(setup_config):
    """Test LLM creation with custom model."""
    llm = LLMFactory.create(provider="openai", model="gpt-3.5-turbo")

    assert "gpt-3.5-turbo" in str(llm.config.get("model", ""))


@pytest.mark.asyncio
async def test_openai_generate():
    """Test OpenAI generate method."""
    config = {"api_key": "test_key", "model": "gpt-4", "temperature": 0.7}

    with patch("aiops.core.llm_factory.ChatOpenAI") as mock_chat:
        mock_instance = AsyncMock()
        mock_instance.ainvoke = AsyncMock(
            return_value=AsyncMock(content="Test response")
        )
        mock_chat.return_value = mock_instance

        llm = OpenAILLM(config)
        response = await llm.generate("Test prompt")

        assert response == "Test response"
        mock_instance.ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_anthropic_generate():
    """Test Anthropic generate method."""
    config = {"api_key": "test_key", "model": "claude-3-5-sonnet-20241022", "temperature": 0.7}

    with patch("aiops.core.llm_factory.ChatAnthropic") as mock_chat:
        mock_instance = AsyncMock()
        mock_instance.ainvoke = AsyncMock(
            return_value=AsyncMock(content="Test response")
        )
        mock_chat.return_value = mock_instance

        llm = AnthropicLLM(config)
        response = await llm.generate("Test prompt", "System prompt")

        assert response == "Test response"
        mock_instance.ainvoke.assert_called_once()
