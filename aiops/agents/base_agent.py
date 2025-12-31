"""Base agent class for all AI agents."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TypeVar, Type, Callable, Union
from functools import wraps
import asyncio
from datetime import datetime
from aiops.core.llm_factory import LLMFactory, BaseLLM
from aiops.core.logger import get_logger
from pydantic import BaseModel, ValidationError

# Note: AgentPromptGenerator is available but not imported here to avoid coupling.
# Agents can import it directly if needed: from aiops.agents.prompt_generator import AgentPromptGenerator

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


class AgentTimeoutError(AgentExecutionError):
    """Exception raised when agent execution times out."""

    def __init__(self, agent_name: str, timeout_seconds: float):
        super().__init__(
            agent_name=agent_name,
            message=f"Execution timed out after {timeout_seconds}s"
        )
        self.timeout_seconds = timeout_seconds


class AgentValidationError(AgentExecutionError):
    """Exception raised when agent result validation fails."""

    def __init__(self, agent_name: str, validation_errors: Any):
        super().__init__(
            agent_name=agent_name,
            message=f"Result validation failed: {validation_errors}"
        )
        self.validation_errors = validation_errors


class AgentRetryExhaustedError(AgentExecutionError):
    """Exception raised when all retry attempts are exhausted."""

    def __init__(self, agent_name: str, attempts: int, last_error: Exception):
        super().__init__(
            agent_name=agent_name,
            message=f"All {attempts} retry attempts failed",
            original_error=last_error
        )
        self.attempts = attempts


def with_timeout(timeout_seconds: float):
    """
    Decorator that adds timeout to agent methods.

    Args:
        timeout_seconds: Maximum execution time in seconds

    Usage:
        @with_timeout(timeout_seconds=30.0)
        async def execute(self, data: str) -> Result:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            agent_name = getattr(self, 'name', self.__class__.__name__)
            try:
                return await asyncio.wait_for(
                    func(self, *args, **kwargs),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                logger.error(
                    f"{agent_name}: Operation timed out after {timeout_seconds}s"
                )
                raise AgentTimeoutError(
                    agent_name=agent_name,
                    timeout_seconds=timeout_seconds
                )
        return wrapper
    return decorator


def with_retry(
    max_attempts: int = 3,
    delay_seconds: float = 1.0,
    backoff_multiplier: float = 2.0,
    retry_exceptions: tuple = (Exception,)
):
    """
    Decorator that adds retry logic to agent methods.

    Args:
        max_attempts: Maximum number of attempts
        delay_seconds: Initial delay between retries
        backoff_multiplier: Multiplier for exponential backoff
        retry_exceptions: Tuple of exceptions to retry on

    Usage:
        @with_retry(max_attempts=3, delay_seconds=1.0)
        async def execute(self, data: str) -> Result:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            agent_name = getattr(self, 'name', self.__class__.__name__)
            last_error = None
            delay = delay_seconds

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(self, *args, **kwargs)
                except retry_exceptions as e:
                    last_error = e
                    if attempt < max_attempts:
                        logger.warning(
                            f"{agent_name}: Attempt {attempt}/{max_attempts} failed: {e}. "
                            f"Retrying in {delay}s..."
                        )
                        await asyncio.sleep(delay)
                        delay *= backoff_multiplier
                    else:
                        logger.error(
                            f"{agent_name}: All {max_attempts} attempts failed"
                        )
                except asyncio.CancelledError:
                    # Don't retry on cancellation
                    raise

            raise AgentRetryExhaustedError(
                agent_name=agent_name,
                attempts=max_attempts,
                last_error=last_error
            )
        return wrapper
    return decorator


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
    """Base class for all AI agents.

    Supports dependency injection of LLM instances for better testability
    and flexibility. If no LLM is provided, one will be created lazily.
    """

    def __init__(
        self,
        name: str,
        llm: Optional[BaseLLM] = None,
        llm_provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        timeout_seconds: Optional[float] = None,
        max_retries: int = 0,
    ):
        """Initialize the agent.

        Args:
            name: Agent name
            llm: Optional pre-configured LLM instance (dependency injection)
            llm_provider: LLM provider to use (if llm not provided)
            model: Model name (if llm not provided)
            temperature: Temperature setting (if llm not provided)
            timeout_seconds: Maximum execution time in seconds
            max_retries: Maximum number of retries on failure
        """
        self.name = name
        self.timeout_seconds = timeout_seconds or 300.0  # Default 5 minutes
        self.max_retries = max_retries
        # Support dependency injection
        self._llm = llm
        self._llm_provider = llm_provider
        self._model = model
        self._temperature = temperature
        logger.info(
            f"Initialized {self.name} agent "
            f"(timeout={self.timeout_seconds}s, retries={self.max_retries})"
        )

    @property
    def llm(self) -> BaseLLM:
        """Get LLM instance, creating it lazily if needed (supports dependency injection)."""
        if self._llm is None:
            self._llm = LLMFactory.create(
                provider=self._llm_provider,
                model=self._model,
                temperature=self._temperature,
            )
            logger.debug(f"{self.name}: Created LLM instance")
        return self._llm

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

    def _validate_result(
        self,
        result: Any,
        expected_type: Optional[Type[T]] = None,
        schema: Optional[Type[BaseModel]] = None,
    ) -> T:
        """
        Validate agent execution result.

        Args:
            result: The result to validate
            expected_type: Expected type of the result
            schema: Pydantic schema for validation

        Returns:
            Validated result

        Raises:
            AgentValidationError: If validation fails
        """
        try:
            # If schema is provided, validate with Pydantic
            if schema:
                if isinstance(result, schema):
                    return result
                elif isinstance(result, dict):
                    return schema(**result)
                else:
                    raise ValueError(f"Cannot convert {type(result)} to {schema}")

            # If expected_type is provided, check type
            if expected_type and not isinstance(result, expected_type):
                raise ValueError(
                    f"Expected type {expected_type}, got {type(result)}"
                )

            return result

        except (ValidationError, ValueError, TypeError) as e:
            logger.error(f"{self.name}: Result validation failed: {e}")
            raise AgentValidationError(
                agent_name=self.name,
                validation_errors=str(e)
            ) from e

    async def execute_with_validation(
        self,
        schema: Type[BaseModel],
        *args,
        **kwargs
    ) -> BaseModel:
        """
        Execute agent and validate result against schema.

        Args:
            schema: Pydantic schema for result validation
            *args: Arguments to pass to execute()
            **kwargs: Keyword arguments to pass to execute()

        Returns:
            Validated result

        Raises:
            AgentValidationError: If result validation fails
        """
        result = await self.execute(*args, **kwargs)
        return self._validate_result(result, schema=schema)

    async def execute_with_timeout(
        self,
        timeout_seconds: Optional[float] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute agent with timeout.

        Args:
            timeout_seconds: Maximum execution time (uses default if not provided)
            *args: Arguments to pass to execute()
            **kwargs: Keyword arguments to pass to execute()

        Returns:
            Execution result

        Raises:
            AgentTimeoutError: If execution times out
        """
        timeout = timeout_seconds or self.timeout_seconds
        try:
            return await asyncio.wait_for(
                self.execute(*args, **kwargs),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"{self.name}: Execution timed out after {timeout}s")
            raise AgentTimeoutError(
                agent_name=self.name,
                timeout_seconds=timeout
            )

    async def execute_with_retry(
        self,
        max_attempts: Optional[int] = None,
        delay_seconds: float = 1.0,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute agent with retry logic.

        Args:
            max_attempts: Maximum retry attempts (uses default if not provided)
            delay_seconds: Initial delay between retries
            *args: Arguments to pass to execute()
            **kwargs: Keyword arguments to pass to execute()

        Returns:
            Execution result

        Raises:
            AgentRetryExhaustedError: If all attempts fail
        """
        attempts = max_attempts or self.max_retries or 1
        last_error = None
        delay = delay_seconds

        for attempt in range(1, attempts + 1):
            try:
                return await self.execute(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < attempts:
                    logger.warning(
                        f"{self.name}: Attempt {attempt}/{attempts} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                    delay *= 2.0  # Exponential backoff
                else:
                    logger.error(f"{self.name}: All {attempts} attempts failed")

        raise AgentRetryExhaustedError(
            agent_name=self.name,
            attempts=attempts,
            last_error=last_error
        )
