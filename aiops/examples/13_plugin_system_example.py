"""Example 13: Plugin System

This example demonstrates how to create and use custom plugins to extend
AIOps functionality.
"""

import asyncio
from typing import Dict, Any

from aiops.plugins import (
    Plugin,
    AgentPlugin,
    IntegrationPlugin,
    PluginManager,
    get_plugin_manager,
    plugin,
)


# Example 1: Simple Plugin
class HelloWorldPlugin(Plugin):
    """A simple hello world plugin."""

    async def initialize(self):
        """Initialize plugin."""
        print(f"  🔌 Initializing {self.name}...")
        self.version = "1.0.0"

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute plugin."""
        name = kwargs.get("name", "World")
        message = f"Hello, {name}! from {self.name}"

        return {
            "message": message,
            "success": True,
        }


# Example 2: Agent Plugin
@plugin(name="custom_code_analyzer", version="1.0.0")
class CustomCodeAnalyzerPlugin(AgentPlugin):
    """Custom code analysis agent plugin."""

    async def initialize(self):
        """Initialize agent."""
        print(f"  🤖 Initializing {self.get_agent_type()} agent...")
        self.version = "1.0.0"

    def get_agent_type(self) -> str:
        """Get agent type."""
        return "custom_code_analyzer"

    async def analyze(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze code."""
        code = input_data.get("code", "")

        # Simple analysis
        analysis = {
            "lines": len(code.split("\n")),
            "characters": len(code),
            "contains_todo": "TODO" in code,
            "contains_fixme": "FIXME" in code,
        }

        recommendations = []
        if analysis["contains_todo"]:
            recommendations.append("Found TODO comments - consider addressing them")
        if analysis["contains_fixme"]:
            recommendations.append("Found FIXME comments - critical issues to fix")

        return {
            "analysis": analysis,
            "recommendations": recommendations,
            "score": 85.0,
        }


# Example 3: Integration Plugin
class DiscordPlugin(IntegrationPlugin):
    """Discord webhook integration plugin."""

    def __init__(self):
        super().__init__()
        self.webhook_url = None

    async def initialize(self):
        """Initialize Discord integration."""
        print(f"  💬 Initializing {self.get_integration_name()} integration...")
        # In production, load webhook URL from config
        self.webhook_url = "https://discord.com/api/webhooks/..."

    def get_integration_name(self) -> str:
        """Get integration name."""
        return "discord"

    async def send_notification(self, message: Dict[str, Any]) -> bool:
        """Send notification to Discord."""
        # Mock implementation
        print(f"    📨 Sending to Discord: {message.get('title', 'Notification')}")

        # In production, send actual webhook request
        # async with aiohttp.ClientSession() as session:
        #     await session.post(self.webhook_url, json=message)

        return True


# Example 4: Advanced Plugin with Lifecycle
class DataProcessorPlugin(Plugin):
    """Plugin that processes data with full lifecycle management."""

    def __init__(self):
        super().__init__()
        self.cache = {}
        self.stats = {
            "total_processed": 0,
            "total_errors": 0,
        }

    async def initialize(self):
        """Initialize data processor."""
        print(f"  📊 Initializing {self.name}...")
        print(f"    Setting up cache and statistics...")
        self.cache = {}
        self.stats = {
            "total_processed": 0,
            "total_errors": 0,
        }

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Process data."""
        data = kwargs.get("data", [])

        try:
            # Process data
            processed = [item.upper() if isinstance(item, str) else item for item in data]

            # Update stats
            self.stats["total_processed"] += len(processed)

            # Cache result
            cache_key = str(data)
            self.cache[cache_key] = processed

            return {
                "processed": processed,
                "count": len(processed),
                "stats": self.stats.copy(),
                "success": True,
            }

        except Exception as e:
            self.stats["total_errors"] += 1
            return {
                "error": str(e),
                "stats": self.stats.copy(),
                "success": False,
            }

    async def cleanup(self):
        """Cleanup resources."""
        print(f"  🧹 Cleaning up {self.name}...")
        print(f"    Processed: {self.stats['total_processed']}")
        print(f"    Errors: {self.stats['total_errors']}")
        print(f"    Clearing cache...")
        self.cache.clear()


async def basic_plugin_usage():
    """Demonstrate basic plugin usage."""

    print("🔌 Basic Plugin Usage")
    print("="*60)

    manager = PluginManager()

    # Load plugin
    print("\n1️⃣  Loading HelloWorldPlugin...")
    await manager.load_plugin(HelloWorldPlugin)

    # List plugins
    print("\n2️⃣  Loaded Plugins:")
    for plugin_info in manager.list_plugins():
        print(f"  • {plugin_info['name']} v{plugin_info['version']}")
        print(f"    {plugin_info['description']}")

    # Execute plugin
    print("\n3️⃣  Executing Plugin:")
    result = await manager.execute_plugin(
        "HelloWorldPlugin",
        name="AIOps User",
    )
    print(f"  Result: {result['message']}")

    # Unload plugin
    print("\n4️⃣  Unloading Plugin...")
    await manager.unload_plugin("HelloWorldPlugin")
    print("  ✅ Plugin unloaded")


async def agent_plugin_example():
    """Demonstrate agent plugin."""

    print("\n\n🤖 Agent Plugin Example")
    print("="*60)

    manager = PluginManager()

    # Load agent plugin
    print("\n1️⃣  Loading CustomCodeAnalyzerPlugin...")
    await manager.load_plugin(CustomCodeAnalyzerPlugin)

    # Execute analysis
    print("\n2️⃣  Analyzing Code:")
    code_sample = """
def calculate_total(items):
    # TODO: Add validation
    # FIXME: Handle negative values
    total = sum(items)
    return total
"""

    result = await manager.execute_plugin(
        "CustomCodeAnalyzerPlugin",
        input_data={"code": code_sample},
    )

    print(f"\n  📊 Analysis Results:")
    print(f"    Lines: {result['analysis']['lines']}")
    print(f"    Characters: {result['analysis']['characters']}")
    print(f"    Score: {result['score']}")

    if result['recommendations']:
        print(f"\n  💡 Recommendations:")
        for rec in result['recommendations']:
            print(f"    • {rec}")


async def integration_plugin_example():
    """Demonstrate integration plugin."""

    print("\n\n💬 Integration Plugin Example")
    print("="*60)

    manager = PluginManager()

    # Load integration plugin
    print("\n1️⃣  Loading DiscordPlugin...")
    await manager.load_plugin(DiscordPlugin)

    # Send notification
    print("\n2️⃣  Sending Notification:")
    result = await manager.execute_plugin(
        "DiscordPlugin",
        action="send_notification",
        message={
            "title": "Deployment Complete",
            "description": "Application deployed successfully to production",
            "color": "#00ff00",
        },
    )

    print(f"  ✅ Notification sent: {result['success']}")


async def lifecycle_management_example():
    """Demonstrate plugin lifecycle management."""

    print("\n\n♻️  Plugin Lifecycle Management")
    print("="*60)

    manager = PluginManager()

    # Load plugin
    print("\n1️⃣  Loading DataProcessorPlugin...")
    await manager.load_plugin(DataProcessorPlugin)

    # Execute multiple times
    print("\n2️⃣  Processing Data (3 batches):")
    for i in range(3):
        data = [f"item_{j}" for j in range(5)]
        result = await manager.execute_plugin(
            "DataProcessorPlugin",
            data=data,
        )
        print(f"  Batch {i+1}: Processed {result['count']} items")

    # Get stats
    plugin = manager.get_plugin("DataProcessorPlugin")
    print(f"\n  📊 Total Stats:")
    print(f"    Total Processed: {plugin.stats['total_processed']}")
    print(f"    Total Errors: {plugin.stats['total_errors']}")

    # Cleanup
    print("\n3️⃣  Unloading Plugin (triggers cleanup)...")
    await manager.unload_plugin("DataProcessorPlugin")


async def plugin_enable_disable_example():
    """Demonstrate enabling/disabling plugins."""

    print("\n\n🎚️  Enable/Disable Plugins")
    print("="*60)

    manager = PluginManager()

    # Load plugin
    await manager.load_plugin(HelloWorldPlugin)

    # Execute (should work)
    print("\n1️⃣  Execute with Plugin Enabled:")
    result = await manager.execute_plugin("HelloWorldPlugin", name="Test 1")
    print(f"  ✅ {result['message']}")

    # Disable plugin
    print("\n2️⃣  Disabling Plugin...")
    manager.disable_plugin("HelloWorldPlugin")
    print("  Plugin disabled")

    # Try to execute (should fail gracefully)
    print("\n3️⃣  Execute with Plugin Disabled:")
    result = await manager.execute_plugin("HelloWorldPlugin", name="Test 2")
    print(f"  ⚠️  {result.get('error', 'Unknown error')}")

    # Re-enable plugin
    print("\n4️⃣  Re-enabling Plugin...")
    manager.enable_plugin("HelloWorldPlugin")
    print("  Plugin re-enabled")

    # Execute again (should work)
    print("\n5️⃣  Execute with Plugin Re-enabled:")
    result = await manager.execute_plugin("HelloWorldPlugin", name="Test 3")
    print(f"  ✅ {result['message']}")


async def create_custom_plugin_tutorial():
    """Show how to create a custom plugin."""

    print("\n\n📚 Creating Custom Plugins Tutorial")
    print("="*60)

    print("\n1️⃣  Simple Plugin:")
    print("""
from aiops.plugins import Plugin

class MyPlugin(Plugin):
    async def initialize(self):
        self.version = "1.0.0"
        # Initialize resources

    async def execute(self, **kwargs):
        # Plugin logic here
        return {"result": "success"}

    async def cleanup(self):
        # Cleanup resources
        pass
""")

    print("\n2️⃣  Agent Plugin:")
    print("""
from aiops.plugins import AgentPlugin

class MyAgentPlugin(AgentPlugin):
    async def initialize(self):
        self.version = "1.0.0"

    def get_agent_type(self) -> str:
        return "my_agent"

    async def analyze(self, input_data):
        # Analysis logic
        return {"analysis": "results"}
""")

    print("\n3️⃣  Integration Plugin:")
    print("""
from aiops.plugins import IntegrationPlugin

class MyIntegrationPlugin(IntegrationPlugin):
    async def initialize(self):
        self.api_key = load_from_env("MY_API_KEY")

    def get_integration_name(self) -> str:
        return "my_service"

    async def send_notification(self, message):
        # Send to external service
        return True
""")

    print("\n4️⃣  Using the Plugin:")
    print("""
from aiops.plugins import get_plugin_manager

manager = get_plugin_manager()
await manager.load_plugin(MyPlugin)
result = await manager.execute_plugin("MyPlugin", arg1="value")
""")


if __name__ == "__main__":
    print("🔌 Plugin System Examples")
    print("="*60)

    # Run examples
    asyncio.run(basic_plugin_usage())
    asyncio.run(agent_plugin_example())
    asyncio.run(integration_plugin_example())
    asyncio.run(lifecycle_management_example())
    asyncio.run(plugin_enable_disable_example())
    asyncio.run(create_custom_plugin_tutorial())

    print("\n\n" + "="*60)
    print("✅ All plugin examples complete!")
    print("="*60)

    print("\n📚 Next Steps:")
    print("  1. Create your own plugins")
    print("  2. Add custom agents")
    print("  3. Integrate new services")
    print("  4. Extend AIOps functionality")
    print("\n")
