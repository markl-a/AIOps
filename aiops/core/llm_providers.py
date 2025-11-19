"""LLM Provider Management with Failover Support

This module provides a unified interface for multiple LLM providers with
automatic failover capabilities.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging

from aiops.core.exceptions import (
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMAuthenticationError,
)
from aiops.core.structured_logger import get_structured_logger


logger = get_structured_logger(__name__)


class ProviderStatus(str, Enum):
    """Status of an LLM provider."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(
        self,
        name: str,
        api_key: str,
        max_retries: int = 3,
        timeout: float = 30.0,
    ):
        self.name = name
        self.api_key = api_key
        self.max_retries = max_retries
        self.timeout = timeout
        self.status = ProviderStatus.HEALTHY
        self.last_success: Optional[datetime] = None
        self.last_failure: Optional[datetime] = None
        self.failure_count = 0
        self.total_requests = 0
        self.successful_requests = 0

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: str,
        max_tokens: int = 4000,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """Generate completion from the LLM.

        Args:
            prompt: The input prompt
            model: Model identifier
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional provider-specific parameters

        Returns:
            Generated text

        Raises:
            LLMProviderError: If generation fails
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is healthy.

        Returns:
            True if healthy, False otherwise
        """
        pass

    async def record_success(self):
        """Record a successful request."""
        self.last_success = datetime.now()
        self.successful_requests += 1
        self.total_requests += 1
        self.failure_count = 0

        if self.status != ProviderStatus.HEALTHY:
            logger.info(
                f"Provider {self.name} recovered",
                provider=self.name,
                status=ProviderStatus.HEALTHY,
            )
            self.status = ProviderStatus.HEALTHY

    async def record_failure(self, error: Exception):
        """Record a failed request."""
        self.last_failure = datetime.now()
        self.failure_count += 1
        self.total_requests += 1

        # Update status based on error type
        if isinstance(error, LLMRateLimitError):
            self.status = ProviderStatus.RATE_LIMITED
        elif self.failure_count >= 3:
            self.status = ProviderStatus.UNAVAILABLE
        else:
            self.status = ProviderStatus.DEGRADED

        logger.warning(
            f"Provider {self.name} failure recorded",
            provider=self.name,
            status=self.status,
            failure_count=self.failure_count,
            error=str(error),
        )

    def get_success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider."""

    def __init__(self, api_key: str, **kwargs):
        super().__init__("openai", api_key, **kwargs)
        self.default_model = "gpt-4-turbo-preview"

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """Generate completion using OpenAI API."""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=self.api_key,
                timeout=self.timeout,
            )

            response = await client.chat.completions.create(
                model=model or self.default_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs,
            )

            await self.record_success()
            return response.choices[0].message.content

        except Exception as e:
            await self.record_failure(e)

            # Convert to our exception types
            error_msg = str(e).lower()
            if "rate_limit" in error_msg or "quota" in error_msg:
                raise LLMRateLimitError(f"OpenAI rate limit: {e}")
            elif "timeout" in error_msg:
                raise LLMTimeoutError(f"OpenAI timeout: {e}")
            elif "authentication" in error_msg or "api_key" in error_msg:
                raise LLMAuthenticationError(f"OpenAI auth error: {e}")
            else:
                raise LLMProviderError(f"OpenAI error: {e}")

    async def health_check(self) -> bool:
        """Check OpenAI API health."""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key, timeout=5.0)

            # Simple test request
            await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
            )
            return True
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return False


class AnthropicProvider(LLMProvider):
    """Anthropic Claude LLM provider."""

    def __init__(self, api_key: str, **kwargs):
        super().__init__("anthropic", api_key, **kwargs)
        self.default_model = "claude-3-sonnet-20240229"

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """Generate completion using Anthropic API."""
        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(
                api_key=self.api_key,
                timeout=self.timeout,
            )

            response = await client.messages.create(
                model=model or self.default_model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
                **kwargs,
            )

            await self.record_success()
            return response.content[0].text

        except Exception as e:
            await self.record_failure(e)

            error_msg = str(e).lower()
            if "rate_limit" in error_msg or "quota" in error_msg:
                raise LLMRateLimitError(f"Anthropic rate limit: {e}")
            elif "timeout" in error_msg:
                raise LLMTimeoutError(f"Anthropic timeout: {e}")
            elif "authentication" in error_msg or "api_key" in error_msg:
                raise LLMAuthenticationError(f"Anthropic auth error: {e}")
            else:
                raise LLMProviderError(f"Anthropic error: {e}")

    async def health_check(self) -> bool:
        """Check Anthropic API health."""
        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=self.api_key, timeout=5.0)

            await client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=5,
                messages=[{"role": "user", "content": "test"}],
            )
            return True
        except Exception as e:
            logger.error(f"Anthropic health check failed: {e}")
            return False


class GoogleProvider(LLMProvider):
    """Google Gemini LLM provider."""

    def __init__(self, api_key: str, **kwargs):
        super().__init__("google", api_key, **kwargs)
        self.default_model = "gemini-pro"

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """Generate completion using Google Gemini API."""
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            model_instance = genai.GenerativeModel(model or self.default_model)

            response = await asyncio.wait_for(
                asyncio.to_thread(
                    model_instance.generate_content,
                    prompt,
                    generation_config={
                        "max_output_tokens": max_tokens,
                        "temperature": temperature,
                    },
                ),
                timeout=self.timeout,
            )

            await self.record_success()
            return response.text

        except Exception as e:
            await self.record_failure(e)

            error_msg = str(e).lower()
            if "quota" in error_msg or "rate" in error_msg:
                raise LLMRateLimitError(f"Google rate limit: {e}")
            elif "timeout" in error_msg:
                raise LLMTimeoutError(f"Google timeout: {e}")
            else:
                raise LLMProviderError(f"Google error: {e}")

    async def health_check(self) -> bool:
        """Check Google Gemini API health."""
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel("gemini-pro")

            await asyncio.wait_for(
                asyncio.to_thread(model.generate_content, "test"),
                timeout=5.0,
            )
            return True
        except Exception as e:
            logger.error(f"Google health check failed: {e}")
            return False


class LLMProviderManager:
    """Manages multiple LLM providers with automatic failover."""

    def __init__(self, providers: List[LLMProvider]):
        """Initialize provider manager.

        Args:
            providers: List of LLM providers in priority order
        """
        if not providers:
            raise ValueError("At least one provider is required")

        self.providers = providers
        self.current_provider_index = 0
        self.health_check_interval = 60  # seconds
        self._last_health_check: Optional[datetime] = None

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 0.7,
        **kwargs,
    ) -> Tuple[str, str]:
        """Generate completion with automatic failover.

        Args:
            prompt: Input prompt
            model: Model identifier (provider-specific)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters

        Returns:
            Tuple of (generated_text, provider_name)

        Raises:
            LLMProviderError: If all providers fail
        """
        errors = []

        # Try each provider in order
        for attempt, provider in enumerate(self.providers):
            # Skip unavailable providers
            if provider.status == ProviderStatus.UNAVAILABLE:
                logger.debug(
                    f"Skipping unavailable provider {provider.name}",
                    provider=provider.name,
                    status=provider.status,
                )
                continue

            # If rate limited, skip for a while
            if provider.status == ProviderStatus.RATE_LIMITED:
                if (provider.last_failure and
                    datetime.now() - provider.last_failure < timedelta(minutes=5)):
                    logger.debug(
                        f"Skipping rate-limited provider {provider.name}",
                        provider=provider.name,
                    )
                    continue

            try:
                logger.info(
                    f"Attempting generation with provider {provider.name}",
                    provider=provider.name,
                    attempt=attempt + 1,
                    total_providers=len(self.providers),
                )

                result = await provider.generate(
                    prompt=prompt,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs,
                )

                # Success! Update current provider
                self.current_provider_index = self.providers.index(provider)

                logger.info(
                    f"Successfully generated with {provider.name}",
                    provider=provider.name,
                    success_rate=provider.get_success_rate(),
                )

                return result, provider.name

            except (LLMRateLimitError, LLMTimeoutError, LLMProviderError) as e:
                errors.append((provider.name, str(e)))
                logger.warning(
                    f"Provider {provider.name} failed, trying next",
                    provider=provider.name,
                    error=str(e),
                    next_provider=(
                        self.providers[attempt + 1].name
                        if attempt + 1 < len(self.providers)
                        else None
                    ),
                )
                continue

        # All providers failed
        error_summary = "; ".join([f"{name}: {err}" for name, err in errors])
        raise LLMProviderError(
            f"All LLM providers failed. Errors: {error_summary}",
            details={"errors": errors},
        )

    async def health_check_all(self) -> Dict[str, bool]:
        """Run health checks on all providers.

        Returns:
            Dictionary mapping provider names to health status
        """
        logger.info("Running health checks on all providers")

        results = {}
        tasks = []

        for provider in self.providers:
            tasks.append(provider.health_check())

        health_results = await asyncio.gather(*tasks, return_exceptions=True)

        for provider, is_healthy in zip(self.providers, health_results):
            if isinstance(is_healthy, Exception):
                results[provider.name] = False
                provider.status = ProviderStatus.UNAVAILABLE
            else:
                results[provider.name] = is_healthy
                if is_healthy:
                    provider.status = ProviderStatus.HEALTHY
                else:
                    provider.status = ProviderStatus.UNAVAILABLE

        self._last_health_check = datetime.now()

        logger.info(
            "Health check completed",
            results=results,
        )

        return results

    async def get_provider_stats(self) -> List[Dict[str, Any]]:
        """Get statistics for all providers.

        Returns:
            List of provider statistics
        """
        stats = []

        for provider in self.providers:
            stats.append({
                "name": provider.name,
                "status": provider.status,
                "total_requests": provider.total_requests,
                "successful_requests": provider.successful_requests,
                "success_rate": provider.get_success_rate(),
                "failure_count": provider.failure_count,
                "last_success": (
                    provider.last_success.isoformat()
                    if provider.last_success
                    else None
                ),
                "last_failure": (
                    provider.last_failure.isoformat()
                    if provider.last_failure
                    else None
                ),
            })

        return stats

    def get_healthy_providers(self) -> List[LLMProvider]:
        """Get list of currently healthy providers.

        Returns:
            List of healthy providers
        """
        return [
            p for p in self.providers
            if p.status == ProviderStatus.HEALTHY
        ]

    async def auto_health_check(self):
        """Automatically run health checks at intervals."""
        while True:
            await asyncio.sleep(self.health_check_interval)

            try:
                await self.health_check_all()
            except Exception as e:
                logger.error(f"Auto health check failed: {e}")
