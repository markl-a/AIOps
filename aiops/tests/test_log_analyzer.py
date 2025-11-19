"""Tests for Log Analyzer Agent."""

import pytest
from unittest.mock import AsyncMock, patch
from aiops.agents.log_analyzer import (
    LogAnalyzerAgent,
    LogAnalysisResult,
    LogPattern,
    RootCause,
)


@pytest.fixture
def log_agent():
    """Create log analyzer agent."""
    return LogAnalyzerAgent()


@pytest.fixture
def sample_error_logs():
    """Sample error logs."""
    return """
2024-01-15 10:30:15 ERROR [api] Connection timeout to database
2024-01-15 10:30:16 WARN [api] Retrying database connection (attempt 1/3)
2024-01-15 10:30:20 ERROR [api] Connection timeout to database
2024-01-15 10:30:21 WARN [api] Retrying database connection (attempt 2/3)
2024-01-15 10:30:25 ERROR [api] Connection timeout to database
2024-01-15 10:30:26 ERROR [api] Max retries exceeded, giving up
2024-01-15 10:30:27 CRITICAL [api] Service degraded: database unavailable
2024-01-15 10:31:00 ERROR [db] Connection pool exhausted
2024-01-15 10:31:05 ERROR [db] Cannot accept new connections
"""


@pytest.fixture
def sample_access_logs():
    """Sample access logs."""
    return """
192.168.1.100 - - [15/Jan/2024:10:30:00] "GET /api/users HTTP/1.1" 200
192.168.1.101 - - [15/Jan/2024:10:30:01] "POST /api/login HTTP/1.1" 200
192.168.1.102 - - [15/Jan/2024:10:30:02] "GET /api/products HTTP/1.1" 500
192.168.1.102 - - [15/Jan/2024:10:30:03] "GET /api/products HTTP/1.1" 500
192.168.1.103 - - [15/Jan/2024:10:30:04] "GET /api/products HTTP/1.1" 500
"""


@pytest.mark.asyncio
async def test_analyze_error_logs(log_agent, sample_error_logs):
    """Test error log analysis."""
    mock_result = LogAnalysisResult(
        patterns=[
            LogPattern(
                pattern="Connection timeout to database",
                frequency=3,
                severity="error",
                first_occurrence="2024-01-15 10:30:15",
                last_occurrence="2024-01-15 10:30:25",
                affected_services=["api", "db"],
            ),
            LogPattern(
                pattern="Retrying database connection",
                frequency=2,
                severity="warn",
                first_occurrence="2024-01-15 10:30:16",
                last_occurrence="2024-01-15 10:30:21",
            ),
        ],
        root_causes=[
            RootCause(
                description="Database connection pool exhaustion",
                confidence=0.85,
                evidence=[
                    "Multiple connection timeouts",
                    "Connection pool exhausted message",
                    "Service degradation warning",
                ],
                suggested_fix="Increase database connection pool size or investigate slow queries",
                impact="high",
            )
        ],
        anomalies_detected=1,
        total_errors=6,
        critical_errors=1,
        analysis_summary="Database connectivity issues causing service degradation",
    )

    with patch.object(
        log_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await log_agent.execute(logs=sample_error_logs, log_type="application")

        assert isinstance(result, LogAnalysisResult)
        assert len(result.patterns) == 2
        assert len(result.root_causes) == 1
        assert result.root_causes[0].confidence == 0.85
        assert result.total_errors == 6


@pytest.mark.asyncio
async def test_detect_anomalies(log_agent, sample_access_logs):
    """Test anomaly detection in logs."""
    mock_result = LogAnalysisResult(
        patterns=[
            LogPattern(
                pattern="GET /api/products HTTP/1.1\" 500",
                frequency=3,
                severity="error",
            )
        ],
        root_causes=[
            RootCause(
                description="API endpoint /api/products consistently failing",
                confidence=0.95,
                evidence=["3 consecutive 500 errors", "Same endpoint affected"],
                suggested_fix="Check /api/products endpoint implementation",
                impact="medium",
            )
        ],
        anomalies_detected=1,
        total_errors=3,
        critical_errors=0,
        analysis_summary="High error rate on /api/products endpoint",
    )

    with patch.object(
        log_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await log_agent.execute(logs=sample_access_logs, log_type="access")

        assert isinstance(result, LogAnalysisResult)
        assert result.anomalies_detected >= 1


@pytest.mark.asyncio
async def test_pattern_recognition(log_agent, sample_error_logs):
    """Test log pattern recognition."""
    mock_result = LogAnalysisResult(
        patterns=[
            LogPattern(
                pattern="Connection timeout",
                frequency=3,
                severity="error",
            ),
            LogPattern(
                pattern="Retrying",
                frequency=2,
                severity="warn",
            ),
        ],
        root_causes=[],
        anomalies_detected=0,
        total_errors=3,
        critical_errors=0,
        analysis_summary="Recurring connection issues",
    )

    with patch.object(
        log_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await log_agent.execute(logs=sample_error_logs)

        assert len(result.patterns) >= 2
        assert all(pattern.frequency > 0 for pattern in result.patterns)


@pytest.mark.asyncio
async def test_time_series_analysis(log_agent):
    """Test time-series log analysis."""
    logs_with_timestamps = """
2024-01-15 10:00:00 INFO Request processed
2024-01-15 10:05:00 INFO Request processed
2024-01-15 10:10:00 ERROR Request failed
2024-01-15 10:15:00 ERROR Request failed
2024-01-15 10:20:00 ERROR Request failed
2024-01-15 10:25:00 ERROR Request failed
"""

    mock_result = LogAnalysisResult(
        patterns=[],
        root_causes=[
            RootCause(
                description="Error rate spike starting at 10:10:00",
                confidence=0.90,
                evidence=["Normal operation until 10:10", "4 consecutive errors"],
                suggested_fix="Investigate what changed at 10:10",
                impact="high",
            )
        ],
        anomalies_detected=1,
        total_errors=4,
        critical_errors=0,
        analysis_summary="Sudden error rate increase detected",
    )

    with patch.object(
        log_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await log_agent.analyze_time_series(logs=logs_with_timestamps)

        assert isinstance(result, LogAnalysisResult)
        assert result.anomalies_detected > 0


@pytest.mark.asyncio
async def test_multi_service_correlation(log_agent):
    """Test correlation across multiple services."""
    multi_service_logs = """
2024-01-15 10:30:00 [auth] ERROR Token validation failed
2024-01-15 10:30:01 [api] ERROR Unauthorized request
2024-01-15 10:30:02 [gateway] ERROR 401 response
"""

    mock_result = LogAnalysisResult(
        patterns=[],
        root_causes=[
            RootCause(
                description="Authentication service failure cascading to downstream services",
                confidence=0.88,
                evidence=["Auth service error first", "Subsequent unauthorized errors"],
                suggested_fix="Investigate auth service token validation",
                impact="high",
            )
        ],
        anomalies_detected=1,
        total_errors=3,
        critical_errors=0,
        analysis_summary="Authentication failure affecting multiple services",
    )

    with patch.object(
        log_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await log_agent.execute(logs=multi_service_logs)

        assert len(result.root_causes) > 0
        assert result.root_causes[0].confidence > 0.8


@pytest.mark.asyncio
async def test_error_handling(log_agent):
    """Test error handling."""
    with patch.object(
        log_agent,
        "_generate_structured_response",
        side_effect=Exception("Analysis failed"),
    ):
        result = await log_agent.execute(logs="invalid logs")

        assert isinstance(result, LogAnalysisResult)
        assert result.total_errors == 0


def test_confidence_score_validation(log_agent):
    """Test root cause confidence score validation."""
    # Confidence should be between 0 and 1
    root_cause = RootCause(
        description="Test",
        confidence=0.75,
        evidence=[],
        suggested_fix="Test",
        impact="low",
    )

    assert 0 <= root_cause.confidence <= 1
