"""Tests for Performance Analyzer Agent."""

import pytest
from unittest.mock import AsyncMock, patch
from aiops.agents.performance_analyzer import (
    PerformanceAnalyzerAgent,
    PerformanceReport,
    PerformanceIssue,
    Optimization,
)


@pytest.fixture
def perf_agent():
    """Create performance analyzer agent."""
    return PerformanceAnalyzerAgent()


@pytest.fixture
def sample_code_with_issues():
    """Sample code with performance issues."""
    return """
def process_users(users):
    results = []
    for user in users:
        # N+1 query pattern
        user_posts = db.query(f"SELECT * FROM posts WHERE user_id = {user.id}")
        for post in user_posts:
            results.append(process_post(post))
    return results

def find_duplicates(items):
    # O(n^2) algorithm
    duplicates = []
    for i in range(len(items)):
        for j in range(i+1, len(items)):
            if items[i] == items[j]:
                duplicates.append(items[i])
    return duplicates
"""


@pytest.fixture
def sample_metrics():
    """Sample performance metrics."""
    return {
        "cpu_usage": 85.5,
        "memory_usage": 78.2,
        "response_time_p50": 250,
        "response_time_p95": 1500,
        "response_time_p99": 3000,
        "throughput": 100,
    }


@pytest.mark.asyncio
async def test_analyze_code_performance(perf_agent, sample_code_with_issues):
    """Test code performance analysis."""
    mock_result = PerformanceReport(
        issues=[
            PerformanceIssue(
                severity="high",
                category="database",
                description="N+1 query pattern detected",
                location="Line 4-6",
                impact="Multiple database round trips causing high latency",
                code_snippet="user_posts = db.query(...)",
            ),
            PerformanceIssue(
                severity="medium",
                category="algorithm",
                description="O(n^2) time complexity",
                location="Line 12-15",
                impact="Poor scalability with large datasets",
                code_snippet="for i in range... for j in range...",
            ),
        ],
        optimizations=[
            Optimization(
                target="process_users function",
                recommendation="Use JOIN or eager loading to fetch all posts in single query",
                estimated_improvement="75% reduction in database calls",
                difficulty="medium",
            ),
            Optimization(
                target="find_duplicates function",
                recommendation="Use set-based approach for O(n) complexity",
                estimated_improvement="90% faster for large datasets",
                difficulty="low",
            ),
        ],
        overall_score=45.0,
        estimated_speedup="3-5x",
    )

    with patch.object(
        perf_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await perf_agent.execute(code=sample_code_with_issues, language="python")

        assert isinstance(result, PerformanceReport)
        assert len(result.issues) == 2
        assert len(result.optimizations) == 2
        assert result.overall_score == 45.0


@pytest.mark.asyncio
async def test_analyze_metrics(perf_agent, sample_metrics):
    """Test performance metrics analysis."""
    mock_result = PerformanceReport(
        issues=[
            PerformanceIssue(
                severity="high",
                category="latency",
                description="P95 response time exceeds acceptable threshold",
                impact="15% of requests experience degraded performance",
            ),
            PerformanceIssue(
                severity="medium",
                category="resource",
                description="High CPU utilization",
                impact="Limited headroom for traffic spikes",
            ),
        ],
        optimizations=[
            Optimization(
                target="Response time",
                recommendation="Add caching layer for frequently accessed data",
                estimated_improvement="50% reduction in P95 latency",
            )
        ],
        overall_score=60.0,
        estimated_speedup="2x",
    )

    with patch.object(
        perf_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await perf_agent.analyze_metrics(metrics=sample_metrics, baseline=None)

        assert isinstance(result, PerformanceReport)
        assert any(issue.category == "latency" for issue in result.issues)


@pytest.mark.asyncio
async def test_compare_with_baseline(perf_agent, sample_metrics):
    """Test performance comparison with baseline."""
    baseline_metrics = {
        "cpu_usage": 45.0,
        "memory_usage": 50.0,
        "response_time_p95": 500,
    }

    mock_result = PerformanceReport(
        issues=[
            PerformanceIssue(
                severity="critical",
                category="regression",
                description="P95 latency increased by 200%",
                impact="Severe performance degradation",
            )
        ],
        optimizations=[],
        overall_score=30.0,
        estimated_speedup="N/A",
    )

    with patch.object(
        perf_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await perf_agent.analyze_metrics(
            metrics=sample_metrics, baseline=baseline_metrics
        )

        assert any(issue.category == "regression" for issue in result.issues)


@pytest.mark.asyncio
async def test_algorithm_complexity_analysis(perf_agent):
    """Test algorithm complexity detection."""
    code_with_nested_loops = """
def matrix_multiply(a, b):
    result = []
    for i in range(len(a)):
        row = []
        for j in range(len(b[0])):
            sum_val = 0
            for k in range(len(b)):
                sum_val += a[i][k] * b[k][j]
            row.append(sum_val)
        result.append(row)
    return result
"""

    mock_result = PerformanceReport(
        issues=[
            PerformanceIssue(
                severity="medium",
                category="algorithm",
                description="O(n^3) time complexity",
                impact="Poor performance for large matrices",
            )
        ],
        optimizations=[
            Optimization(
                target="matrix_multiply",
                recommendation="Use NumPy for optimized matrix operations",
                estimated_improvement="10-100x faster",
            )
        ],
        overall_score=55.0,
        estimated_speedup="10-100x",
    )

    with patch.object(
        perf_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await perf_agent.execute(code=code_with_nested_loops)

        assert any("complexity" in issue.category.lower() for issue in result.issues)


@pytest.mark.asyncio
async def test_memory_leak_detection(perf_agent):
    """Test memory leak detection."""
    code_with_leak = """
cache = []

def process_data(data):
    # Potential memory leak - cache grows indefinitely
    cache.append(data)
    return cache[-1]
"""

    mock_result = PerformanceReport(
        issues=[
            PerformanceIssue(
                severity="high",
                category="memory",
                description="Potential memory leak in global cache",
                impact="Unbounded memory growth over time",
            )
        ],
        optimizations=[
            Optimization(
                target="cache management",
                recommendation="Implement LRU cache with size limit",
                estimated_improvement="Prevent memory exhaustion",
            )
        ],
        overall_score=40.0,
        estimated_speedup="N/A",
    )

    with patch.object(
        perf_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await perf_agent.execute(code=code_with_leak)

        assert any(issue.category == "memory" for issue in result.issues)


@pytest.mark.asyncio
async def test_error_handling(perf_agent):
    """Test error handling."""
    with patch.object(
        perf_agent,
        "_generate_structured_response",
        side_effect=Exception("Analysis failed"),
    ):
        result = await perf_agent.execute(code="invalid")

        assert isinstance(result, PerformanceReport)
        assert result.overall_score == 0


def test_score_validation(perf_agent):
    """Test performance score is valid."""
    report = PerformanceReport(
        issues=[],
        optimizations=[],
        overall_score=75.0,
        estimated_speedup="1x",
    )

    assert 0 <= report.overall_score <= 100
