"""Tests for LLM Provider Failover System"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from aiops.core.llm_providers import (
    LLMProvider,
    LLMProviderManager,
    OpenAIProvider,
    AnthropicProvider,
    GoogleProvider,
    ProviderStatus,
)
from aiops.core.llm_config import (
    LLMConfig,
    ProviderConfig,
    ProviderType,
    create_llm_manager_from_config,
    load_config_from_env,
)
from aiops.core.exceptions import (
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)


class MockProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self, name: str, should_fail: bool = False, **kwargs):
        super().__init__(name, "mock-api-key", **kwargs)
        self.should_fail = should_fail
        self.generate_calls = 0

    async def generate(self, prompt: str, **kwargs) -> str:
        """Mock generate method."""
        self.generate_calls += 1

        if self.should_fail:
            await self.record_failure(LLMProviderError("Mock failure"))
            raise LLMProviderError("Mock provider failed")

        await self.record_success()
        return f"Mock response from {self.name}"

    async def health_check(self) -> bool:
        """Mock health check."""
        return not self.should_fail


class TestLLMProvider:
    """Test LLM provider base functionality."""

    @pytest.mark.asyncio
    async def test_record_success(self):
        """Test recording successful requests."""
        provider = MockProvider("test")

        assert provider.total_requests == 0
        assert provider.successful_requests == 0
        assert provider.failure_count == 0

        await provider.record_success()

        assert provider.total_requests == 1
        assert provider.successful_requests == 1
        assert provider.failure_count == 0
        assert provider.status == ProviderStatus.HEALTHY
        assert provider.last_success is not None

    @pytest.mark.asyncio
    async def test_record_failure(self):
        """Test recording failed requests."""
        provider = MockProvider("test")

        error = LLMProviderError("Test error")
        await provider.record_failure(error)

        assert provider.total_requests == 1
        assert provider.successful_requests == 0
        assert provider.failure_count == 1
        assert provider.status == ProviderStatus.DEGRADED
        assert provider.last_failure is not None

    @pytest.mark.asyncio
    async def test_multiple_failures_mark_unavailable(self):
        """Test that multiple failures mark provider as unavailable."""
        provider = MockProvider("test")

        error = LLMProviderError("Test error")
        for _ in range(3):
            await provider.record_failure(error)

        assert provider.status == ProviderStatus.UNAVAILABLE
        assert provider.failure_count == 3

    @pytest.mark.asyncio
    async def test_rate_limit_error_sets_correct_status(self):
        """Test that rate limit errors set correct status."""
        provider = MockProvider("test")

        error = LLMRateLimitError("Rate limited")
        await provider.record_failure(error)

        assert provider.status == ProviderStatus.RATE_LIMITED

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        provider = MockProvider("test")

        # No requests yet
        assert provider.get_success_rate() == 1.0

        # Add some successes and failures
        provider.successful_requests = 7
        provider.total_requests = 10

        assert provider.get_success_rate() == 0.7


class TestLLMProviderManager:
    """Test LLM provider manager with failover."""

    @pytest.mark.asyncio
    async def test_basic_generation(self):
        """Test basic generation with single provider."""
        provider = MockProvider("test")
        manager = LLMProviderManager([provider])

        result, provider_name = await manager.generate("test prompt")

        assert result == "Mock response from test"
        assert provider_name == "test"
        assert provider.generate_calls == 1

    @pytest.mark.asyncio
    async def test_failover_to_second_provider(self):
        """Test automatic failover to second provider."""
        provider1 = MockProvider("primary", should_fail=True)
        provider2 = MockProvider("secondary", should_fail=False)

        manager = LLMProviderManager([provider1, provider2])

        result, provider_name = await manager.generate("test prompt")

        assert result == "Mock response from secondary"
        assert provider_name == "secondary"
        assert provider1.generate_calls == 1
        assert provider2.generate_calls == 1

    @pytest.mark.asyncio
    async def test_all_providers_fail(self):
        """Test behavior when all providers fail."""
        provider1 = MockProvider("provider1", should_fail=True)
        provider2 = MockProvider("provider2", should_fail=True)

        manager = LLMProviderManager([provider1, provider2])

        with pytest.raises(LLMProviderError) as exc_info:
            await manager.generate("test prompt")

        assert "All LLM providers failed" in str(exc_info.value)
        assert provider1.generate_calls == 1
        assert provider2.generate_calls == 1

    @pytest.mark.asyncio
    async def test_skip_unavailable_providers(self):
        """Test that unavailable providers are skipped."""
        provider1 = MockProvider("provider1")
        provider1.status = ProviderStatus.UNAVAILABLE

        provider2 = MockProvider("provider2")

        manager = LLMProviderManager([provider1, provider2])

        result, provider_name = await manager.generate("test prompt")

        assert provider_name == "provider2"
        assert provider1.generate_calls == 0  # Skipped
        assert provider2.generate_calls == 1

    @pytest.mark.asyncio
    async def test_health_check_all(self):
        """Test health check on all providers."""
        provider1 = MockProvider("healthy")
        provider2 = MockProvider("unhealthy", should_fail=True)

        manager = LLMProviderManager([provider1, provider2])

        results = await manager.health_check_all()

        assert results["healthy"] is True
        assert results["unhealthy"] is False
        assert provider1.status == ProviderStatus.HEALTHY
        assert provider2.status == ProviderStatus.UNAVAILABLE

    @pytest.mark.asyncio
    async def test_get_provider_stats(self):
        """Test getting provider statistics."""
        provider = MockProvider("test")
        await provider.record_success()
        await provider.record_failure(LLMProviderError("test"))

        manager = LLMProviderManager([provider])

        stats = await manager.get_provider_stats()

        assert len(stats) == 1
        assert stats[0]["name"] == "test"
        assert stats[0]["total_requests"] == 2
        assert stats[0]["successful_requests"] == 1
        assert stats[0]["success_rate"] == 0.5

    def test_get_healthy_providers(self):
        """Test filtering healthy providers."""
        provider1 = MockProvider("healthy1")
        provider2 = MockProvider("healthy2")
        provider3 = MockProvider("unhealthy")
        provider3.status = ProviderStatus.UNAVAILABLE

        manager = LLMProviderManager([provider1, provider2, provider3])

        healthy = manager.get_healthy_providers()

        assert len(healthy) == 2
        assert provider1 in healthy
        assert provider2 in healthy
        assert provider3 not in healthy


class TestLLMConfig:
    """Test LLM configuration."""

    def test_valid_config(self):
        """Test valid configuration."""
        config = LLMConfig(
            providers=[
                ProviderConfig(
                    type=ProviderType.OPENAI,
                    api_key="test-key",
                    priority=1,
                )
            ]
        )

        assert len(config.providers) == 1
        assert config.providers[0].type == ProviderType.OPENAI

    def test_config_requires_at_least_one_provider(self):
        """Test that config requires at least one provider."""
        with pytest.raises(ValueError, match="At least one provider"):
            LLMConfig(providers=[])

    def test_config_requires_enabled_provider_with_key(self):
        """Test that config requires at least one enabled provider with API key."""
        with pytest.raises(ValueError, match="At least one enabled provider"):
            LLMConfig(
                providers=[
                    ProviderConfig(
                        type=ProviderType.OPENAI,
                        api_key=None,
                        enabled=False,
                    )
                ]
            )

    def test_get_sorted_providers(self):
        """Test getting providers sorted by priority."""
        config = LLMConfig(
            providers=[
                ProviderConfig(
                    type=ProviderType.OPENAI,
                    api_key="key1",
                    priority=1,
                ),
                ProviderConfig(
                    type=ProviderType.ANTHROPIC,
                    api_key="key2",
                    priority=3,
                ),
                ProviderConfig(
                    type=ProviderType.GOOGLE,
                    api_key="key3",
                    priority=2,
                ),
            ]
        )

        sorted_providers = config.get_sorted_providers()

        assert len(sorted_providers) == 3
        assert sorted_providers[0].type == ProviderType.ANTHROPIC  # Priority 3
        assert sorted_providers[1].type == ProviderType.GOOGLE     # Priority 2
        assert sorted_providers[2].type == ProviderType.OPENAI     # Priority 1

    def test_provider_config_api_key_from_env(self):
        """Test loading API key from environment variable."""
        with patch.dict('os.environ', {'TEST_API_KEY': 'secret-key'}):
            config = ProviderConfig(
                type=ProviderType.OPENAI,
                api_key_env="TEST_API_KEY",
            )

            assert config.api_key == "secret-key"

    def test_provider_config_missing_env_var(self):
        """Test error when environment variable is missing."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="not set"):
                ProviderConfig(
                    type=ProviderType.OPENAI,
                    api_key_env="MISSING_KEY",
                )


class TestConfigLoading:
    """Test configuration loading from environment."""

    def test_load_config_from_env_default(self):
        """Test loading default config from environment."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            config = load_config_from_env()

            assert len(config.providers) >= 1
            assert config.failover_enabled is True

    def test_load_config_with_custom_priority(self):
        """Test loading config with custom provider priority."""
        env = {
            'OPENAI_API_KEY': 'openai-key',
            'ANTHROPIC_API_KEY': 'anthropic-key',
            'LLM_PROVIDER_PRIORITY': 'anthropic,openai',
        }

        with patch.dict('os.environ', env):
            config = load_config_from_env()

            sorted_providers = config.get_sorted_providers()
            # Anthropic should be first (higher priority)
            assert sorted_providers[0].type == ProviderType.ANTHROPIC

    def test_create_manager_from_config(self):
        """Test creating manager from configuration."""
        config = LLMConfig(
            providers=[
                ProviderConfig(
                    type=ProviderType.OPENAI,
                    api_key="test-key",
                    priority=1,
                )
            ]
        )

        with patch('aiops.core.llm_config.OpenAIProvider') as MockOpenAI:
            mock_instance = MagicMock()
            MockOpenAI.return_value = mock_instance

            manager = create_llm_manager_from_config(config)

            assert manager is not None
            assert len(manager.providers) == 1
            MockOpenAI.assert_called_once()


class TestRealProviders:
    """Integration tests with real providers (requires API keys)."""

    @pytest.mark.skipif(
        not pytest.config.getoption("--run-integration"),
        reason="Integration tests disabled (use --run-integration to enable)"
    )
    @pytest.mark.asyncio
    async def test_openai_provider_real(self):
        """Test OpenAI provider with real API."""
        import os

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            pytest.skip("OPENAI_API_KEY not set")

        provider = OpenAIProvider(api_key)

        result = await provider.generate(
            prompt="Say 'test' and nothing else",
            model="gpt-3.5-turbo",
            max_tokens=10,
        )

        assert result is not None
        assert len(result) > 0
        assert provider.status == ProviderStatus.HEALTHY

    @pytest.mark.skipif(
        not pytest.config.getoption("--run-integration"),
        reason="Integration tests disabled"
    )
    @pytest.mark.asyncio
    async def test_failover_with_real_providers(self):
        """Test failover with real providers."""
        import os

        openai_key = os.getenv("OPENAI_API_KEY")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")

        if not (openai_key and anthropic_key):
            pytest.skip("API keys not set")

        provider1 = OpenAIProvider(openai_key)
        provider2 = AnthropicProvider(anthropic_key)

        manager = LLMProviderManager([provider1, provider2])

        result, provider_name = await manager.generate(
            prompt="Say 'test' and nothing else",
            max_tokens=10,
        )

        assert result is not None
        assert provider_name in ["openai", "anthropic"]


def pytest_addoption(parser):
    """Add custom pytest options."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests with real APIs"
    )
