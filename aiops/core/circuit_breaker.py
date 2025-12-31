"""Circuit breaker pattern implementation for resilient LLM calls."""

import asyncio
import time
from enum import Enum
from typing import Any, Callable, Optional, Dict, List
from dataclasses import dataclass, field
from functools import wraps
from collections import defaultdict
import threading

from aiops.core.logger import get_logger

logger = get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation, requests pass through
    OPEN = "open"          # Circuit is open, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitStats:
    """Statistics for a circuit breaker."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rejected_requests: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5          # Failures before opening circuit
    success_threshold: int = 3          # Successes before closing circuit
    timeout: float = 60.0               # Seconds before attempting recovery
    half_open_max_calls: int = 3        # Max concurrent calls in half-open state

    # Backoff configuration
    initial_backoff: float = 1.0        # Initial retry delay in seconds
    max_backoff: float = 60.0           # Maximum retry delay
    backoff_multiplier: float = 2.0     # Multiplier for exponential backoff

    # Monitoring
    window_size: int = 60               # Rolling window size in seconds


class CircuitBreaker:
    """
    Circuit breaker for resilient external service calls.

    Implements the circuit breaker pattern with:
    - Automatic failure detection and circuit opening
    - Configurable thresholds and timeouts
    - Exponential backoff for retries
    - Half-open state for recovery testing
    - Comprehensive statistics tracking

    Example:
        breaker = CircuitBreaker("openai_api")

        @breaker.protect
        async def call_openai():
            # API call here
            pass
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Name identifier for this circuit
            config: Configuration options
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()

        # State management
        self._state = CircuitState.CLOSED
        self._state_changed_at = time.time()
        self._half_open_calls = 0

        # Statistics
        self._stats = CircuitStats()
        self._lock = threading.Lock()

        # Failure tracking for rolling window
        self._failures: List[float] = []
        self._successes: List[float] = []

        # Backoff tracking
        self._current_backoff = self.config.initial_backoff

        logger.info(f"Circuit breaker '{name}' initialized in CLOSED state")

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing fast)."""
        return self._state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing recovery)."""
        return self._state == CircuitState.HALF_OPEN

    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "state_duration": time.time() - self._state_changed_at,
                "total_requests": self._stats.total_requests,
                "successful_requests": self._stats.successful_requests,
                "failed_requests": self._stats.failed_requests,
                "rejected_requests": self._stats.rejected_requests,
                "consecutive_failures": self._stats.consecutive_failures,
                "consecutive_successes": self._stats.consecutive_successes,
                "failure_rate": self._calculate_failure_rate(),
                "current_backoff": self._current_backoff,
            }

    def _calculate_failure_rate(self) -> float:
        """Calculate failure rate in current window."""
        now = time.time()
        window_start = now - self.config.window_size

        # Clean old entries
        self._failures = [t for t in self._failures if t > window_start]
        self._successes = [t for t in self._successes if t > window_start]

        total = len(self._failures) + len(self._successes)
        if total == 0:
            return 0.0

        return len(self._failures) / total

    def _should_allow_request(self) -> bool:
        """Determine if request should be allowed."""
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.OPEN:
                # Check if timeout has elapsed
                elapsed = time.time() - self._state_changed_at
                if elapsed >= self.config.timeout:
                    self._transition_to(CircuitState.HALF_OPEN)
                    return True
                return False

            if self._state == CircuitState.HALF_OPEN:
                # Allow limited calls in half-open state
                if self._half_open_calls < self.config.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False

            return False

    def _transition_to(self, new_state: CircuitState):
        """Transition to a new state."""
        old_state = self._state
        self._state = new_state
        self._state_changed_at = time.time()

        if new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
        elif new_state == CircuitState.CLOSED:
            self._current_backoff = self.config.initial_backoff

        logger.info(
            f"Circuit '{self.name}' transitioned from {old_state.value} to {new_state.value}"
        )

    def _record_success(self):
        """Record a successful request."""
        with self._lock:
            now = time.time()
            self._stats.total_requests += 1
            self._stats.successful_requests += 1
            self._stats.last_success_time = now
            self._stats.consecutive_successes += 1
            self._stats.consecutive_failures = 0
            self._successes.append(now)

            if self._state == CircuitState.HALF_OPEN:
                if self._stats.consecutive_successes >= self.config.success_threshold:
                    self._transition_to(CircuitState.CLOSED)

    def _record_failure(self, error: Exception):
        """Record a failed request."""
        with self._lock:
            now = time.time()
            self._stats.total_requests += 1
            self._stats.failed_requests += 1
            self._stats.last_failure_time = now
            self._stats.consecutive_failures += 1
            self._stats.consecutive_successes = 0
            self._failures.append(now)

            logger.warning(
                f"Circuit '{self.name}' recorded failure: {error}. "
                f"Consecutive failures: {self._stats.consecutive_failures}"
            )

            if self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open reopens circuit
                self._transition_to(CircuitState.OPEN)
                self._increase_backoff()
            elif self._state == CircuitState.CLOSED:
                if self._stats.consecutive_failures >= self.config.failure_threshold:
                    self._transition_to(CircuitState.OPEN)

    def _record_rejection(self):
        """Record a rejected request."""
        with self._lock:
            self._stats.total_requests += 1
            self._stats.rejected_requests += 1

    def _increase_backoff(self):
        """Increase backoff time exponentially."""
        self._current_backoff = min(
            self._current_backoff * self.config.backoff_multiplier,
            self.config.max_backoff,
        )

    def reset(self):
        """Reset circuit breaker to initial state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._state_changed_at = time.time()
            self._stats = CircuitStats()
            self._failures.clear()
            self._successes.clear()
            self._current_backoff = self.config.initial_backoff
            self._half_open_calls = 0

        logger.info(f"Circuit '{self.name}' reset to CLOSED state")

    async def call(
        self,
        func: Callable,
        *args,
        fallback: Optional[Callable] = None,
        **kwargs,
    ) -> Any:
        """
        Execute a function through the circuit breaker.

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            fallback: Optional fallback function if circuit is open
            **kwargs: Keyword arguments for func

        Returns:
            Result from func or fallback

        Raises:
            CircuitOpenError: If circuit is open and no fallback provided
        """
        if not self._should_allow_request():
            self._record_rejection()

            if fallback:
                logger.info(f"Circuit '{self.name}' is open, using fallback")
                if asyncio.iscoroutinefunction(fallback):
                    return await fallback(*args, **kwargs)
                return fallback(*args, **kwargs)

            raise CircuitOpenError(
                f"Circuit '{self.name}' is open. "
                f"Retry after {self._current_backoff:.1f}s"
            )

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            self._record_success()
            return result

        except Exception as e:
            self._record_failure(e)
            raise

    def protect(self, func: Callable) -> Callable:
        """
        Decorator to protect a function with this circuit breaker.

        Example:
            @breaker.protect
            async def call_api():
                pass
        """
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await self.call(func, *args, **kwargs)

        return wrapper


class CircuitOpenError(Exception):
    """Raised when circuit is open and no fallback is available."""
    pass


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._breakers: Dict[str, CircuitBreaker] = {}
        return cls._instance

    def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ) -> CircuitBreaker:
        """Get existing or create new circuit breaker."""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, config)
        return self._breakers[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self._breakers.get(name)

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers."""
        return {name: breaker.get_stats() for name, breaker in self._breakers.items()}

    def reset_all(self):
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            breaker.reset()


# Global registry instance
_registry = CircuitBreakerRegistry()


def get_circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None,
) -> CircuitBreaker:
    """Get or create a circuit breaker from the global registry."""
    return _registry.get_or_create(name, config)


def circuit_protected(
    name: str,
    config: Optional[CircuitBreakerConfig] = None,
    fallback: Optional[Callable] = None,
):
    """
    Decorator to protect a function with a circuit breaker.

    Args:
        name: Circuit breaker name
        config: Circuit breaker configuration
        fallback: Optional fallback function

    Example:
        @circuit_protected("openai_api")
        async def call_openai():
            pass
    """
    breaker = get_circuit_breaker(name, config)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await breaker.call(func, *args, fallback=fallback, **kwargs)

        wrapper.circuit_breaker = breaker
        return wrapper

    return decorator


class AdaptiveRetry:
    """
    Adaptive retry with exponential backoff.

    Example:
        retry = AdaptiveRetry()
        result = await retry.execute(api_call, max_retries=3)
    """

    def __init__(
        self,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0,
        jitter: float = 0.1,
    ):
        """
        Initialize adaptive retry.

        Args:
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            multiplier: Delay multiplier
            jitter: Random jitter factor (0-1)
        """
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.jitter = jitter

    async def execute(
        self,
        func: Callable,
        *args,
        max_retries: int = 3,
        retry_exceptions: tuple = (Exception,),
        **kwargs,
    ) -> Any:
        """
        Execute function with retry logic.

        Args:
            func: Async function to execute
            *args: Positional arguments
            max_retries: Maximum retry attempts
            retry_exceptions: Exceptions to retry on
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Last exception if all retries fail
        """
        import random

        last_exception = None
        delay = self.initial_delay

        for attempt in range(max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                return func(*args, **kwargs)

            except retry_exceptions as e:
                last_exception = e

                if attempt < max_retries:
                    # Add jitter
                    jittered_delay = delay * (1 + random.uniform(-self.jitter, self.jitter))

                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                        f"Retrying in {jittered_delay:.2f}s"
                    )

                    await asyncio.sleep(jittered_delay)

                    # Increase delay for next attempt
                    delay = min(delay * self.multiplier, self.max_delay)

        raise last_exception


class ConnectionPool:
    """
    Connection pool for managing concurrent connections.

    Limits the number of concurrent connections to external services.
    """

    def __init__(self, max_connections: int = 10, name: str = "default"):
        """
        Initialize connection pool.

        Args:
            max_connections: Maximum concurrent connections
            name: Pool name for logging
        """
        self.max_connections = max_connections
        self.name = name
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._active = 0
        self._lock = threading.Lock()

    def _ensure_semaphore(self):
        """Ensure semaphore is initialized (lazy initialization)."""
        if self._semaphore is None:
            try:
                self._semaphore = asyncio.Semaphore(self.max_connections)
            except RuntimeError:
                # No event loop running, create one
                loop = asyncio.get_event_loop()
                self._semaphore = asyncio.Semaphore(self.max_connections)

    @property
    def available(self) -> int:
        """Get number of available connections."""
        return self.max_connections - self._active

    async def acquire(self):
        """Acquire a connection from the pool."""
        self._ensure_semaphore()
        await self._semaphore.acquire()
        with self._lock:
            self._active += 1

    def release(self):
        """Release a connection back to the pool."""
        with self._lock:
            self._active -= 1
        if self._semaphore:
            self._semaphore.release()

    async def __aenter__(self):
        """Context manager entry."""
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()


def pooled(pool: ConnectionPool):
    """
    Decorator to limit concurrent executions using a connection pool.

    Example:
        pool = ConnectionPool(max_connections=5)

        @pooled(pool)
        async def api_call():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async with pool:
                return await func(*args, **kwargs)

        wrapper.pool = pool
        return wrapper

    return decorator
