"""Plugin System for AIOps

Extend AIOps functionality with custom plugins.
"""

from aiops.plugins.plugin_system import (
    Plugin,
    AgentPlugin,
    IntegrationPlugin,
    PluginManager,
    get_plugin_manager,
    plugin,
)

__all__ = [
    "Plugin",
    "AgentPlugin",
    "IntegrationPlugin",
    "PluginManager",
    "get_plugin_manager",
    "plugin",
]
