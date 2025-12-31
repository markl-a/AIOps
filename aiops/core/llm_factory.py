"""LLM Factory for creating and managing LLM instances."""

import threading
from typing import Optional, Any, Dict
from abc import ABC, abstractmethod
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.callbacks.base import BaseCallbackHandler
from aiops.core.config import get_config
from aiops.core.logger import get_logger
from aiops.core.token_tracker import get_token_tracker

logger = get_logger(__name__)


class TokenTrackingCallback(BaseCallbackHandler):
    """Callback to track token usage."""

    def __init__(self, model: str, provider: str, user: Optional[str] = None, agent: Optional[str] = None):
        """Initialize callback."""
        self.model = model
        self.provider = provider
        self.user = user
        self.agent = agent
        self.tracker = get_token_tracker()

    def on_llm_end(self, response, **kwargs):
        """Track tokens when LLM call ends."""
        try:
            # Extract token usage from response
            if hasattr(response, 'llm_output') and response.llm_output:
                token_usage = response.llm_output.get('token_usage', {})
                if token_usage:
                    input_tokens = token_usage.get('prompt_tokens', 0)
                    output_tokens = token_usage.get('completion_tokens', 0)

                    # Track usage
                    self.tracker.track(
                        model=self.model,
                        provider=self.provider,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        user=self.user,
                        agent=self.agent,
                    )
        except Exception as e:
            logger.warning(f"Failed to track token usage: {e}")


class BaseLLM(ABC):
    """Base class for LLM wrappers."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model = config.get("model", "unknown")
        self.provider = config.get("provider", "unknown")
        self.user = config.get("user")
        self.agent = config.get("agent")

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """Generate response from LLM."""
        pass

    @abstractmethod
    async def generate_structured(
        self, prompt: str, schema: Dict[str, Any], system_prompt: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        """Generate structured response from LLM."""
        pass

    def _create_callback(self):
        """Create token tracking callback."""
        return TokenTrackingCallback(
            model=self.model,
            provider=self.provider,
            user=self.user,
            agent=self.agent,
        )


class OpenAILLM(BaseLLM):
    """OpenAI LLM wrapper."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.llm = ChatOpenAI(
            model=config.get("model", "gpt-4-turbo-preview"),
            temperature=config.get("temperature", 0.7),
            max_tokens=config.get("max_tokens", 4096),
            api_key=config.get("api_key"),
            callbacks=[self._create_callback()],
        )

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """Generate response from OpenAI."""
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        try:
            logger.debug(f"OpenAI request: model={self.model}, prompt_length={len(prompt)}")
            response = await self.llm.ainvoke(messages, config={"callbacks": [self._create_callback()]})
            logger.debug(f"OpenAI response: length={len(response.content)}")
            return response.content
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise

    async def generate_structured(
        self, prompt: str, schema: Dict[str, Any], system_prompt: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        """Generate structured response from OpenAI."""
        # Use function calling for structured output
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        try:
            logger.debug(f"OpenAI structured request: model={self.model}, prompt_length={len(prompt)}")
            structured_llm = self.llm.with_structured_output(schema)
            response = await structured_llm.ainvoke(messages, config={"callbacks": [self._create_callback()]})
            logger.debug(f"OpenAI structured response received")
            return response
        except Exception as e:
            logger.error(f"OpenAI structured generation failed: {e}")
            raise


class AnthropicLLM(BaseLLM):
    """Anthropic Claude LLM wrapper."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.llm = ChatAnthropic(
            model=config.get("model", "claude-3-5-sonnet-20241022"),
            temperature=config.get("temperature", 0.7),
            max_tokens=config.get("max_tokens", 4096),
            api_key=config.get("api_key"),
            callbacks=[self._create_callback()],
        )

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """Generate response from Anthropic."""
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        try:
            logger.debug(f"Anthropic request: model={self.model}, prompt_length={len(prompt)}")
            response = await self.llm.ainvoke(messages, config={"callbacks": [self._create_callback()]})
            logger.debug(f"Anthropic response: length={len(response.content)}")
            return response.content
        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")
            raise

    async def generate_structured(
        self, prompt: str, schema: Dict[str, Any], system_prompt: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        """Generate structured response from Anthropic."""
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        try:
            logger.debug(f"Anthropic structured request: model={self.model}, prompt_length={len(prompt)}")
            structured_llm = self.llm.with_structured_output(schema)
            response = await structured_llm.ainvoke(messages, config={"callbacks": [self._create_callback()]})
            logger.debug(f"Anthropic structured response received")
            return response
        except Exception as e:
            logger.error(f"Anthropic structured generation failed: {e}")
            raise


class LLMFactory:
    """Factory for creating LLM instances."""

    _instances: Dict[str, BaseLLM] = {}
    _lock = threading.Lock()

    @classmethod
    def create(cls, provider: Optional[str] = None, **kwargs) -> BaseLLM:
        """Create or retrieve LLM instance."""
        config = get_config()
        provider = provider or config.default_llm_provider

        # Check if instance already exists
        cache_key = f"{provider}_{kwargs.get('model', config.default_model)}"

        with cls._lock:
            if cache_key in cls._instances:
                return cls._instances[cache_key]

        # Get LLM configuration (outside lock to avoid holding lock during config access)
        llm_config = config.get_llm_config(provider)
        llm_config.update(kwargs)
        llm_config["provider"] = provider

        # Create instance based on provider (outside lock to avoid holding lock during initialization)
        instance: BaseLLM
        if provider == "openai":
            instance = OpenAILLM(llm_config)
        elif provider == "anthropic":
            instance = AnthropicLLM(llm_config)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        # Cache instance with lock
        with cls._lock:
            # Double-check in case another thread created it while we were creating ours
            if cache_key not in cls._instances:
                cls._instances[cache_key] = instance
                logger.info(f"Created {provider} LLM instance with model {llm_config.get('model')}")
            else:
                instance = cls._instances[cache_key]

        return instance

    @classmethod
    def clear_cache(cls):
        """Clear cached LLM instances."""
        with cls._lock:
            cls._instances.clear()
            logger.info("Cleared LLM instance cache")
