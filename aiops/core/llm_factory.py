"""LLM Factory for creating and managing LLM instances."""

from typing import Optional, Any, Dict
from abc import ABC, abstractmethod
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.schema import HumanMessage, SystemMessage
from aiops.core.config import get_config
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class BaseLLM(ABC):
    """Base class for LLM wrappers."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate response from LLM."""
        pass

    @abstractmethod
    async def generate_structured(
        self, prompt: str, schema: Dict[str, Any], system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate structured response from LLM."""
        pass


class OpenAILLM(BaseLLM):
    """OpenAI LLM wrapper."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.llm = ChatOpenAI(
            model=config.get("model", "gpt-4-turbo-preview"),
            temperature=config.get("temperature", 0.7),
            max_tokens=config.get("max_tokens", 4096),
            api_key=config.get("api_key"),
        )

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate response from OpenAI."""
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        try:
            response = await self.llm.ainvoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise

    async def generate_structured(
        self, prompt: str, schema: Dict[str, Any], system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate structured response from OpenAI."""
        # Use function calling for structured output
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        try:
            structured_llm = self.llm.with_structured_output(schema)
            response = await structured_llm.ainvoke(messages)
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
        )

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate response from Anthropic."""
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        try:
            response = await self.llm.ainvoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")
            raise

    async def generate_structured(
        self, prompt: str, schema: Dict[str, Any], system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate structured response from Anthropic."""
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        try:
            structured_llm = self.llm.with_structured_output(schema)
            response = await structured_llm.ainvoke(messages)
            return response
        except Exception as e:
            logger.error(f"Anthropic structured generation failed: {e}")
            raise


class LLMFactory:
    """Factory for creating LLM instances."""

    _instances: Dict[str, BaseLLM] = {}

    @classmethod
    def create(cls, provider: Optional[str] = None, **kwargs) -> BaseLLM:
        """Create or retrieve LLM instance."""
        config = get_config()
        provider = provider or config.default_llm_provider

        # Check if instance already exists
        cache_key = f"{provider}_{kwargs.get('model', config.default_model)}"
        if cache_key in cls._instances:
            return cls._instances[cache_key]

        # Get LLM configuration
        llm_config = config.get_llm_config(provider)
        llm_config.update(kwargs)

        # Create instance based on provider
        if provider == "openai":
            instance = OpenAILLM(llm_config)
        elif provider == "anthropic":
            instance = AnthropicLLM(llm_config)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        # Cache instance
        cls._instances[cache_key] = instance
        logger.info(f"Created {provider} LLM instance with model {llm_config.get('model')}")

        return instance

    @classmethod
    def clear_cache(cls):
        """Clear cached LLM instances."""
        cls._instances.clear()
        logger.info("Cleared LLM instance cache")
