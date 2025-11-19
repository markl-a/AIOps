"""Plugin System for AIOps

Allows users to extend AIOps functionality with custom plugins.
"""

import importlib
import inspect
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Type, Callable
from pathlib import Path
import sys

from aiops.core.structured_logger import get_structured_logger


logger = get_structured_logger(__name__)


class Plugin(ABC):
    """Base class for all plugins."""

    def __init__(self):
        """Initialize plugin."""
        self.name = self.__class__.__name__
        self.version = "1.0.0"
        self.enabled = True

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the plugin.

        Called when the plugin is loaded.
        """
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the plugin's main functionality.

        Args:
            **kwargs: Plugin-specific arguments

        Returns:
            Plugin execution results
        """
        pass

    async def cleanup(self) -> None:
        """Cleanup resources when plugin is unloaded.

        Optional method that plugins can override.
        """
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """Get plugin metadata.

        Returns:
            Plugin metadata dictionary
        """
        return {
            "name": self.name,
            "version": self.version,
            "enabled": self.enabled,
            "description": self.__doc__ or "No description available",
        }


class AgentPlugin(Plugin):
    """Base class for agent plugins.

    Agent plugins can add new AI agents to the system.
    """

    @abstractmethod
    def get_agent_type(self) -> str:
        """Get the agent type identifier.

        Returns:
            Agent type string
        """
        pass

    @abstractmethod
    async def analyze(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze input using the agent.

        Args:
            input_data: Input data for analysis

        Returns:
            Analysis results
        """
        pass

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute agent analysis."""
        return await self.analyze(kwargs.get("input_data", {}))


class IntegrationPlugin(Plugin):
    """Base class for integration plugins.

    Integration plugins can add support for new external services.
    """

    @abstractmethod
    def get_integration_name(self) -> str:
        """Get the integration name.

        Returns:
            Integration name string
        """
        pass

    @abstractmethod
    async def send_notification(self, message: Dict[str, Any]) -> bool:
        """Send notification via this integration.

        Args:
            message: Message to send

        Returns:
            True if successful
        """
        pass

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute integration action."""
        action = kwargs.get("action", "send_notification")

        if action == "send_notification":
            success = await self.send_notification(kwargs.get("message", {}))
            return {"success": success}

        return {"error": f"Unknown action: {action}"}


class PluginManager:
    """Manages plugin loading, execution, and lifecycle."""

    def __init__(self):
        """Initialize plugin manager."""
        self.plugins: Dict[str, Plugin] = {}
        self.plugin_paths: List[Path] = []

    def add_plugin_path(self, path: Path):
        """Add a directory to search for plugins.

        Args:
            path: Path to plugin directory
        """
        if path.exists() and path.is_dir():
            self.plugin_paths.append(path)
            if str(path) not in sys.path:
                sys.path.insert(0, str(path))

            logger.info(f"Added plugin path: {path}")
        else:
            logger.warning(f"Plugin path does not exist: {path}")

    async def load_plugin(self, plugin_class: Type[Plugin]) -> bool:
        """Load and initialize a plugin.

        Args:
            plugin_class: Plugin class to load

        Returns:
            True if loaded successfully
        """
        try:
            plugin = plugin_class()
            await plugin.initialize()

            self.plugins[plugin.name] = plugin

            logger.info(
                f"Loaded plugin: {plugin.name}",
                plugin_name=plugin.name,
                version=plugin.version,
            )

            return True

        except Exception as e:
            logger.error(
                f"Failed to load plugin: {str(e)}",
                plugin_class=plugin_class.__name__,
                error=str(e),
            )
            return False

    async def load_plugin_from_module(self, module_name: str) -> bool:
        """Load plugin from a Python module.

        Args:
            module_name: Python module name (e.g., 'my_plugin')

        Returns:
            True if loaded successfully
        """
        try:
            module = importlib.import_module(module_name)

            # Find all Plugin subclasses in the module
            plugin_classes = []
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, Plugin) and
                    obj != Plugin and
                    obj != AgentPlugin and
                    obj != IntegrationPlugin):
                    plugin_classes.append(obj)

            if not plugin_classes:
                logger.warning(f"No plugin classes found in module: {module_name}")
                return False

            # Load all plugin classes
            for plugin_class in plugin_classes:
                await self.load_plugin(plugin_class)

            return True

        except Exception as e:
            logger.error(
                f"Failed to load module: {module_name}",
                error=str(e),
            )
            return False

    async def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin.

        Args:
            plugin_name: Name of plugin to unload

        Returns:
            True if unloaded successfully
        """
        if plugin_name not in self.plugins:
            logger.warning(f"Plugin not found: {plugin_name}")
            return False

        plugin = self.plugins[plugin_name]

        try:
            await plugin.cleanup()
            del self.plugins[plugin_name]

            logger.info(f"Unloaded plugin: {plugin_name}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to unload plugin: {plugin_name}",
                error=str(e),
            )
            return False

    async def execute_plugin(
        self,
        plugin_name: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Execute a plugin.

        Args:
            plugin_name: Name of plugin to execute
            **kwargs: Plugin-specific arguments

        Returns:
            Plugin execution results

        Raises:
            KeyError: If plugin not found
            Exception: If plugin execution fails
        """
        if plugin_name not in self.plugins:
            raise KeyError(f"Plugin not found: {plugin_name}")

        plugin = self.plugins[plugin_name]

        if not plugin.enabled:
            return {
                "error": f"Plugin {plugin_name} is disabled",
                "success": False,
            }

        try:
            logger.info(f"Executing plugin: {plugin_name}")
            result = await plugin.execute(**kwargs)
            return result

        except Exception as e:
            logger.error(
                f"Plugin execution failed: {plugin_name}",
                error=str(e),
            )
            raise

    def get_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """Get a plugin by name.

        Args:
            plugin_name: Plugin name

        Returns:
            Plugin instance or None
        """
        return self.plugins.get(plugin_name)

    def list_plugins(
        self,
        plugin_type: Optional[Type[Plugin]] = None,
    ) -> List[Dict[str, Any]]:
        """List all loaded plugins.

        Args:
            plugin_type: Filter by plugin type

        Returns:
            List of plugin metadata
        """
        plugins = []

        for plugin in self.plugins.values():
            if plugin_type is None or isinstance(plugin, plugin_type):
                plugins.append(plugin.get_metadata())

        return plugins

    def enable_plugin(self, plugin_name: str) -> bool:
        """Enable a plugin.

        Args:
            plugin_name: Plugin name

        Returns:
            True if enabled successfully
        """
        if plugin_name in self.plugins:
            self.plugins[plugin_name].enabled = True
            logger.info(f"Enabled plugin: {plugin_name}")
            return True

        return False

    def disable_plugin(self, plugin_name: str) -> bool:
        """Disable a plugin.

        Args:
            plugin_name: Plugin name

        Returns:
            True if disabled successfully
        """
        if plugin_name in self.plugins:
            self.plugins[plugin_name].enabled = False
            logger.info(f"Disabled plugin: {plugin_name}")
            return True

        return False


# Global plugin manager instance
_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """Get the global plugin manager instance.

    Returns:
        Plugin manager instance
    """
    global _plugin_manager

    if _plugin_manager is None:
        _plugin_manager = PluginManager()

    return _plugin_manager


def plugin(
    name: Optional[str] = None,
    version: str = "1.0.0",
):
    """Decorator to register a plugin class.

    Args:
        name: Plugin name (defaults to class name)
        version: Plugin version

    Example:
        @plugin(name="my_agent", version="1.0.0")
        class MyAgentPlugin(AgentPlugin):
            pass
    """
    def decorator(cls):
        # Set plugin metadata
        if name:
            cls._plugin_name = name
        cls._plugin_version = version

        return cls

    return decorator
