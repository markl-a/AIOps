"""Example 11: LLM Provider Failover Mechanism

This example demonstrates how to use multiple LLM providers with automatic
failover for high availability.
"""

import asyncio
import os
from datetime import datetime

from aiops.core.llm_providers import (
    LLMProviderManager,
    OpenAIProvider,
    AnthropicProvider,
    GoogleProvider,
    ProviderStatus,
)
from aiops.core.llm_config import (
    LLMConfig,
    ProviderConfig,
    ProviderType,
    create_llm_manager_from_config,
    load_config_from_env,
    get_example_config,
)
from aiops.core.exceptions import LLMProviderError


async def basic_failover_example():
    """Basic example of failover between providers."""

    print("🔄 Basic LLM Provider Failover")
    print("="*60)

    # Note: Replace with real API keys
    openai_key = os.getenv("OPENAI_API_KEY", "your-openai-key")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "your-anthropic-key")

    # Create providers in priority order
    providers = [
        OpenAIProvider(openai_key),      # Primary
        AnthropicProvider(anthropic_key),  # Fallback
    ]

    manager = LLMProviderManager(providers)

    print("\n📋 Provider Configuration:")
    print(f"  1. OpenAI (Primary)")
    print(f"  2. Anthropic (Fallback)")

    # Generate text
    try:
        print("\n🤖 Generating text...")
        result, provider_name = await manager.generate(
            prompt="Explain what is AIOps in one sentence.",
            max_tokens=100,
        )

        print(f"\n✅ Success!")
        print(f"  Provider used: {provider_name}")
        print(f"  Response: {result}")

    except LLMProviderError as e:
        print(f"\n❌ All providers failed: {e}")


async def configuration_based_setup():
    """Example using configuration-based setup."""

    print("\n\n⚙️  Configuration-Based Setup")
    print("="*60)

    # Create configuration
    config = LLMConfig(
        providers=[
            ProviderConfig(
                type=ProviderType.OPENAI,
                api_key_env="OPENAI_API_KEY",
                priority=3,  # Highest priority
                max_retries=3,
                timeout=30.0,
            ),
            ProviderConfig(
                type=ProviderType.ANTHROPIC,
                api_key_env="ANTHROPIC_API_KEY",
                priority=2,  # Second priority
                max_retries=3,
                timeout=30.0,
            ),
            ProviderConfig(
                type=ProviderType.GOOGLE,
                api_key_env="GOOGLE_API_KEY",
                priority=1,  # Lowest priority
                max_retries=2,
                timeout=20.0,
            ),
        ],
        failover_enabled=True,
        health_check_interval=60,
    )

    print("\n📊 Configuration:")
    for provider in config.get_sorted_providers():
        print(f"  {provider.priority}. {provider.type.upper()}")
        print(f"     Max Retries: {provider.max_retries}")
        print(f"     Timeout: {provider.timeout}s")

    # Create manager from config
    try:
        manager = create_llm_manager_from_config(config)
        print(f"\n✅ Manager created with {len(manager.providers)} providers")

        # Generate text
        result, provider_name = await manager.generate(
            prompt="What are the benefits of multi-cloud strategy?",
            max_tokens=150,
        )

        print(f"\n📝 Response from {provider_name}:")
        print(f"  {result}")

    except Exception as e:
        print(f"\n⚠️  Error: {e}")


async def health_monitoring_example():
    """Example of health monitoring and statistics."""

    print("\n\n🏥 Health Monitoring")
    print("="*60)

    # Load config from environment
    try:
        config = load_config_from_env()
        manager = create_llm_manager_from_config(config)

        # Run health checks
        print("\n🔍 Running health checks...")
        health_results = await manager.health_check_all()

        print("\n📊 Health Check Results:")
        for provider_name, is_healthy in health_results.items():
            status = "✅ Healthy" if is_healthy else "❌ Unhealthy"
            print(f"  {provider_name}: {status}")

        # Get provider statistics
        print("\n\n📈 Provider Statistics:")
        stats = await manager.get_provider_stats()

        for stat in stats:
            print(f"\n  {stat['name'].upper()}:")
            print(f"    Status: {stat['status']}")
            print(f"    Total Requests: {stat['total_requests']}")
            print(f"    Successful: {stat['successful_requests']}")
            print(f"    Success Rate: {stat['success_rate']:.2%}")
            print(f"    Consecutive Failures: {stat['failure_count']}")

            if stat['last_success']:
                print(f"    Last Success: {stat['last_success']}")
            if stat['last_failure']:
                print(f"    Last Failure: {stat['last_failure']}")

        # Get healthy providers
        healthy_providers = manager.get_healthy_providers()
        print(f"\n\n💚 Healthy Providers: {len(healthy_providers)}")
        for provider in healthy_providers:
            print(f"  • {provider.name}")

    except Exception as e:
        print(f"\n⚠️  Error: {e}")


async def simulate_failover_scenario():
    """Simulate a failover scenario."""

    print("\n\n🎯 Simulated Failover Scenario")
    print("="*60)

    print("\n📋 Scenario: Primary provider fails, system auto-fails over")

    # Create mock providers for simulation
    from aiops.core.llm_providers import LLMProvider

    class SimulatedProvider(LLMProvider):
        """Simulated provider for testing."""

        def __init__(self, name: str, will_fail: bool = False):
            super().__init__(name, "mock-key")
            self.will_fail = will_fail
            self.call_count = 0

        async def generate(self, prompt: str, **kwargs) -> str:
            self.call_count += 1
            print(f"\n  🔄 Attempting with {self.name}...")

            if self.will_fail:
                await self.record_failure(
                    LLMProviderError(f"{self.name} is unavailable")
                )
                raise LLMProviderError(f"{self.name} failed")

            await self.record_success()
            return f"Response from {self.name}"

        async def health_check(self) -> bool:
            return not self.will_fail

    # Create providers
    primary = SimulatedProvider("Primary-Provider", will_fail=True)
    secondary = SimulatedProvider("Secondary-Provider", will_fail=False)
    tertiary = SimulatedProvider("Tertiary-Provider", will_fail=False)

    manager = LLMProviderManager([primary, secondary, tertiary])

    # Attempt generation
    print("\n🚀 Starting request...")
    try:
        result, provider_name = await manager.generate(
            prompt="Test prompt",
            max_tokens=100,
        )

        print(f"\n✅ Request successful!")
        print(f"  Final Provider: {provider_name}")
        print(f"  Response: {result}")

        print(f"\n📊 Call Statistics:")
        print(f"  Primary Provider: {primary.call_count} attempts")
        print(f"  Secondary Provider: {secondary.call_count} attempts")
        print(f"  Tertiary Provider: {tertiary.call_count} attempts")

    except LLMProviderError as e:
        print(f"\n❌ All providers failed: {e}")


async def rate_limiting_handling():
    """Example of handling rate limiting."""

    print("\n\n⏱️  Rate Limiting Handling")
    print("="*60)

    print("\n📋 When a provider hits rate limits, the system automatically:")
    print("  1. Marks the provider as RATE_LIMITED")
    print("  2. Skips that provider for 5 minutes")
    print("  3. Uses the next available provider")
    print("  4. Continues to monitor provider health")

    # Simulated example
    print("\n🎬 Simulation:")
    print("\n  T+0s:  OpenAI request succeeds")
    print("  T+1s:  OpenAI hits rate limit")
    print("  T+1s:  System marks OpenAI as RATE_LIMITED")
    print("  T+2s:  Request automatically routed to Anthropic")
    print("  T+2s:  Anthropic request succeeds")
    print("  T+5m:  OpenAI becomes available again")
    print("  T+5m:  System resumes using OpenAI")

    print("\n💡 Configuration:")
    print("""
# In your config
config = LLMConfig(
    providers=[
        ProviderConfig(
            type=ProviderType.OPENAI,
            priority=2,
            max_retries=3,  # Retry on transient failures
        ),
        ProviderConfig(
            type=ProviderType.ANTHROPIC,
            priority=1,  # Fallback
        ),
    ],
    failover_enabled=True,
)
""")


async def best_practices_example():
    """Show best practices for production deployment."""

    print("\n\n💡 Production Best Practices")
    print("="*60)

    print("\n1️⃣  Always Configure Multiple Providers:")
    print("""
# Recommended: At least 2 providers
providers = [
    OpenAIProvider(api_key),      # Primary
    AnthropicProvider(api_key),   # Fallback
]
""")

    print("\n2️⃣  Set Appropriate Timeouts:")
    print("""
# Prevent long waits on failing providers
ProviderConfig(
    type=ProviderType.OPENAI,
    timeout=30.0,  # 30 seconds max
    max_retries=3,
)
""")

    print("\n3️⃣  Monitor Provider Health:")
    print("""
# Regularly check provider health
async def monitor_loop():
    while True:
        await manager.health_check_all()
        await asyncio.sleep(60)  # Every minute

# Start background monitoring
asyncio.create_task(monitor_loop())
""")

    print("\n4️⃣  Track Metrics:")
    print("""
# Monitor provider performance
stats = await manager.get_provider_stats()

# Alert on low success rate
for stat in stats:
    if stat['success_rate'] < 0.95:
        send_alert(f"Provider {stat['name']} degraded")
""")

    print("\n5️⃣  Handle Errors Gracefully:")
    print("""
try:
    result, provider = await manager.generate(prompt)
except LLMProviderError as e:
    # All providers failed
    logger.error(f"LLM generation failed: {e}")
    # Fallback to cached response or queue for retry
    return get_cached_or_queue(prompt)
""")

    print("\n6️⃣  Use Environment Variables for API Keys:")
    print("""
# Never hardcode API keys
config = ProviderConfig(
    type=ProviderType.OPENAI,
    api_key_env="OPENAI_API_KEY",  # Load from env
)
""")


async def cost_optimization_example():
    """Example of using cheaper models as fallback."""

    print("\n\n💰 Cost Optimization Strategy")
    print("="*60)

    print("\n📊 Strategy: Use cheaper models as fallback")

    print("\nPrimary Provider (OpenAI GPT-4):")
    print("  • Cost: $0.03/1K tokens")
    print("  • Quality: Highest")
    print("  • Speed: Moderate")

    print("\nFallback Provider (OpenAI GPT-3.5):")
    print("  • Cost: $0.002/1K tokens (15x cheaper)")
    print("  • Quality: Good")
    print("  • Speed: Fast")

    print("\nImplementation:")
    print("""
# Different models as fallback
providers = [
    OpenAIProvider(api_key),  # Will use GPT-4
    OpenAIProvider(api_key),  # Will use GPT-3.5 as fallback
]

# Specify model in generate call
result, provider = await manager.generate(
    prompt="...",
    model="gpt-4-turbo-preview",  # Try GPT-4 first
)

# If GPT-4 fails, automatically falls back to GPT-3.5
""")


if __name__ == "__main__":
    print("🔄 LLM Provider Failover Examples")
    print("="*60)

    # Run examples
    print("\nNOTE: These examples require valid API keys.")
    print("Set environment variables: OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.\n")

    # Simulated examples (no API keys needed)
    asyncio.run(simulate_failover_scenario())

    asyncio.run(rate_limiting_handling())

    asyncio.run(best_practices_example())

    asyncio.run(cost_optimization_example())

    # Real examples (require API keys)
    # Uncomment to run with real API keys
    # asyncio.run(basic_failover_example())
    # asyncio.run(configuration_based_setup())
    # asyncio.run(health_monitoring_example())

    print("\n✅ All failover examples complete!\n")
