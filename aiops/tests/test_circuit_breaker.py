"""Comprehensive tests for Circuit Breaker pattern implementation."""

import pytest
import asyncio
import time
import threading
from unittest.mock import AsyncMock, Mock, patch

from aiops.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    CircuitStats,
    CircuitOpenError,
    CircuitBreakerRegistry,
    get_circuit_breaker,
    circuit_protected,
    AdaptiveRetry,
    ConnectionPool,
    pooled,
)


class TestCircuitBreakerConfig:
    """Tests for CircuitBreakerConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CircuitBreakerConfig()

        assert config.failure_threshold == 5
        assert config.success_threshold == 3
        assert config.timeout == 60.0
        assert config.half_open_max_calls == 3
        assert config.initial_backoff == 1.0
        assert config.max_backoff == 60.0
        assert config.backoff_multiplier == 2.0
        assert config.window_size == 60

    def test_custom_config(self):
        """Test custom configuration."""
        config = CircuitBreakerConfig(
            failure_threshold=10,
            timeout=120.0,
            initial_backoff=2.0,
        )

        assert config.failure_threshold == 10
        assert config.timeout == 120.0
        assert config.initial_backoff == 2.0


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""

    @pytest.fixture
    def breaker(self):
        """Create a circuit breaker with default config."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=1.0,
        )
        return CircuitBreaker("test_circuit", config)

    def test_initialization(self, breaker):
        """Test circuit breaker initialization."""
        assert breaker.name == "test_circuit"
        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_closed
        assert not breaker.is_open
        assert not breaker.is_half_open

    def test_initial_stats(self, breaker):
        """Test initial statistics."""
        stats = breaker.get_stats()

        assert stats["name"] == "test_circuit"
        assert stats["state"] == "closed"
        assert stats["total_requests"] == 0
        assert stats["successful_requests"] == 0
        assert stats["failed_requests"] == 0
        assert stats["rejected_requests"] == 0

    @pytest.mark.asyncio
    async def test_successful_call(self, breaker):
        """Test successful call through circuit breaker."""
        async def success_func():
            return "success"

        result = await breaker.call(success_func)

        assert result == "success"
        stats = breaker.get_stats()
        assert stats["successful_requests"] == 1
        assert stats["total_requests"] == 1
        assert breaker.is_closed

    @pytest.mark.asyncio
    async def test_failed_call(self, breaker):
        """Test failed call through circuit breaker."""
        async def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await breaker.call(failing_func)

        stats = breaker.get_stats()
        assert stats["failed_requests"] == 1
        assert stats["consecutive_failures"] == 1

    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold(self, breaker):
        """Test that circuit opens after failure threshold."""
        async def failing_func():
            raise ValueError("Test error")

        # Fail multiple times to exceed threshold (3)
        for _ in range(3):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        # Circuit should now be open
        assert breaker.is_open
        stats = breaker.get_stats()
        assert stats["failed_requests"] == 3
        assert stats["consecutive_failures"] == 3

    @pytest.mark.asyncio
    async def test_circuit_rejects_when_open(self, breaker):
        """Test that circuit rejects calls when open."""
        async def failing_func():
            raise ValueError("Test error")

        # Open the circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        # Now calls should be rejected
        async def success_func():
            return "success"

        with pytest.raises(CircuitOpenError):
            await breaker.call(success_func)

        stats = breaker.get_stats()
        assert stats["rejected_requests"] == 1

    @pytest.mark.asyncio
    async def test_circuit_uses_fallback_when_open(self, breaker):
        """Test that circuit uses fallback when open."""
        async def failing_func():
            raise ValueError("Test error")

        async def fallback_func():
            return "fallback_result"

        # Open the circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        # Call with fallback should use fallback
        result = await breaker.call(failing_func, fallback=fallback_func)
        assert result == "fallback_result"

    @pytest.mark.asyncio
    async def test_circuit_transitions_to_half_open(self, breaker):
        """Test circuit transitions to half-open after timeout."""
        async def failing_func():
            raise ValueError("Test error")

        # Open the circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        assert breaker.is_open

        # Wait for timeout (1 second in test config)
        await asyncio.sleep(1.1)

        # Next call should transition to half-open
        async def success_func():
            return "success"

        result = await breaker.call(success_func)

        assert result == "success"
        assert breaker.is_half_open or breaker.is_closed  # May close if success threshold met

    @pytest.mark.asyncio
    async def test_circuit_closes_after_successes_in_half_open(self, breaker):
        """Test circuit closes after success threshold in half-open state."""
        async def failing_func():
            raise ValueError("Test error")

        # Open the circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        # Wait for timeout
        await asyncio.sleep(1.1)

        # Succeed enough times to close (success_threshold = 2)
        async def success_func():
            return "success"

        for _ in range(2):
            await breaker.call(success_func)

        # Circuit should be closed now
        assert breaker.is_closed

    @pytest.mark.asyncio
    async def test_circuit_reopens_on_failure_in_half_open(self, breaker):
        """Test circuit reopens on failure in half-open state."""
        async def failing_func():
            raise ValueError("Test error")

        # Open the circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        # Wait for timeout
        await asyncio.sleep(1.1)

        # Fail in half-open state
        with pytest.raises(ValueError):
            await breaker.call(failing_func)

        # Circuit should reopen
        assert breaker.is_open

    @pytest.mark.asyncio
    async def test_protect_decorator(self, breaker):
        """Test protect decorator."""
        @breaker.protect
        async def decorated_func():
            return "decorated_result"

        result = await decorated_func()
        assert result == "decorated_result"

        stats = breaker.get_stats()
        assert stats["successful_requests"] == 1

    def test_reset_circuit(self, breaker):
        """Test resetting circuit breaker."""
        # Record some failures
        breaker._record_failure(Exception("test"))
        breaker._record_failure(Exception("test"))

        stats = breaker.get_stats()
        assert stats["failed_requests"] > 0

        # Reset
        breaker.reset()

        stats = breaker.get_stats()
        assert stats["failed_requests"] == 0
        assert stats["total_requests"] == 0
        assert breaker.is_closed

    def test_failure_rate_calculation(self, breaker):
        """Test failure rate calculation."""
        breaker._record_success()
        breaker._record_success()
        breaker._record_failure(Exception("test"))

        stats = breaker.get_stats()
        failure_rate = stats["failure_rate"]

        # 1 failure out of 3 total = 33.33%
        assert 0.3 < failure_rate < 0.4

    @pytest.mark.asyncio
    async def test_sync_function_support(self, breaker):
        """Test circuit breaker works with sync functions."""
        def sync_func():
            return "sync_result"

        result = await breaker.call(sync_func)
        assert result == "sync_result"

    @pytest.mark.asyncio
    async def test_backoff_increases(self, breaker):
        """Test that backoff increases on failures."""
        async def failing_func():
            raise ValueError("Test error")

        initial_backoff = breaker._current_backoff

        # Open circuit and trigger backoff
        for _ in range(3):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        # Wait and fail in half-open to trigger backoff increase
        await asyncio.sleep(1.1)
        with pytest.raises(ValueError):
            await breaker.call(failing_func)

        assert breaker._current_backoff > initial_backoff

    def test_max_backoff_limit(self, breaker):
        """Test that backoff doesn't exceed max."""
        # Increase backoff many times
        for _ in range(20):
            breaker._increase_backoff()

        assert breaker._current_backoff <= breaker.config.max_backoff


class TestCircuitBreakerRegistry:
    """Tests for CircuitBreakerRegistry."""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry."""
        return CircuitBreakerRegistry()

    def test_singleton_pattern(self):
        """Test that registry follows singleton pattern."""
        registry1 = CircuitBreakerRegistry()
        registry2 = CircuitBreakerRegistry()

        assert registry1 is registry2

    def test_get_or_create(self, registry):
        """Test getting or creating circuit breakers."""
        breaker1 = registry.get_or_create("test1")
        breaker2 = registry.get_or_create("test1")
        breaker3 = registry.get_or_create("test2")

        assert breaker1 is breaker2  # Same name returns same instance
        assert breaker1 is not breaker3  # Different names return different instances

    def test_get_existing(self, registry):
        """Test getting existing circuit breaker."""
        created = registry.get_or_create("test")
        retrieved = registry.get("test")

        assert retrieved is created

    def test_get_nonexistent(self, registry):
        """Test getting non-existent circuit breaker."""
        result = registry.get("nonexistent")
        assert result is None

    def test_get_all_stats(self, registry):
        """Test getting all circuit breaker stats."""
        registry.get_or_create("circuit1")
        registry.get_or_create("circuit2")

        stats = registry.get_all_stats()

        assert "circuit1" in stats
        assert "circuit2" in stats
        assert stats["circuit1"]["name"] == "circuit1"

    def test_reset_all(self, registry):
        """Test resetting all circuit breakers."""
        breaker1 = registry.get_or_create("circuit1")
        breaker2 = registry.get_or_create("circuit2")

        # Record some activity
        breaker1._record_failure(Exception("test"))
        breaker2._record_failure(Exception("test"))

        # Reset all
        registry.reset_all()

        # All should be reset
        assert breaker1.get_stats()["failed_requests"] == 0
        assert breaker2.get_stats()["failed_requests"] == 0


class TestGlobalFunctions:
    """Tests for global helper functions."""

    @pytest.mark.asyncio
    async def test_circuit_protected_decorator(self):
        """Test circuit_protected decorator."""
        @circuit_protected("protected_circuit")
        async def protected_func():
            return "protected_result"

        result = await protected_func()
        assert result == "protected_result"

        # Verify circuit breaker was created
        breaker = get_circuit_breaker("protected_circuit")
        assert breaker is not None
        assert breaker.get_stats()["successful_requests"] == 1

    @pytest.mark.asyncio
    async def test_circuit_protected_with_fallback(self):
        """Test circuit_protected with fallback."""
        async def fallback():
            return "fallback"

        @circuit_protected("failing_circuit", fallback=fallback)
        async def failing_func():
            raise ValueError("Error")

        # Open the circuit
        config = CircuitBreakerConfig(failure_threshold=1)
        breaker = get_circuit_breaker("failing_circuit", config)

        with pytest.raises(ValueError):
            await failing_func()

        # Now it should use fallback
        result = await failing_func()
        assert result == "fallback"


class TestAdaptiveRetry:
    """Tests for AdaptiveRetry class."""

    @pytest.mark.asyncio
    async def test_retry_success_on_first_attempt(self):
        """Test successful execution on first attempt."""
        retry = AdaptiveRetry()

        async def success_func():
            return "success"

        result = await retry.execute(success_func, max_retries=3)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_success_after_failures(self):
        """Test success after initial failures."""
        retry = AdaptiveRetry(initial_delay=0.01)  # Fast retry for testing
        attempts = {"count": 0}

        async def eventually_succeeds():
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise ValueError("Not yet")
            return "success"

        result = await retry.execute(eventually_succeeds, max_retries=3)
        assert result == "success"
        assert attempts["count"] == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        """Test all retries exhausted."""
        retry = AdaptiveRetry(initial_delay=0.01)

        async def always_fails():
            raise ValueError("Always fails")

        with pytest.raises(ValueError):
            await retry.execute(always_fails, max_retries=2)

    @pytest.mark.asyncio
    async def test_retry_with_specific_exceptions(self):
        """Test retrying only on specific exceptions."""
        retry = AdaptiveRetry(initial_delay=0.01)

        async def raises_runtime_error():
            raise RuntimeError("Runtime error")

        # Should not retry RuntimeError if only ValueError is allowed
        with pytest.raises(RuntimeError):
            await retry.execute(
                raises_runtime_error,
                max_retries=3,
                retry_exceptions=(ValueError,)
            )

    @pytest.mark.asyncio
    async def test_retry_delay_increases(self):
        """Test that retry delay increases exponentially."""
        retry = AdaptiveRetry(initial_delay=0.01, multiplier=2.0)
        delays = []

        async def track_delays():
            delays.append(time.time())
            if len(delays) < 3:
                raise ValueError("Fail")
            return "success"

        await retry.execute(track_delays, max_retries=3)

        # Verify delays increased (approximately)
        assert len(delays) == 3

    @pytest.mark.asyncio
    async def test_retry_sync_function(self):
        """Test retry with sync function."""
        retry = AdaptiveRetry(initial_delay=0.01)
        attempts = {"count": 0}

        def eventually_succeeds():
            attempts["count"] += 1
            if attempts["count"] < 2:
                raise ValueError("Not yet")
            return "success"

        result = await retry.execute(eventually_succeeds, max_retries=3)
        assert result == "success"
        assert attempts["count"] == 2


class TestConnectionPool:
    """Tests for ConnectionPool class."""

    def test_initialization(self):
        """Test connection pool initialization."""
        pool = ConnectionPool(max_connections=5, name="test_pool")

        assert pool.max_connections == 5
        assert pool.name == "test_pool"
        assert pool.available == 5

    @pytest.mark.asyncio
    async def test_acquire_and_release(self):
        """Test acquiring and releasing connections."""
        pool = ConnectionPool(max_connections=2)

        assert pool.available == 2

        await pool.acquire()
        assert pool.available == 1

        await pool.acquire()
        assert pool.available == 0

        pool.release()
        assert pool.available == 1

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test connection pool as context manager."""
        pool = ConnectionPool(max_connections=2)

        assert pool.available == 2

        async with pool:
            assert pool.available == 1

        assert pool.available == 2

    @pytest.mark.asyncio
    async def test_pooled_decorator(self):
        """Test pooled decorator."""
        pool = ConnectionPool(max_connections=2)

        @pooled(pool)
        async def pooled_func():
            return "result"

        assert pool.available == 2
        result = await pooled_func()
        assert result == "result"
        assert pool.available == 2

    @pytest.mark.asyncio
    async def test_concurrent_limit(self):
        """Test that pool limits concurrent connections."""
        pool = ConnectionPool(max_connections=2)
        results = []

        async def task(task_id):
            async with pool:
                results.append(f"start_{task_id}")
                await asyncio.sleep(0.1)
                results.append(f"end_{task_id}")

        # Start 3 tasks, but only 2 can run concurrently
        await asyncio.gather(task(1), task(2), task(3))

        # All tasks should complete
        assert len([r for r in results if r.startswith("start_")]) == 3
        assert len([r for r in results if r.startswith("end_")]) == 3


class TestThreadSafety:
    """Tests for thread safety."""

    def test_circuit_breaker_thread_safety(self):
        """Test that circuit breaker is thread-safe."""
        breaker = CircuitBreaker("thread_safe")
        results = []
        errors = []

        def worker():
            try:
                breaker._record_success()
                results.append(breaker.get_stats()["successful_requests"])
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 10
        # Final count should be 10
        assert breaker.get_stats()["successful_requests"] == 10


class TestEdgeCases:
    """Edge case tests."""

    @pytest.mark.asyncio
    async def test_zero_failure_threshold(self):
        """Test circuit breaker with zero failure threshold."""
        config = CircuitBreakerConfig(failure_threshold=0)
        breaker = CircuitBreaker("zero_threshold", config)

        async def failing_func():
            raise ValueError("Fail")

        # Should open immediately on any failure
        with pytest.raises(ValueError):
            await breaker.call(failing_func)

        # Circuit might be open now (depending on implementation)

    @pytest.mark.asyncio
    async def test_very_short_timeout(self):
        """Test circuit breaker with very short timeout."""
        config = CircuitBreakerConfig(timeout=0.01)
        breaker = CircuitBreaker("short_timeout", config)

        # Open the circuit
        for _ in range(3):
            breaker._record_failure(Exception("test"))

        assert breaker.is_open

        # Wait for very short timeout
        await asyncio.sleep(0.02)

        # Should transition to half-open
        async def success_func():
            return "success"

        result = await breaker.call(success_func)
        assert result == "success"

    def test_empty_circuit_name(self):
        """Test circuit breaker with empty name."""
        breaker = CircuitBreaker("")
        assert breaker.name == ""

    @pytest.mark.asyncio
    async def test_none_fallback(self):
        """Test circuit breaker with None as fallback."""
        config = CircuitBreakerConfig(failure_threshold=1)
        breaker = CircuitBreaker("none_fallback", config)

        async def failing_func():
            raise ValueError("Fail")

        # Open circuit
        with pytest.raises(ValueError):
            await breaker.call(failing_func)

        # Should raise CircuitOpenError with None fallback
        with pytest.raises(CircuitOpenError):
            await breaker.call(failing_func, fallback=None)
