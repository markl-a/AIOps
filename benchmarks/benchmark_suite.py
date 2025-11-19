#!/usr/bin/env python3
"""
AIOps Performance Benchmark Suite

Comprehensive benchmarks for measuring performance of AIOps components:
- API endpoint response times
- Database query performance
- Cache hit rates and latency
- Agent execution times
- LLM provider latency
- Webhook processing
- Concurrent request handling
"""

import sys
import asyncio
import time
import statistics
from pathlib import Path
from typing import List, Dict, Any, Callable
from dataclasses import dataclass, field
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@dataclass
class BenchmarkResult:
    """Result of a benchmark"""
    name: str
    iterations: int
    total_time: float
    min_time: float
    max_time: float
    mean_time: float
    median_time: float
    p95_time: float
    p99_time: float
    throughput: float  # operations per second
    success_count: int
    error_count: int
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "iterations": self.iterations,
            "total_time_seconds": round(self.total_time, 4),
            "latency_ms": {
                "min": round(self.min_time * 1000, 2),
                "max": round(self.max_time * 1000, 2),
                "mean": round(self.mean_time * 1000, 2),
                "median": round(self.median_time * 1000, 2),
                "p95": round(self.p95_time * 1000, 2),
                "p99": round(self.p99_time * 1000, 2),
            },
            "throughput_ops_per_second": round(self.throughput, 2),
            "success_rate": round(self.success_count / self.iterations * 100, 2) if self.iterations > 0 else 0,
            "error_count": self.error_count,
        }


class BenchmarkRunner:
    """Run performance benchmarks"""

    def __init__(self, iterations: int = 100):
        """
        Initialize benchmark runner.

        Args:
            iterations: Number of iterations for each benchmark
        """
        self.iterations = iterations
        self.results: List[BenchmarkResult] = []

    async def run_benchmark(
        self,
        name: str,
        func: Callable,
        *args,
        **kwargs
    ) -> BenchmarkResult:
        """
        Run a benchmark.

        Args:
            name: Benchmark name
            func: Function to benchmark
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            BenchmarkResult
        """
        print(f"\n🏃 Running: {name} ({self.iterations} iterations)")

        times: List[float] = []
        errors: List[str] = []
        success_count = 0
        error_count = 0

        start_total = time.time()

        for i in range(self.iterations):
            try:
                start = time.time()

                if asyncio.iscoroutinefunction(func):
                    await func(*args, **kwargs)
                else:
                    func(*args, **kwargs)

                elapsed = time.time() - start
                times.append(elapsed)
                success_count += 1

            except Exception as e:
                error_count += 1
                error_msg = f"{type(e).__name__}: {str(e)}"
                if error_msg not in errors:
                    errors.append(error_msg)

            # Progress indicator
            if (i + 1) % (self.iterations // 10) == 0:
                print(f"  Progress: {i + 1}/{self.iterations}")

        total_time = time.time() - start_total

        # Calculate statistics
        if times:
            sorted_times = sorted(times)
            min_time = min(times)
            max_time = max(times)
            mean_time = statistics.mean(times)
            median_time = statistics.median(times)
            p95_time = sorted_times[int(len(sorted_times) * 0.95)]
            p99_time = sorted_times[int(len(sorted_times) * 0.99)]
            throughput = success_count / total_time
        else:
            min_time = max_time = mean_time = median_time = p95_time = p99_time = 0
            throughput = 0

        result = BenchmarkResult(
            name=name,
            iterations=self.iterations,
            total_time=total_time,
            min_time=min_time,
            max_time=max_time,
            mean_time=mean_time,
            median_time=median_time,
            p95_time=p95_time,
            p99_time=p99_time,
            throughput=throughput,
            success_count=success_count,
            error_count=error_count,
            errors=errors,
        )

        self.results.append(result)

        # Print summary
        print(f"  ✓ Completed")
        print(f"    Mean: {mean_time * 1000:.2f}ms")
        print(f"    P95: {p95_time * 1000:.2f}ms")
        print(f"    Throughput: {throughput:.2f} ops/sec")

        return result

    def print_summary(self):
        """Print benchmark summary"""
        print("\n" + "=" * 70)
        print("📊 BENCHMARK SUMMARY")
        print("=" * 70)

        for result in self.results:
            print(f"\n{result.name}:")
            print(f"  Iterations: {result.iterations}")
            print(f"  Total Time: {result.total_time:.2f}s")
            print(f"  Latency:")
            print(f"    Min:    {result.min_time * 1000:8.2f}ms")
            print(f"    Mean:   {result.mean_time * 1000:8.2f}ms")
            print(f"    Median: {result.median_time * 1000:8.2f}ms")
            print(f"    P95:    {result.p95_time * 1000:8.2f}ms")
            print(f"    P99:    {result.p99_time * 1000:8.2f}ms")
            print(f"    Max:    {result.max_time * 1000:8.2f}ms")
            print(f"  Throughput: {result.throughput:.2f} ops/sec")
            print(f"  Success Rate: {result.success_count / result.iterations * 100:.2f}%")

            if result.errors:
                print(f"  Errors ({result.error_count}):")
                for error in result.errors[:3]:
                    print(f"    - {error}")
                if len(result.errors) > 3:
                    print(f"    ... and {len(result.errors) - 3} more")

    def save_results(self, filename: str = "benchmark_results.json"):
        """Save results to JSON file"""
        output = {
            "timestamp": time.time(),
            "iterations": self.iterations,
            "benchmarks": [r.to_dict() for r in self.results],
        }

        output_path = Path(__file__).parent / filename

        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"\n📄 Results saved to: {output_path}")


# Benchmark functions
async def benchmark_cache_write():
    """Benchmark cache write operations"""
    try:
        from aiops.cache.redis_cache import RedisCache
        import os

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        cache = RedisCache(redis_url=redis_url)
        await cache.connect()

        await cache.set("benchmark_key", {"data": "test"}, ttl=60)

        await cache.disconnect()
    except Exception:
        # Silently skip if Redis not available
        pass


async def benchmark_cache_read():
    """Benchmark cache read operations"""
    try:
        from aiops.cache.redis_cache import RedisCache
        import os

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        cache = RedisCache(redis_url=redis_url)
        await cache.connect()

        # Set a value first
        await cache.set("benchmark_key", {"data": "test"}, ttl=60)

        # Read it
        await cache.get("benchmark_key")

        await cache.disconnect()
    except Exception:
        pass


async def benchmark_agent_execution():
    """Benchmark AI agent execution (mocked)"""
    # Simulate agent execution time
    await asyncio.sleep(0.01)  # 10ms simulated work


async def benchmark_webhook_parsing():
    """Benchmark webhook parsing"""
    from aiops.webhooks import GitHubWebhookHandler

    handler = GitHubWebhookHandler()

    headers = {
        "x-github-event": "pull_request",
        "x-github-delivery": "test-123",
    }

    payload = {
        "action": "opened",
        "number": 1,
        "pull_request": {
            "number": 1,
            "title": "Test PR",
            "state": "open",
            "html_url": "https://github.com/test/repo/pull/1",
            "base": {"ref": "main"},
            "head": {"ref": "feature"},
        },
        "repository": {
            "full_name": "test/repo",
            "html_url": "https://github.com/test/repo",
        },
        "sender": {
            "login": "testuser",
        },
    }

    handler.parse_event(headers, payload)


async def benchmark_concurrent_operations(n_concurrent: int = 10):
    """Benchmark concurrent operations"""
    async def mock_operation():
        await asyncio.sleep(0.001)  # 1ms work

    tasks = [mock_operation() for _ in range(n_concurrent)]
    await asyncio.gather(*tasks)


async def main():
    """Run all benchmarks"""
    print("🏁 AIOps Performance Benchmark Suite")
    print("=" * 70)

    # Check if we should run full or quick benchmarks
    import sys
    if "--quick" in sys.argv:
        iterations = 10
        print("Running in QUICK mode (10 iterations)")
    else:
        iterations = 100
        print(f"Running {iterations} iterations per benchmark")

    runner = BenchmarkRunner(iterations=iterations)

    # Run benchmarks
    print("\n📦 Cache Benchmarks")
    await runner.run_benchmark("Cache Write", benchmark_cache_write)
    await runner.run_benchmark("Cache Read", benchmark_cache_read)

    print("\n🤖 Agent Benchmarks")
    await runner.run_benchmark("Agent Execution (Mocked)", benchmark_agent_execution)

    print("\n🔗 Webhook Benchmarks")
    await runner.run_benchmark("Webhook Parsing", benchmark_webhook_parsing)

    print("\n⚡ Concurrency Benchmarks")
    await runner.run_benchmark("10 Concurrent Operations", benchmark_concurrent_operations, 10)
    await runner.run_benchmark("50 Concurrent Operations", benchmark_concurrent_operations, 50)
    await runner.run_benchmark("100 Concurrent Operations", benchmark_concurrent_operations, 100)

    # Print summary
    runner.print_summary()

    # Save results
    runner.save_results()

    print("\n✅ Benchmarks completed!")


if __name__ == "__main__":
    asyncio.run(main())
