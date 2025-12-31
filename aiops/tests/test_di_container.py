"""Comprehensive tests for Dependency Injection Container."""

import pytest
import threading
from unittest.mock import Mock
from aiops.core.di_container import (
    DIContainer,
    get_container,
    reset_container,
)


class DummyService:
    """Dummy service for testing."""

    def __init__(self, name: str = "default"):
        self.name = name

    def get_name(self):
        return self.name


class DependentService:
    """Service that depends on DummyService."""

    def __init__(self, dependency: DummyService):
        self.dependency = dependency

    def get_dependency_name(self):
        return self.dependency.get_name()


class TestDIContainer:
    """Tests for DIContainer class."""

    @pytest.fixture
    def container(self):
        """Create a fresh DI container for each test."""
        container = DIContainer()
        yield container
        container.clear()

    def test_register_singleton(self, container):
        """Test registering a singleton instance."""
        service = DummyService("test")
        container.register_singleton(DummyService, service)

        # Should return the same instance
        result1 = container.get(DummyService)
        result2 = container.get(DummyService)

        assert result1 is service
        assert result2 is service
        assert result1 is result2

    def test_register_factory(self, container):
        """Test registering a factory function."""
        call_count = {"count": 0}

        def factory():
            call_count["count"] += 1
            return DummyService(f"instance_{call_count['count']}")

        container.register_factory(DummyService, factory)

        # Should create new instance each time
        result1 = container.get(DummyService)
        result2 = container.get(DummyService)

        assert result1 is not result2
        assert result1.name == "instance_1"
        assert result2.name == "instance_2"
        assert call_count["count"] == 2

    def test_register_transient(self, container):
        """Test registering a transient type."""
        container.register_transient(DummyService, DummyService)

        # Should create new instance each time
        result1 = container.get(DummyService)
        result2 = container.get(DummyService)

        assert result1 is not result2
        assert isinstance(result1, DummyService)
        assert isinstance(result2, DummyService)

    def test_get_nonexistent_type(self, container):
        """Test getting a type that is not registered."""
        with pytest.raises(KeyError) as exc_info:
            container.get(DummyService)

        assert "No registration found for type: DummyService" in str(exc_info.value)

    def test_try_get_returns_none_for_nonexistent(self, container):
        """Test try_get returns None for unregistered types."""
        result = container.try_get(DummyService)
        assert result is None

    def test_try_get_returns_instance_when_registered(self, container):
        """Test try_get returns instance when type is registered."""
        service = DummyService("test")
        container.register_singleton(DummyService, service)

        result = container.try_get(DummyService)
        assert result is service

    def test_is_registered(self, container):
        """Test is_registered method."""
        assert container.is_registered(DummyService) is False

        service = DummyService()
        container.register_singleton(DummyService, service)

        assert container.is_registered(DummyService) is True

    def test_clear(self, container):
        """Test clearing all registrations."""
        service = DummyService()
        container.register_singleton(DummyService, service)

        assert container.is_registered(DummyService) is True

        container.clear()

        assert container.is_registered(DummyService) is False
        with pytest.raises(KeyError):
            container.get(DummyService)

    def test_get_registrations_stats(self, container):
        """Test getting registration statistics."""
        stats = container.get_registrations()
        assert stats["singletons"] == 0
        assert stats["factories"] == 0
        assert stats["transient"] == 0
        assert stats["total"] == 0

        # Register different types
        container.register_singleton(DummyService, DummyService())
        container.register_factory(str, lambda: "test")
        container.register_transient(int, int)

        stats = container.get_registrations()
        assert stats["singletons"] == 1
        assert stats["factories"] == 1
        assert stats["transient"] == 1
        assert stats["total"] == 3

    def test_dependency_injection(self, container):
        """Test dependency injection pattern."""
        dummy = DummyService("injected")
        container.register_singleton(DummyService, dummy)

        # Register factory that uses injected dependency
        def dependent_factory():
            return DependentService(container.get(DummyService))

        container.register_factory(DependentService, dependent_factory)

        # Get dependent service
        dependent = container.get(DependentService)

        assert isinstance(dependent, DependentService)
        assert dependent.get_dependency_name() == "injected"

    def test_thread_safety_singleton(self, container):
        """Test thread safety for singleton registration and retrieval."""
        service = DummyService("thread-safe")
        container.register_singleton(DummyService, service)

        results = []
        errors = []

        def worker():
            try:
                result = container.get(DummyService)
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Create multiple threads accessing the same singleton
        threads = [threading.Thread(target=worker) for _ in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All threads should get the same instance
        assert len(errors) == 0
        assert len(results) == 10
        assert all(r is service for r in results)

    def test_thread_safety_registration(self, container):
        """Test thread safety for concurrent registrations."""
        errors = []

        def register_service(index):
            try:
                service = DummyService(f"service_{index}")
                # Use index as a fake type to register different types
                container.register_singleton(f"Service{index}", service)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register_service, args=(i,)) for i in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        assert len(errors) == 0

    def test_factory_with_parameters(self, container):
        """Test factory that creates instances with different parameters."""
        counter = {"value": 0}

        def factory():
            counter["value"] += 1
            return DummyService(f"factory_{counter['value']}")

        container.register_factory(DummyService, factory)

        instance1 = container.get(DummyService)
        instance2 = container.get(DummyService)

        assert instance1.name == "factory_1"
        assert instance2.name == "factory_2"

    def test_override_registration(self, container):
        """Test that re-registering a type overrides the previous registration."""
        service1 = DummyService("first")
        container.register_singleton(DummyService, service1)

        result1 = container.get(DummyService)
        assert result1 is service1

        # Override with new instance
        service2 = DummyService("second")
        container.register_singleton(DummyService, service2)

        result2 = container.get(DummyService)
        assert result2 is service2
        assert result2 is not service1


class TestGlobalContainer:
    """Tests for global container functions."""

    def test_get_container_returns_singleton(self):
        """Test that get_container returns the same instance."""
        reset_container()  # Start fresh

        container1 = get_container()
        container2 = get_container()

        assert container1 is container2

    def test_reset_container(self):
        """Test that reset_container creates new instance."""
        container1 = get_container()
        container1.register_singleton(DummyService, DummyService("test"))

        reset_container()

        container2 = get_container()
        assert container2 is not container1
        assert not container2.is_registered(DummyService)

    def test_global_container_isolation(self):
        """Test that global container is isolated from local containers."""
        reset_container()

        # Register in global container
        global_container = get_container()
        global_service = DummyService("global")
        global_container.register_singleton(DummyService, global_service)

        # Create local container
        local_container = DIContainer()
        local_service = DummyService("local")
        local_container.register_singleton(DummyService, local_service)

        # They should be independent
        assert global_container.get(DummyService) is global_service
        assert local_container.get(DummyService) is local_service
        assert global_service is not local_service


class TestEdgeCases:
    """Edge case tests."""

    def test_none_value_as_singleton(self):
        """Test registering None as a singleton value."""
        container = DIContainer()
        container.register_singleton(type(None), None)

        result = container.get(type(None))
        assert result is None

    def test_lambda_as_factory(self):
        """Test using lambda as factory function."""
        container = DIContainer()
        container.register_factory(str, lambda: "lambda_result")

        result = container.get(str)
        assert result == "lambda_result"

    def test_callable_class_as_factory(self):
        """Test using callable class as factory."""
        class ServiceFactory:
            def __call__(self):
                return DummyService("callable")

        container = DIContainer()
        container.register_factory(DummyService, ServiceFactory())

        result = container.get(DummyService)
        assert isinstance(result, DummyService)
        assert result.name == "callable"

    def test_multiple_types_registered(self):
        """Test registering multiple different types."""
        container = DIContainer()

        service = DummyService()
        container.register_singleton(DummyService, service)
        container.register_factory(str, lambda: "test")
        container.register_transient(int, int)

        assert container.get(DummyService) is service
        assert container.get(str) == "test"
        assert isinstance(container.get(int), int)

    def test_priority_order_singleton_over_factory(self):
        """Test that singleton takes precedence when both are registered."""
        container = DIContainer()

        service = DummyService("singleton")
        container.register_factory(DummyService, lambda: DummyService("factory"))
        container.register_singleton(DummyService, service)

        # Singleton should be returned (checked first)
        result = container.get(DummyService)
        assert result is service
        assert result.name == "singleton"


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_factory_raises_exception(self):
        """Test handling when factory function raises exception."""
        container = DIContainer()

        def failing_factory():
            raise ValueError("Factory failed")

        container.register_factory(DummyService, failing_factory)

        with pytest.raises(ValueError) as exc_info:
            container.get(DummyService)

        assert "Factory failed" in str(exc_info.value)

    def test_transient_class_requires_no_args(self):
        """Test transient class that requires constructor arguments fails."""
        class RequiresArgs:
            def __init__(self, required_arg):
                self.arg = required_arg

        container = DIContainer()
        container.register_transient(RequiresArgs, RequiresArgs)

        # Should fail when trying to instantiate without args
        with pytest.raises(TypeError):
            container.get(RequiresArgs)

    def test_get_after_clear(self):
        """Test that get fails after container is cleared."""
        container = DIContainer()
        service = DummyService()
        container.register_singleton(DummyService, service)

        assert container.get(DummyService) is service

        container.clear()

        with pytest.raises(KeyError):
            container.get(DummyService)
