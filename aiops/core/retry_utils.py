"""Retry utilities with exponential backoff."""
import asyncio
import functools
import logging
from typing import Tuple, Type, Callable, Optional

logger = logging.getLogger(__name__)


def retry_async(
    max_retries: int = 3,
    retry_on: Tuple[Type[Exception], ...] = (Exception,),
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    on_retry: Optional[Callable] = None,
):
    """Async retry decorator with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        retry_on: Tuple of exception types to retry on
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries
        backoff_factor: Multiplier for delay after each retry
        on_retry: Optional callback function called on each retry

    Example:
        @retry_async(max_retries=3, retry_on=(TimeoutError, ConnectionError))
        async def fetch_data():
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retry_on as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} retries: {e}"
                        )
                        raise

                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )

                    if on_retry:
                        on_retry(attempt, e)

                    await asyncio.sleep(delay)
                    delay = min(delay * backoff_factor, max_delay)

            raise last_exception

        return wrapper
    return decorator


def retry_sync(
    max_retries: int = 3,
    retry_on: Tuple[Type[Exception], ...] = (Exception,),
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
):
    """Synchronous retry decorator with exponential backoff."""
    import time

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retry_on as e:
                    last_exception = e

                    if attempt == max_retries:
                        raise

                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )

                    time.sleep(delay)
                    delay = min(delay * backoff_factor, max_delay)

            raise last_exception

        return wrapper
    return decorator


def with_timeout(seconds: float = 30.0):
    """Async timeout decorator.

    Args:
        seconds: Timeout in seconds

    Raises:
        asyncio.TimeoutError: If operation exceeds timeout
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=seconds
                )
            except asyncio.TimeoutError:
                logger.error(f"{func.__name__} timed out after {seconds}s")
                raise

        return wrapper
    return decorator
