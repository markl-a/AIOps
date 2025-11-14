"""Base agent class for all AI agents."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from aiops.core.llm_factory import LLMFactory, BaseLLM
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class BaseAgent(ABC):
    """Base class for all AI agents."""

    def __init__(
        self,
        name: str,
        llm_provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        self.name = name
        self.llm: BaseLLM = LLMFactory.create(
            provider=llm_provider,
            model=model,
            temperature=temperature,
        )
        logger.info(f"Initialized {self.name} agent")

    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """Execute the agent's main task."""
        pass

    async def _generate_response(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> str:
        """Generate response from LLM."""
        try:
            response = await self.llm.generate(prompt, system_prompt)
            logger.debug(f"{self.name}: Generated response (length: {len(response)})")
            return response
        except Exception as e:
            logger.error(f"{self.name}: Failed to generate response: {e}")
            raise

    async def _generate_structured_response(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate structured response from LLM."""
        try:
            response = await self.llm.generate_structured(prompt, schema, system_prompt)
            logger.debug(f"{self.name}: Generated structured response")
            return response
        except Exception as e:
            logger.error(f"{self.name}: Failed to generate structured response: {e}")
            raise
