"""Basic usage examples for AIOps framework."""

import asyncio
from aiops.agents.code_reviewer import CodeReviewAgent
from aiops.agents.test_generator import TestGeneratorAgent
from aiops.agents.log_analyzer import LogAnalyzerAgent
from aiops.core.logger import setup_logger


async def example_code_review():
    """Example: Code review."""
    print("\n=== Example 1: Code Review ===\n")

    code = """
def calculate_sum(numbers):
    total = 0
    for i in range(len(numbers)):
        total = total + numbers[i]
    return total

def process_data(data):
    result = []
    for item in data:
        if item != None:
            result.append(item * 2)
    return result
"""

    agent = CodeReviewAgent()
    result = await agent.execute(code=code, language="python")

    print(f"Overall Score: {result.overall_score}/100")
    print(f"\nSummary: {result.summary}\n")

    if result.issues:
        print("Issues Found:")
        for i, issue in enumerate(result.issues, 1):
            print(f"\n{i}. [{issue.severity}] {issue.category}")
            print(f"   {issue.description}")
            print(f"   Suggestion: {issue.suggestion}")

    if result.strengths:
        print("\nStrengths:")
        for strength in result.strengths:
            print(f"  ✓ {strength}")


async def example_test_generation():
    """Example: Test generation."""
    print("\n=== Example 2: Test Generation ===\n")

    code = """
def fibonacci(n):
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]

    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i-1] + fib[i-2])
    return fib
"""

    agent = TestGeneratorAgent()
    result = await agent.execute(code=code, language="python")

    print(f"Generated {len(result.test_cases)} test cases using {result.framework}\n")

    for i, test in enumerate(result.test_cases[:3], 1):  # Show first 3 tests
        print(f"\n--- Test {i}: {test.name} ---")
        print(f"Type: {test.test_type} | Priority: {test.priority}")
        print(f"Description: {test.description}\n")
        print(test.test_code)


async def example_log_analysis():
    """Example: Log analysis."""
    print("\n=== Example 3: Log Analysis ===\n")

    logs = """
2024-01-10 10:15:23 ERROR Failed to connect to database: Connection timeout
2024-01-10 10:15:24 WARN Retrying connection (attempt 1/3)
2024-01-10 10:15:29 ERROR Failed to connect to database: Connection timeout
2024-01-10 10:15:30 WARN Retrying connection (attempt 2/3)
2024-01-10 10:15:35 ERROR Failed to connect to database: Connection timeout
2024-01-10 10:15:36 WARN Retrying connection (attempt 3/3)
2024-01-10 10:15:41 CRITICAL Database connection failed after 3 attempts
2024-01-10 10:15:41 ERROR API request /api/users failed: Service unavailable
2024-01-10 10:15:42 ERROR API request /api/products failed: Service unavailable
2024-01-10 10:15:43 INFO Health check failed: database unhealthy
"""

    agent = LogAnalyzerAgent()
    result = await agent.execute(logs=logs)

    print(f"Summary: {result.summary}\n")

    if result.insights:
        print("Key Insights:")
        for insight in result.insights:
            print(f"\n  [{insight.severity}] {insight.category}")
            print(f"  {insight.message}")

    if result.root_causes:
        print("\nRoot Causes:")
        for rc in result.root_causes:
            print(f"\n  • {rc.root_cause} (confidence: {rc.confidence}%)")
            print(f"    Evidence: {', '.join(rc.evidence[:2])}")

    if result.recommendations:
        print("\nRecommendations:")
        for rec in result.recommendations:
            print(f"  • {rec}")


async def main():
    """Run all examples."""
    setup_logger()

    print("\n" + "="*60)
    print("AIOps Framework - Basic Usage Examples")
    print("="*60)

    await example_code_review()
    await example_test_generation()
    await example_log_analysis()

    print("\n" + "="*60)
    print("Examples completed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
