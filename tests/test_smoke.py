"""Smoke tests to verify core components can be instantiated."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_import_core_modules():
    """Test that core modules can be imported."""
    try:
        from aiops.core.config import Config
        from aiops.core.cache import CacheManager
        from aiops.agents.registry import agent_registry
        print("✓ Core modules imported successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to import core modules: {e}")
        return False


def test_instantiate_cache_manager():
    """Test that CacheManager can be instantiated."""
    try:
        from aiops.core.cache import CacheManager
        cache = CacheManager()
        print("✓ CacheManager instantiated successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to instantiate CacheManager: {e}")
        return False


def test_agent_registry():
    """Test that agent registry is accessible."""
    try:
        from aiops.agents.registry import agent_registry
        agents = agent_registry.list_agents()
        print(f"✓ Agent registry accessible with {len(agents)} agents")
        return True
    except Exception as e:
        print(f"✗ Failed to access agent registry: {e}")
        return False


def test_config():
    """Test that Config can be loaded."""
    try:
        from aiops.core.config import Config
        # Set minimal required env vars
        os.environ.setdefault("OPENAI_API_KEY", "test-key")
        config = Config()
        print("✓ Config loaded successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to load config: {e}")
        return False


def test_list_available_agents():
    """Test listing available agents."""
    try:
        from aiops.agents.registry import agent_registry
        agents = agent_registry.list_agents()

        print("\nAvailable Agents:")
        for agent in agents:
            print(f"  - {agent.name}: {agent.description}")

        # Check that we have expected agents
        expected_agents = ['code_reviewer', 'test_generator', 'log_analyzer']
        agent_names = [a.name for a in agents]

        for expected in expected_agents:
            if expected in agent_names:
                print(f"✓ Found expected agent: {expected}")
            else:
                print(f"✗ Missing expected agent: {expected}")

        return True
    except Exception as e:
        print(f"✗ Failed to list agents: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("AIOPS SMOKE TESTS")
    print("=" * 60)

    tests = [
        ("Import Core Modules", test_import_core_modules),
        ("Instantiate CacheManager", test_instantiate_cache_manager),
        ("Access Agent Registry", test_agent_registry),
        ("Load Config", test_config),
        ("List Available Agents", test_list_available_agents),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 60)
        result = test_func()
        results.append(result)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("✓ All smoke tests passed!")
        sys.exit(0)
    else:
        print(f"✗ {total - passed} smoke test(s) failed")
        sys.exit(1)
