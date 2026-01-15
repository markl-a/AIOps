"""Tests for API Performance Analyzer Agent."""

import pytest
from aiops.agents.api_performance_analyzer import (
    APIPerformanceAnalyzer,
    APIPerformanceResult,
    APIEndpoint,
    APIOptimization,
)


@pytest.fixture
def api_analyzer():
    """Create API performance analyzer agent."""
    return APIPerformanceAnalyzer()


@pytest.fixture
def sample_endpoints():
    """Sample API endpoints data."""
    return [
        {
            "method": "GET",
            "path": "/api/users",
            "avg_latency_ms": 150,
            "p95_latency_ms": 300,
            "p99_latency_ms": 500,
            "requests_per_minute": 200,
            "error_rate": 0.5,
            "avg_response_size_kb": 50,
        },
        {
            "method": "POST",
            "path": "/api/orders",
            "avg_latency_ms": 800,
            "p95_latency_ms": 1500,
            "p99_latency_ms": 2500,
            "requests_per_minute": 50,
            "error_rate": 2.5,
            "avg_response_size_kb": 100,
        },
        {
            "method": "GET",
            "path": "/api/products",
            "avg_latency_ms": 100,
            "p95_latency_ms": 200,
            "p99_latency_ms": 400,
            "requests_per_minute": 500,
            "error_rate": 0.1,
            "avg_response_size_kb": 800,
        },
    ]


@pytest.fixture
def high_latency_endpoint():
    """Single endpoint with high latency."""
    return [
        {
            "method": "GET",
            "path": "/api/reports",
            "avg_latency_ms": 2000,
            "p95_latency_ms": 3500,
            "p99_latency_ms": 5000,
            "requests_per_minute": 30,
            "error_rate": 1.5,
            "avg_response_size_kb": 200,
        }
    ]


@pytest.fixture
def high_error_rate_endpoint():
    """Endpoint with high error rate."""
    return [
        {
            "method": "POST",
            "path": "/api/payments",
            "avg_latency_ms": 300,
            "p95_latency_ms": 500,
            "p99_latency_ms": 800,
            "requests_per_minute": 100,
            "error_rate": 7.5,
            "avg_response_size_kb": 50,
        }
    ]


@pytest.mark.asyncio
async def test_analyze_api_basic(api_analyzer, sample_endpoints):
    """Test basic API performance analysis."""
    result = await api_analyzer.analyze_api(
        endpoints=sample_endpoints,
        api_type="REST"
    )

    assert isinstance(result, APIPerformanceResult)
    assert result.api_type == "REST"
    assert result.endpoints_analyzed == 3
    assert len(result.endpoints) == 3
    assert result.performance_score >= 0
    assert result.performance_score <= 100


@pytest.mark.asyncio
async def test_analyze_api_detects_high_latency(api_analyzer, high_latency_endpoint):
    """Test detection of high latency issues."""
    result = await api_analyzer.analyze_api(
        endpoints=high_latency_endpoint,
        api_type="REST"
    )

    assert isinstance(result, APIPerformanceResult)
    # Should have at least one optimization for high latency
    high_latency_optimizations = [
        opt for opt in result.optimizations
        if opt.issue_type == "high_latency"
    ]
    assert len(high_latency_optimizations) >= 1
    assert high_latency_optimizations[0].severity in ["high", "critical"]


@pytest.mark.asyncio
async def test_analyze_api_detects_high_error_rate(api_analyzer, high_error_rate_endpoint):
    """Test detection of high error rate issues."""
    result = await api_analyzer.analyze_api(
        endpoints=high_error_rate_endpoint,
        api_type="REST"
    )

    assert isinstance(result, APIPerformanceResult)
    # Should detect high error rate
    error_optimizations = [
        opt for opt in result.optimizations
        if opt.issue_type == "high_error_rate"
    ]
    assert len(error_optimizations) >= 1
    # Error rate > 5% should be critical
    assert error_optimizations[0].severity == "critical"


@pytest.mark.asyncio
async def test_analyze_api_detects_caching_opportunities(api_analyzer):
    """Test detection of caching opportunities for high-traffic GET endpoints."""
    endpoints = [
        {
            "method": "GET",
            "path": "/api/products/list",
            "avg_latency_ms": 100,
            "p95_latency_ms": 200,
            "p99_latency_ms": 300,
            "requests_per_minute": 500,
            "error_rate": 0.1,
            "avg_response_size_kb": 100,
        }
    ]

    result = await api_analyzer.analyze_api(endpoints=endpoints, api_type="REST")

    assert len(result.caching_opportunities) >= 1
    assert "500" in result.caching_opportunities[0]  # Should mention request rate


@pytest.mark.asyncio
async def test_analyze_api_detects_large_response(api_analyzer):
    """Test detection of large response size issues."""
    endpoints = [
        {
            "method": "GET",
            "path": "/api/export",
            "avg_latency_ms": 500,
            "p95_latency_ms": 800,
            "p99_latency_ms": 1000,
            "requests_per_minute": 20,
            "error_rate": 0.2,
            "avg_response_size_kb": 1500,
        }
    ]

    result = await api_analyzer.analyze_api(endpoints=endpoints, api_type="REST")

    large_response_opts = [
        opt for opt in result.optimizations
        if opt.issue_type == "large_response"
    ]
    assert len(large_response_opts) >= 1
    assert "compression" in str(large_response_opts[0].recommendations).lower()


@pytest.mark.asyncio
async def test_analyze_api_detects_slow_mutations(api_analyzer):
    """Test detection of slow mutation endpoints."""
    endpoints = [
        {
            "method": "POST",
            "path": "/api/bulk-import",
            "avg_latency_ms": 1200,
            "p95_latency_ms": 2000,
            "p99_latency_ms": 3000,
            "requests_per_minute": 10,
            "error_rate": 0.5,
            "avg_response_size_kb": 50,
        }
    ]

    result = await api_analyzer.analyze_api(endpoints=endpoints, api_type="REST")

    slow_mutation_opts = [
        opt for opt in result.optimizations
        if opt.issue_type == "slow_mutation"
    ]
    assert len(slow_mutation_opts) >= 1
    assert "async" in str(slow_mutation_opts[0].recommendations).lower()


@pytest.mark.asyncio
async def test_analyze_api_empty_endpoints(api_analyzer):
    """Test analysis with empty endpoint list."""
    result = await api_analyzer.analyze_api(endpoints=[], api_type="REST")

    assert isinstance(result, APIPerformanceResult)
    assert result.endpoints_analyzed == 0
    assert len(result.endpoints) == 0
    assert result.performance_score == 100.0  # Perfect score for no endpoints


@pytest.mark.asyncio
async def test_analyze_api_graphql_type(api_analyzer, sample_endpoints):
    """Test analysis with GraphQL API type."""
    result = await api_analyzer.analyze_api(
        endpoints=sample_endpoints,
        api_type="GraphQL"
    )

    assert result.api_type == "GraphQL"
    assert "GraphQL" in result.summary


def test_performance_score_calculation(api_analyzer):
    """Test performance score calculation logic."""
    # Perfect endpoints
    perfect_endpoints = [
        APIEndpoint(
            method="GET",
            path="/api/test",
            avg_latency_ms=50,
            p95_latency_ms=100,
            p99_latency_ms=200,
            requests_per_minute=100,
            error_rate=0.0,
            avg_response_size_kb=50,
        )
    ]
    score = api_analyzer._calculate_performance_score(perfect_endpoints)
    assert score == 100.0

    # High latency endpoints
    slow_endpoints = [
        APIEndpoint(
            method="GET",
            path="/api/slow",
            avg_latency_ms=1000,
            p95_latency_ms=2000,
            p99_latency_ms=3000,
            requests_per_minute=100,
            error_rate=0.0,
            avg_response_size_kb=50,
        )
    ]
    slow_score = api_analyzer._calculate_performance_score(slow_endpoints)
    assert slow_score < 100.0
    assert slow_score >= 0


def test_suggest_cache_ttl(api_analyzer):
    """Test cache TTL suggestions."""
    user_endpoint = APIEndpoint(
        method="GET",
        path="/api/user/profile",
        avg_latency_ms=100,
        p95_latency_ms=200,
        p99_latency_ms=300,
        requests_per_minute=100,
        error_rate=0.1,
        avg_response_size_kb=50,
    )
    assert "5-10 minutes" in api_analyzer._suggest_cache_ttl(user_endpoint)

    list_endpoint = APIEndpoint(
        method="GET",
        path="/api/products/list",
        avg_latency_ms=100,
        p95_latency_ms=200,
        p99_latency_ms=300,
        requests_per_minute=100,
        error_rate=0.1,
        avg_response_size_kb=50,
    )
    assert "2-5 minutes" in api_analyzer._suggest_cache_ttl(list_endpoint)

    config_endpoint = APIEndpoint(
        method="GET",
        path="/api/config/settings",
        avg_latency_ms=100,
        p95_latency_ms=200,
        p99_latency_ms=300,
        requests_per_minute=100,
        error_rate=0.1,
        avg_response_size_kb=50,
    )
    assert "30-60 minutes" in api_analyzer._suggest_cache_ttl(config_endpoint)


def test_generate_summary(api_analyzer):
    """Test summary generation."""
    # Excellent performance
    summary = api_analyzer._generate_summary("REST", 10, 90.0, 2)
    assert "REST" in summary
    assert "10" in summary
    assert "excellent" in summary.lower()

    # Good performance
    summary = api_analyzer._generate_summary("REST", 5, 75.0, 5)
    assert "good" in summary.lower() or "improvement" in summary.lower()

    # Poor performance
    summary = api_analyzer._generate_summary("REST", 5, 40.0, 10)
    assert "critical" in summary.lower() or "needs" in summary.lower()
