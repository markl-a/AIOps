#!/usr/bin/env python3
"""
Load Testing Script for AIOps API

Simulates realistic load on the AIOps API to measure performance
under stress and identify bottlenecks.
"""

import sys
import asyncio
import time
import statistics
from pathlib import Path
from typing import List, Dict, Any
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class LoadTester:
    """Load testing for AIOps API"""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        duration_seconds: int = 60,
        rps: int = 10,
    ):
        """
        Initialize load tester.

        Args:
            base_url: API base URL
            duration_seconds: Test duration in seconds
            rps: Target requests per second
        """
        self.base_url = base_url
        self.duration_seconds = duration_seconds
        self.rps = rps
        self.results: List[Dict[str, Any]] = []

    async def make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an API request"""
        import aiohttp

        url = f"{self.base_url}{endpoint}"

        start = time.time()
        error = None
        status_code = None

        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, **kwargs) as response:
                    status_code = response.status
                    data = await response.json() if response.content_type == "application/json" else await response.text()
                    elapsed = time.time() - start

                    return {
                        "method": method,
                        "endpoint": endpoint,
                        "status_code": status_code,
                        "elapsed": elapsed,
                        "success": 200 <= status_code < 300,
                        "error": None,
                    }

        except Exception as e:
            elapsed = time.time() - start
            return {
                "method": method,
                "endpoint": endpoint,
                "status_code": status_code,
                "elapsed": elapsed,
                "success": False,
                "error": str(e),
            }

    async def run_scenario(self, scenario_name: str, requests: List[Dict[str, Any]]):
        """
        Run a load test scenario.

        Args:
            scenario_name: Scenario name
            requests: List of request specifications
        """
        print(f"\n🔥 Running scenario: {scenario_name}")
        print(f"   Duration: {self.duration_seconds}s")
        print(f"   Target RPS: {self.rps}")
        print(f"   Requests: {len(requests)} different endpoints")

        start_time = time.time()
        results = []
        request_count = 0

        # Calculate delay between requests
        delay = 1.0 / self.rps if self.rps > 0 else 0

        while time.time() - start_time < self.duration_seconds:
            # Pick a request from the scenario
            request_spec = requests[request_count % len(requests)]

            # Make request
            result = await self.make_request(**request_spec)
            results.append(result)
            request_count += 1

            # Progress
            if request_count % (self.rps * 10) == 0:
                elapsed = time.time() - start_time
                print(f"   Progress: {elapsed:.0f}s / {self.duration_seconds}s ({request_count} requests)")

            # Throttle to target RPS
            if delay > 0:
                await asyncio.sleep(delay)

        # Calculate statistics
        total_time = time.time() - start_time
        self.print_scenario_results(scenario_name, results, total_time)

        return results

    def print_scenario_results(self, scenario_name: str, results: List[Dict], total_time: float):
        """Print scenario results"""
        print(f"\n📊 Results for {scenario_name}:")

        total_requests = len(results)
        successful_requests = sum(1 for r in results if r["success"])
        failed_requests = total_requests - successful_requests

        # Calculate latency statistics
        latencies = [r["elapsed"] * 1000 for r in results if r["success"]]

        if latencies:
            sorted_latencies = sorted(latencies)
            print(f"   Total Requests: {total_requests}")
            print(f"   Successful: {successful_requests} ({successful_requests / total_requests * 100:.1f}%)")
            print(f"   Failed: {failed_requests}")
            print(f"   Actual RPS: {total_requests / total_time:.2f}")
            print(f"   Latency:")
            print(f"     Min:    {min(latencies):8.2f}ms")
            print(f"     Mean:   {statistics.mean(latencies):8.2f}ms")
            print(f"     Median: {statistics.median(latencies):8.2f}ms")
            print(f"     P95:    {sorted_latencies[int(len(sorted_latencies) * 0.95)]:8.2f}ms")
            print(f"     P99:    {sorted_latencies[int(len(sorted_latencies) * 0.99)]:8.2f}ms")
            print(f"     Max:    {max(latencies):8.2f}ms")
        else:
            print(f"   All requests failed!")

        # Status code distribution
        status_codes = {}
        for result in results:
            code = result["status_code"] or "error"
            status_codes[code] = status_codes.get(code, 0) + 1

        print(f"   Status Codes:")
        for code, count in sorted(status_codes.items()):
            print(f"     {code}: {count} ({count / total_requests * 100:.1f}%)")

        # Errors
        errors = [r["error"] for r in results if r["error"]]
        if errors:
            unique_errors = list(set(errors))
            print(f"   Errors ({len(unique_errors)} unique):")
            for error in unique_errors[:3]:
                print(f"     - {error}")
            if len(unique_errors) > 3:
                print(f"     ... and {len(unique_errors) - 3} more")


async def main():
    """Run load tests"""
    print("⚡ AIOps API Load Testing")
    print("=" * 70)

    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(description="Load test AIOps API")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--duration", type=int, default=30, help="Test duration in seconds")
    parser.add_argument("--rps", type=int, default=10, help="Target requests per second")
    parser.add_argument("--scenario", choices=["light", "medium", "heavy"], default="light")

    args = parser.parse_args()

    # Adjust duration and RPS based on scenario
    if args.scenario == "medium":
        duration = args.duration * 2
        rps = args.rps * 2
    elif args.scenario == "heavy":
        duration = args.duration * 3
        rps = args.rps * 5
    else:
        duration = args.duration
        rps = args.rps

    print(f"Scenario: {args.scenario.upper()}")
    print(f"Target: {args.url}")
    print(f"Duration: {duration}s")
    print(f"RPS: {rps}")

    tester = LoadTester(
        base_url=args.url,
        duration_seconds=duration,
        rps=rps,
    )

    # Define scenarios
    health_check_requests = [
        {"method": "GET", "endpoint": "/health"},
    ]

    api_requests = [
        {"method": "GET", "endpoint": "/"},
        {"method": "GET", "endpoint": "/health"},
        {"method": "GET", "endpoint": "/api/v1/llm/providers"},
        {"method": "GET", "endpoint": "/api/v1/webhooks/status"},
    ]

    # Run scenarios
    print("\n" + "=" * 70)
    print("Starting Load Tests")
    print("=" * 70)

    # Scenario 1: Health check endpoint
    await tester.run_scenario("Health Check Endpoint", health_check_requests)

    # Scenario 2: Mixed API endpoints
    await tester.run_scenario("Mixed API Endpoints", api_requests)

    print("\n" + "=" * 70)
    print("✅ Load Testing Complete")
    print("=" * 70)

    print("\n💡 Recommendations:")
    print("   - Monitor API response times under load")
    print("   - Check for memory leaks during extended tests")
    print("   - Verify database connection pool doesn't exhaust")
    print("   - Test with production-like data volumes")
    print("   - Run tests with different concurrency levels")


if __name__ == "__main__":
    asyncio.run(main())
