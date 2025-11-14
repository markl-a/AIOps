"""Advanced usage examples for AIOps framework."""

import asyncio
from aiops.agents.cicd_optimizer import CICDOptimizerAgent
from aiops.agents.anomaly_detector import AnomalyDetectorAgent
from aiops.agents.auto_fixer import AutoFixerAgent
from aiops.agents.performance_analyzer import PerformanceAnalyzerAgent
from aiops.core.logger import setup_logger


async def example_cicd_optimization():
    """Example: CI/CD pipeline optimization."""
    print("\n=== Example 1: CI/CD Pipeline Optimization ===\n")

    pipeline_config = """
name: CI Pipeline

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Node.js
        uses: actions/setup-node@v2
        with:
          node-version: '16'
      - name: Install dependencies
        run: npm install
      - name: Run linter
        run: npm run lint
      - name: Run tests
        run: npm test
      - name: Build
        run: npm run build
      - name: Deploy
        run: ./deploy.sh
"""

    agent = CICDOptimizerAgent()
    result = await agent.execute(pipeline_config=pipeline_config)

    if result.current_duration and result.estimated_duration:
        improvement = (
            (result.current_duration - result.estimated_duration)
            / result.current_duration
            * 100
        )
        print(f"Estimated Improvement: {improvement:.1f}%")
        print(f"Duration: {result.current_duration}m → {result.estimated_duration}m\n")

    if result.optimizations:
        print("Optimizations:")
        for opt in result.optimizations:
            print(f"  • {opt}")

    if result.parallel_opportunities:
        print("\nParallelization Opportunities:")
        for opp in result.parallel_opportunities:
            print(f"  • {opp}")


async def example_anomaly_detection():
    """Example: Anomaly detection."""
    print("\n=== Example 2: Anomaly Detection ===\n")

    metrics = {
        "cpu_usage": 95.2,
        "memory_usage": 87.5,
        "error_rate": 12.5,
        "response_time_ms": 2500,
        "request_rate": 1200,
        "disk_usage": 45.0,
    }

    baseline = {
        "cpu_usage": 45.0,
        "memory_usage": 60.0,
        "error_rate": 0.5,
        "response_time_ms": 250,
        "request_rate": 1000,
        "disk_usage": 40.0,
    }

    agent = AnomalyDetectorAgent()
    result = await agent.execute(
        metrics=metrics, baseline=baseline, context="Production API server"
    )

    print(f"Total Anomalies: {result.total_anomalies}")
    print(f"Critical: {result.critical_count}\n")
    print(f"Summary: {result.summary}\n")

    if result.anomalies:
        print("Detected Anomalies:")
        for anomaly in result.anomalies:
            print(f"\n  [{anomaly.severity}] {anomaly.metric_name}")
            print(f"  {anomaly.description}")
            print(f"  Baseline: {anomaly.baseline} → Current: {anomaly.current_value}")
            print(f"  Confidence: {anomaly.confidence}%")

    if result.recommendations:
        print("\nRecommendations:")
        for rec in result.recommendations:
            print(f"  • {rec}")


async def example_auto_fix():
    """Example: Auto-fix."""
    print("\n=== Example 3: Automated Fix Generation ===\n")

    issue = "Application is experiencing high memory usage and frequent OOM errors"

    logs = """
2024-01-10 15:30:45 ERROR OutOfMemoryError: Java heap space
2024-01-10 15:30:46 WARN GC overhead limit exceeded
2024-01-10 15:31:12 ERROR OutOfMemoryError: Java heap space
2024-01-10 15:31:45 ERROR Application crashed with exit code 137
"""

    system_state = {
        "memory_limit": "512Mi",
        "memory_usage": "498Mi",
        "heap_size": "-Xmx256m",
        "deployment": "api-service",
    }

    agent = AutoFixerAgent()
    result = await agent.execute(
        issue_description=issue, logs=logs, system_state=system_state
    )

    print(f"Issue: {result.issue_summary}")
    print(f"Root Cause: {result.root_cause}\n")

    fix = result.recommended_fix
    print(f"Recommended Fix ({fix.fix_type}):")
    print(f"  Confidence: {fix.confidence}%")
    print(f"  Risk Level: {fix.risk_level}")
    print(f"  Description: {fix.description}\n")

    print("Commands:")
    for cmd in fix.commands:
        print(f"  $ {cmd}")

    print("\nValidation:")
    for val in fix.validation:
        print(f"  • {val}")

    print(f"\nRollback Plan: {fix.rollback_plan}")


async def example_performance_analysis():
    """Example: Performance analysis."""
    print("\n=== Example 4: Performance Analysis ===\n")

    code = """
def find_duplicates(data):
    duplicates = []
    for i in range(len(data)):
        for j in range(i + 1, len(data)):
            if data[i] == data[j] and data[i] not in duplicates:
                duplicates.append(data[i])
    return duplicates

def process_records(records):
    results = []
    for record in records:
        # Query database for each record
        user = database.get_user(record['user_id'])
        # Query again for user details
        details = database.get_user_details(record['user_id'])
        results.append({'user': user, 'details': details})
    return results
"""

    agent = PerformanceAnalyzerAgent()
    result = await agent.execute(code=code, language="python")

    print(f"Performance Score: {result.overall_score}/100\n")
    print(f"Summary: {result.summary}\n")

    if result.issues:
        print("Performance Issues:")
        for issue in result.issues:
            print(f"\n  [{issue.severity}] {issue.category} - {issue.location}")
            print(f"  {issue.description}")
            print(f"  Impact: {issue.impact}")
            print(f"  Optimization: {issue.optimization}")
            if issue.estimated_improvement:
                print(f"  Estimated Improvement: {issue.estimated_improvement}")

    if result.optimizations:
        print("\nPriority Optimizations:")
        for opt in result.optimizations:
            print(f"  • {opt}")


async def main():
    """Run all advanced examples."""
    setup_logger()

    print("\n" + "="*60)
    print("AIOps Framework - Advanced Usage Examples")
    print("="*60)

    await example_cicd_optimization()
    await example_anomaly_detection()
    await example_auto_fix()
    await example_performance_analysis()

    print("\n" + "="*60)
    print("Advanced examples completed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
