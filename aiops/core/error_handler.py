"""Error handling utilities for AIOps framework."""

import traceback
import sys
from typing import Optional, Dict, Any, Callable
from functools import wraps
import asyncio
from loguru import logger

from aiops.core.exceptions import (
    AIOpsException,
    AgentExecutionError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
    handle_exception,
)


class ErrorHandler:
    """Centralized error handling for AIOps."""

    def __init__(self, enable_sentry: bool = False, sentry_dsn: Optional[str] = None):
        """Initialize error handler.

        Args:
            enable_sentry: Whether to enable Sentry integration
            sentry_dsn: Sentry DSN for error tracking
        """
        self.enable_sentry = enable_sentry
        self.sentry_dsn = sentry_dsn

        if enable_sentry and sentry_dsn:
            self._init_sentry()

    def _init_sentry(self):
        """Initialize Sentry for error tracking."""
        try:
            import sentry_sdk

            sentry_sdk.init(dsn=self.sentry_dsn, traces_sample_rate=0.1)
            logger.info("Sentry error tracking initialized")
        except ImportError:
            logger.warning("Sentry SDK not installed, error tracking disabled")
        except Exception as e:
            logger.error(f"Failed to initialize Sentry: {e}")

    def log_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        severity: str = "error",
    ):
        """Log error with context.

        Args:
            error: The exception
            context: Additional context information
            severity: Log severity level
        """
        aiops_error = handle_exception(error)

        log_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "error_code": getattr(aiops_error, "error_code", "UNKNOWN"),
            "traceback": traceback.format_exc(),
        }

        if context:
            log_data["context"] = context

        if hasattr(aiops_error, "details"):
            log_data["details"] = aiops_error.details

        # Log based on severity
        log_func = getattr(logger, severity, logger.error)
        log_func(f"Error occurred: {log_data}")

        # Send to Sentry if enabled
        if self.enable_sentry:
            self._send_to_sentry(error, context)

    def _send_to_sentry(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Send error to Sentry.

        Args:
            error: The exception
            context: Additional context
        """
        try:
            import sentry_sdk

            with sentry_sdk.push_scope() as scope:
                if context:
                    for key, value in context.items():
                        scope.set_extra(key, value)

                if isinstance(error, AIOpsException):
                    scope.set_tag("error_code", error.error_code)
                    for key, value in error.details.items():
                        scope.set_extra(key, value)

                sentry_sdk.capture_exception(error)
        except Exception as e:
            logger.warning(f"Failed to send error to Sentry: {e}")

    def handle_agent_error(
        self,
        error: Exception,
        agent_name: str,
        operation: str = "execute",
    ) -> AIOpsException:
        """Handle agent execution errors.

        Args:
            error: The exception
            agent_name: Name of the agent
            operation: Operation that failed

        Returns:
            AIOpsException with context
        """
        if isinstance(error, AIOpsException):
            return error

        # Wrap in agent-specific error
        agent_error = AgentExecutionError(
            agent_name=agent_name,
            message=f"Agent '{agent_name}' failed during {operation}: {str(error)}",
            original_error=error,
        )

        self.log_error(
            agent_error,
            context={"agent_name": agent_name, "operation": operation},
        )

        return agent_error

    def handle_llm_error(
        self,
        error: Exception,
        provider: str,
        model: Optional[str] = None,
        retry_count: int = 0,
    ) -> AIOpsException:
        """Handle LLM provider errors.

        Args:
            error: The exception
            provider: LLM provider name
            model: Model name
            retry_count: Number of retries attempted

        Returns:
            AIOpsException with context
        """
        # Check for rate limit
        if "rate limit" in str(error).lower() or "429" in str(error):
            llm_error = LLMRateLimitError(provider=provider)
        # Check for timeout
        elif isinstance(error, (TimeoutError, asyncio.TimeoutError)):
            llm_error = LLMTimeoutError(provider=provider, timeout_seconds=30)
        # Generic LLM error
        else:
            llm_error = LLMProviderError(
                message=f"LLM request failed: {str(error)}",
                provider=provider,
                model=model,
                original_error=error,
            )

        self.log_error(
            llm_error,
            context={
                "provider": provider,
                "model": model,
                "retry_count": retry_count,
            },
        )

        return llm_error


# Global error handler instance
_error_handler = ErrorHandler()


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance."""
    return _error_handler


def configure_error_handler(enable_sentry: bool = False, sentry_dsn: Optional[str] = None):
    """Configure global error handler.

    Args:
        enable_sentry: Whether to enable Sentry
        sentry_dsn: Sentry DSN
    """
    global _error_handler
    _error_handler = ErrorHandler(enable_sentry=enable_sentry, sentry_dsn=sentry_dsn)


# Decorators for error handling
def handle_errors(
    agent_name: Optional[str] = None,
    operation: str = "execute",
    raise_on_error: bool = False,
    default_return: Any = None,
):
    """Decorator to handle errors in functions.

    Args:
        agent_name: Name of the agent (for context)
        operation: Operation name
        raise_on_error: Whether to re-raise errors
        default_return: Default return value on error

    Returns:
        Decorated function
    """

    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_handler = get_error_handler()

                if agent_name:
                    handled_error = error_handler.handle_agent_error(
                        error=e,
                        agent_name=agent_name,
                        operation=operation,
                    )
                else:
                    handled_error = handle_exception(e)
                    error_handler.log_error(handled_error)

                if raise_on_error:
                    raise handled_error
                return default_return

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler = get_error_handler()

                if agent_name:
                    handled_error = error_handler.handle_agent_error(
                        error=e,
                        agent_name=agent_name,
                        operation=operation,
                    )
                else:
                    handled_error = handle_exception(e)
                    error_handler.log_error(handled_error)

                if raise_on_error:
                    raise handled_error
                return default_return

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def retry_on_error(
    max_retries: int = 3,
    retry_on: tuple = (LLMRateLimitError, LLMTimeoutError),
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
):
    """Decorator to retry function on specific errors.

    Args:
        max_retries: Maximum number of retries
        retry_on: Tuple of exceptions to retry on
        backoff_factor: Exponential backoff factor
        initial_delay: Initial delay in seconds

    Returns:
        Decorated function
    """

    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            delay = initial_delay
            last_error = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retry_on as e:
                    last_error = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Retry attempt {attempt + 1}/{max_retries} after error: {e}. "
                            f"Waiting {delay}s..."
                        )
                        await asyncio.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(f"Max retries ({max_retries}) exceeded")

            raise last_error

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            import time

            delay = initial_delay
            last_error = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retry_on as e:
                    last_error = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Retry attempt {attempt + 1}/{max_retries} after error: {e}. "
                            f"Waiting {delay}s..."
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(f"Max retries ({max_retries}) exceeded")

            raise last_error

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def safe_execute(func: Callable, *args, **kwargs) -> tuple[bool, Any]:
    """Safely execute a function and return success status.

    Args:
        func: Function to execute
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Tuple of (success: bool, result_or_error: Any)
    """
    try:
        if asyncio.iscoroutinefunction(func):
            # For async functions, need to be called from async context
            result = asyncio.run(func(*args, **kwargs))
        else:
            result = func(*args, **kwargs)
        return True, result
    except Exception as e:
        error_handler = get_error_handler()
        handled_error = handle_exception(e)
        error_handler.log_error(handled_error)
        return False, handled_error
