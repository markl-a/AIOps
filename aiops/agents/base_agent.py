"""Base agent class for all AI agents."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TypeVar, Type, Callable
from functools import wraps
import asyncio
from aiops.core.llm_factory import LLMFactory, BaseLLM
from aiops.core.logger import get_logger
from aiops.agents.prompt_generator import AgentPromptGenerator

logger = get_logger(__name__)

# Type variable for return types
T = TypeVar('T')


class AgentExecutionError(Exception):
    """Exception raised when agent execution fails."""

    def __init__(self, agent_name: str, message: str, original_error: Optional[Exception] = None):
        self.agent_name = agent_name
        self.message = message
        self.original_error = original_error
        super().__init__(f"[{agent_name}] {message}")


def with_error_handling(
    default_factory: Optional[Callable[[], T]] = None,
    reraise: bool = False,
):
    """
    Decorator for agent methods that provides consistent error handling.

    Args:
        default_factory: Factory function to create default return value on error
        reraise: Whether to reraise the exception after logging

    Usage:
        @with_error_handling(default_factory=lambda: CodeReviewResult(...))
        async def execute(self, code: str) -> CodeReviewResult:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, **kwargs) -> T:
            try:
                return await func(self, *args, **kwargs)
            except asyncio.CancelledError:
                # Don't catch cancellation
                raise
            except Exception as e:
                agent_name = getattr(self, 'name', self.__class__.__name__)
                logger.error(
                    f"{agent_name}: Execution failed in {func.__name__}: {e}",
                    exc_info=True
                )
                if reraise:
                    raise AgentExecutionError(
                        agent_name=agent_name,
                        message=str(e),
                        original_error=e
                    ) from e
                if default_factory:
                    logger.warning(f"{agent_name}: Returning default value due to error")
                    return default_factory()
                raise
        return wrapper
    return decorator


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

    async def _safe_execute(
        self,
        operation: Callable,
        *args,
        default: Optional[T] = None,
        error_message: str = "Operation failed",
        **kwargs,
    ) -> T:
        """
        Safely execute an operation with error handling.

        Args:
            operation: The async operation to execute
            *args: Arguments to pass to the operation
            default: Default value to return on error
            error_message: Message to log on error
            **kwargs: Keyword arguments to pass to the operation

        Returns:
            Operation result or default value on error
        """
        try:
            if asyncio.iscoroutinefunction(operation):
                return await operation(*args, **kwargs)
            else:
                return await asyncio.to_thread(operation, *args, **kwargs)
        except Exception as e:
            logger.error(f"{self.name}: {error_message}: {e}")
            if default is not None:
                return default
            raise

    def _log_execution_start(self, operation: str, **context) -> None:
        """Log the start of an operation with context."""
        context_str = ", ".join(f"{k}={v}" for k, v in context.items()) if context else ""
        logger.info(f"{self.name}: Starting {operation}" + (f" ({context_str})" if context_str else ""))

    def _log_execution_complete(self, operation: str, **results) -> None:
        """Log the completion of an operation with results."""
        results_str = ", ".join(f"{k}={v}" for k, v in results.items()) if results else ""
        logger.info(f"{self.name}: Completed {operation}" + (f" ({results_str})" if results_str else ""))
