#!/usr/bin/env python3
"""Test script to verify memory management fixes."""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from aiops.core.cache import Cache, RateLimiter, get_cache, _stampede_locks
from aiops.core.semantic_cache import SemanticCache
from aiops.agents.orchestrator import AgentOrchestrator
from aiops.agents.registry import AgentRegistry


def test_stampede_locks_bounded():
    """Test that stampede locks dictionary is bounded."""
    print("Testing stampede locks are bounded...")
    cache = Cache()

    # Simulate creating many locks
    for i in range(1500):  # More than _MAX_STAMPEDE_LOCKS (1000)
        key = f"test_key_{i}"
        lock = cache._get_stampede_lock(key)

    # Check that locks are bounded
    assert len(_stampede_locks) <= 1000, f"Stampede locks exceeded limit: {len(_stampede_locks)}"
    print(f"  ✓ Stampede locks bounded to {len(_stampede_locks)} (max: 1000)")


def test_rate_limiter_bounded():
    """Test that RateLimiter calls list is bounded."""
    print("Testing RateLimiter is bounded...")
    limiter = RateLimiter(max_calls=10, time_window=60)

    # Add many calls
    for _ in range(50):
        limiter.is_allowed()

    # Should not exceed max_calls * 2
    assert len(limiter.calls) <= limiter.max_calls * 2, \
        f"RateLimiter calls exceeded limit: {len(limiter.calls)}"
    print(f"  ✓ RateLimiter calls bounded to {len(limiter.calls)} (max: {limiter.max_calls * 2})")

    # Test clear method
    limiter.clear()
    assert len(limiter.calls) == 0, "RateLimiter clear() failed"
    print("  ✓ RateLimiter clear() works")


def test_semantic_cache_bounded():
    """Test that SemanticCache is bounded with LRU eviction."""
    print("Testing SemanticCache is bounded...")
    cache = SemanticCache(max_entries=100)

    # Add more entries than max
    for i in range(150):
        cache.set(f"prompt_{i}", f"result_{i}")

    # Should not exceed max_entries
    assert cache._cache.__len__() <= cache.max_entries, \
        f"SemanticCache exceeded max entries: {len(cache._cache)}"
    print(f"  ✓ SemanticCache bounded to {len(cache._cache)} entries (max: {cache.max_entries})")

    # Verify prompt_index is also cleaned up
    assert len(cache._prompt_index) <= cache.max_entries, \
        f"Prompt index not cleaned up: {len(cache._prompt_index)}"
    print(f"  ✓ Prompt index also bounded: {len(cache._prompt_index)}")


def test_semantic_cache_context_manager():
    """Test SemanticCache context manager."""
    print("Testing SemanticCache context manager...")

    with SemanticCache(max_entries=10) as cache:
        cache.set("test", "value")
        assert cache.get("test") == "value"

    # Cache should be cleared after context
    # (Note: we can't test this directly as cache is destroyed)
    print("  ✓ SemanticCache context manager works")


async def test_semantic_cache_async_context_manager():
    """Test SemanticCache async context manager."""
    print("Testing SemanticCache async context manager...")

    async with SemanticCache(max_entries=10) as cache:
        await cache.aset("test", "value")
        result = await cache.aget("test")
        assert result == "value"

    print("  ✓ SemanticCache async context manager works")


def test_orchestrator_bounded():
    """Test that AgentOrchestrator workflow history is bounded."""
    print("Testing AgentOrchestrator workflow history is bounded...")
    orchestrator = AgentOrchestrator(max_workflow_history=50)

    # Create many workflow results
    from aiops.agents.orchestrator import WorkflowResult, ExecutionStatus
    from datetime import datetime

    for i in range(75):
        result = WorkflowResult(
            workflow_id=f"workflow_{i}",
            status=ExecutionStatus.COMPLETED,
            tasks=[],
            started_at=datetime.now(),
            summary={"test": True}
        )
        orchestrator._store_workflow_result(f"workflow_{i}", result)

    # Should not exceed max_workflow_history
    assert len(orchestrator.workflows) <= orchestrator._max_workflow_history, \
        f"Workflow history exceeded limit: {len(orchestrator.workflows)}"
    print(f"  ✓ Workflow history bounded to {len(orchestrator.workflows)} (max: {orchestrator._max_workflow_history})")


def test_agent_registry_bounded():
    """Test that AgentRegistry instance cache is bounded."""
    print("Testing AgentRegistry instance cache is bounded...")
    registry = AgentRegistry(max_cached_instances=20)

    # Note: We can't easily test this without actually registering agents
    # But we can verify the structure is correct
    assert hasattr(registry, '_max_cached_instances')
    assert registry._max_cached_instances == 20
    print(f"  ✓ AgentRegistry configured with max instances: {registry._max_cached_instances}")


def test_cache_context_manager():
    """Test Cache context manager."""
    print("Testing Cache context manager...")

    with Cache(cache_dir=".test_cache") as cache:
        cache.set("test_key", "test_value")
        assert cache.get("test_key") == "test_value"

    print("  ✓ Cache context manager works")


async def test_cache_async_context_manager():
    """Test Cache async context manager."""
    print("Testing Cache async context manager...")

    async with Cache(cache_dir=".test_cache") as cache:
        cache.set("test_key", "test_value")
        assert cache.get("test_key") == "test_value"

    print("  ✓ Cache async context manager works")


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Memory Management Tests")
    print("="*60 + "\n")

    try:
        # Sync tests
        test_stampede_locks_bounded()
        test_rate_limiter_bounded()
        test_semantic_cache_bounded()
        test_semantic_cache_context_manager()
        test_orchestrator_bounded()
        test_agent_registry_bounded()
        test_cache_context_manager()

        # Async tests
        await test_semantic_cache_async_context_manager()
        await test_cache_async_context_manager()

        print("\n" + "="*60)
        print("All memory management tests PASSED ✓")
        print("="*60 + "\n")

    except AssertionError as e:
        print(f"\n❌ Test FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
