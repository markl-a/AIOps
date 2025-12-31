"""Dependency Injection Container for AIOps.

This module provides a simple dependency injection container for managing
service dependencies across the application.
"""

from typing import Any, Callable, Dict, Optional, Type, TypeVar
from threading import Lock
from aiops.core.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class DIContainer:
    """Simple dependency injection container.

    Supports:
    - Singleton instances (shared across app)
    - Factory functions (create new instance each time)
    - Transient instances (new instance each time)

    Example:
        # Register services
        container = DIContainer()
        container.register_singleton(Database, database_instance)
        container.register_factory(UserService, lambda: UserService(container.get(Database)))

        # Resolve dependencies
        db = container.get(Database)
        user_service = container.get(UserService)
    """

    def __init__(self):
        """Initialize the container."""
        self._singletons: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}
        self._transient: Dict[Type, Type] = {}
        self._lock = Lock()
        logger.debug("Initialized DI Container")

    def register_singleton(self, interface: Type[T], instance: T) -> None:
        """Register a singleton instance.

        Args:
            interface: The interface/type to register
            instance: The singleton instance
        """
        with self._lock:
            self._singletons[interface] = instance
            logger.debug(f"Registered singleton: {interface.__name__}")

    def register_factory(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """Register a factory function.

        Args:
            interface: The interface/type to register
            factory: Factory function that creates instances
        """
        with self._lock:
            self._factories[interface] = factory
            logger.debug(f"Registered factory: {interface.__name__}")

    def register_transient(self, interface: Type[T], implementation: Type[T]) -> None:
        """Register a transient type (new instance each time).

        Args:
            interface: The interface/type to register
            implementation: The implementation class
        """
        with self._lock:
            self._transient[interface] = implementation
            logger.debug(f"Registered transient: {interface.__name__}")

    def get(self, interface: Type[T]) -> T:
        """Resolve and return an instance.

        Args:
            interface: The interface/type to resolve

        Returns:
            Instance of the requested type

        Raises:
            KeyError: If type is not registered
        """
        # Check singletons first
        if interface in self._singletons:
            return self._singletons[interface]

        # Check factories
        if interface in self._factories:
            factory = self._factories[interface]
            instance = factory()
            logger.debug(f"Created instance via factory: {interface.__name__}")
            return instance

        # Check transient
        if interface in self._transient:
            implementation = self._transient[interface]
            instance = implementation()
            logger.debug(f"Created transient instance: {interface.__name__}")
            return instance

        raise KeyError(f"No registration found for type: {interface.__name__}")

    def try_get(self, interface: Type[T]) -> Optional[T]:
        """Try to resolve an instance, return None if not registered.

        Args:
            interface: The interface/type to resolve

        Returns:
            Instance or None if not registered
        """
        try:
            return self.get(interface)
        except KeyError:
            return None

    def is_registered(self, interface: Type) -> bool:
        """Check if a type is registered.

        Args:
            interface: The interface/type to check

        Returns:
            True if registered, False otherwise
        """
        return (
            interface in self._singletons
            or interface in self._factories
            or interface in self._transient
        )

    def clear(self) -> None:
        """Clear all registrations."""
        with self._lock:
            self._singletons.clear()
            self._factories.clear()
            self._transient.clear()
            logger.info("Cleared all DI registrations")

    def get_registrations(self) -> Dict[str, int]:
        """Get statistics about registrations.

        Returns:
            Dictionary with counts of each registration type
        """
        return {
            "singletons": len(self._singletons),
            "factories": len(self._factories),
            "transient": len(self._transient),
            "total": len(self._singletons) + len(self._factories) + len(self._transient),
        }


# Global container instance
_container: Optional[DIContainer] = None
_container_lock = Lock()


def get_container() -> DIContainer:
    """Get the global DI container instance.

    Returns:
        Global DIContainer instance
    """
    global _container
    if _container is None:
        with _container_lock:
            if _container is None:
                _container = DIContainer()
                logger.info("Created global DI container")
    return _container


def reset_container() -> None:
    """Reset the global DI container (mainly for testing)."""
    global _container
    with _container_lock:
        _container = None
        logger.info("Reset global DI container")
