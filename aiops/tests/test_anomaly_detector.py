"""Tests for Anomaly Detector Agent."""

import pytest
from unittest.mock import AsyncMock, patch
from aiops.agents.anomaly_detector import (
    AnomalyDetectorAgent,
    AnomalyReport,
    Anomaly,
)


@pytest.fixture
def anomaly_agent():
    """Create anomaly detector agent."""
    return AnomalyDetectorAgent()


@pytest.fixture
def sample_time_series_data():
    """Sample time series metrics."""
    return {
        "timestamps": [
            "2024-01-15 10:00:00",
            "2024-01-15 10:05:00",
            "2024-01-15 10:10:00",
            "2024-01-15 10:15:00",
            "2024-01-15 10:20:00",
            "2024-01-15 10:25:00",
        ],
        "values": [100, 105, 102, 450, 108, 103],  # Spike at 10:15
        "metric_name": "response_time_ms",
    }


@pytest.fixture
def sample_system_metrics():
    """Sample system metrics."""
    return {
        "cpu_usage": [45, 47, 48, 92, 46, 45],  # Spike in CPU
        "memory_usage": [60, 61, 60, 88, 62, 60],  # Spike in memory
        "error_rate": [0.1, 0.2, 0.1, 5.2, 0.2, 0.1],  # Spike in errors
    }


@pytest.mark.asyncio
async def test_detect_spike_anomaly(anomaly_agent, sample_time_series_data):
    """Test spike anomaly detection."""
    mock_result = AnomalyReport(
        anomalies=[
            Anomaly(
                type="spike",
                metric="response_time_ms",
                timestamp="2024-01-15 10:15:00",
                value=450,
                baseline_value=105.0,
                severity="high",
                deviation_percent=328.6,
                confidence=0.95,
                description="Response time spike detected - 328% above baseline",
                possible_causes=["Traffic surge", "Slow database query", "Resource contention"],
            )
        ],
        total_anomalies=1,
        critical_anomalies=0,
        high_severity_anomalies=1,
        detection_confidence=0.95,
    )

    with patch.object(
        anomaly_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await anomaly_agent.execute(
            metrics=sample_time_series_data, detection_method="statistical"
        )

        assert isinstance(result, AnomalyReport)
        assert result.total_anomalies == 1
        assert result.anomalies[0].type == "spike"
        assert result.anomalies[0].confidence == 0.95


@pytest.mark.asyncio
async def test_detect_multi_metric_anomalies(anomaly_agent, sample_system_metrics):
    """Test multi-metric anomaly detection."""
    mock_result = AnomalyReport(
        anomalies=[
            Anomaly(
                type="correlated",
                metric="cpu_usage,memory_usage,error_rate",
                timestamp="Index 3",
                value=0,
                baseline_value=0,
                severity="critical",
                confidence=0.92,
                description="Simultaneous spike in CPU, memory, and error rate",
                possible_causes=["Application crash", "Resource leak", "DDoS attack"],
            )
        ],
        total_anomalies=1,
        critical_anomalies=1,
        high_severity_anomalies=0,
        detection_confidence=0.92,
    )

    with patch.object(
        anomaly_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await anomaly_agent.detect_multi_metric(metrics=sample_system_metrics)

        assert isinstance(result, AnomalyReport)
        assert result.critical_anomalies == 1
        assert "correlated" in result.anomalies[0].type.lower()


@pytest.mark.asyncio
async def test_detect_trend_anomaly(anomaly_agent):
    """Test trend anomaly detection."""
    trending_data = {
        "timestamps": [f"2024-01-{i:02d}" for i in range(1, 11)],
        "values": [100, 110, 120, 130, 140, 150, 160, 170, 180, 190],
        "metric_name": "memory_usage_percent",
    }

    mock_result = AnomalyReport(
        anomalies=[
            Anomaly(
                type="trend",
                metric="memory_usage_percent",
                timestamp="2024-01-01 to 2024-01-10",
                value=190,
                baseline_value=100,
                severity="medium",
                deviation_percent=90.0,
                confidence=0.88,
                description="Continuous upward trend in memory usage",
                possible_causes=["Memory leak", "Growing dataset without cleanup"],
            )
        ],
        total_anomalies=1,
        critical_anomalies=0,
        high_severity_anomalies=0,
        detection_confidence=0.88,
    )

    with patch.object(
        anomaly_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await anomaly_agent.execute(metrics=trending_data)

        assert any(anomaly.type == "trend" for anomaly in result.anomalies)


@pytest.mark.asyncio
async def test_detect_pattern_anomaly(anomaly_agent):
    """Test pattern change anomaly detection."""
    pattern_data = {
        "timestamps": [f"Hour {i}" for i in range(24)],
        "values": [10, 15, 20, 30, 40, 50, 45, 40, 35, 30, 25, 20,  # Normal daily pattern
                   10, 15, 20, 30, 15, 10, 8, 7, 5, 3, 2, 1],  # Pattern breaks at hour 16
        "metric_name": "request_count",
    }

    mock_result = AnomalyReport(
        anomalies=[
            Anomaly(
                type="pattern",
                metric="request_count",
                timestamp="Hour 16",
                value=15,
                baseline_value=40,
                severity="high",
                confidence=0.85,
                description="Expected daily traffic pattern disrupted",
                possible_causes=["Service outage", "Client-side issue", "Network problem"],
            )
        ],
        total_anomalies=1,
        critical_anomalies=0,
        high_severity_anomalies=1,
        detection_confidence=0.85,
    )

    with patch.object(
        anomaly_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await anomaly_agent.execute(metrics=pattern_data, detection_method="pattern")

        assert isinstance(result, AnomalyReport)


@pytest.mark.asyncio
async def test_seasonal_adjustment(anomaly_agent):
    """Test seasonal anomaly detection."""
    # Higher traffic on weekdays, lower on weekends
    weekly_pattern = {
        "timestamps": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "values": [1000, 1100, 1050, 1000, 900, 300, 250],
        "metric_name": "daily_transactions",
    }

    mock_result = AnomalyReport(
        anomalies=[],  # Weekend dip is expected, not anomalous
        total_anomalies=0,
        critical_anomalies=0,
        high_severity_anomalies=0,
        detection_confidence=0.90,
    )

    with patch.object(
        anomaly_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await anomaly_agent.execute(
            metrics=weekly_pattern, seasonal_pattern="weekly"
        )

        # Should not flag weekend as anomaly if seasonal pattern is specified
        assert result.total_anomalies == 0


@pytest.mark.asyncio
async def test_error_handling(anomaly_agent):
    """Test error handling."""
    with patch.object(
        anomaly_agent,
        "_generate_structured_response",
        side_effect=Exception("Detection failed"),
    ):
        result = await anomaly_agent.execute(metrics={})

        assert isinstance(result, AnomalyReport)
        assert result.total_anomalies == 0


def test_confidence_score_validation():
    """Test anomaly confidence score validation."""
    anomaly = Anomaly(
        type="spike",
        metric="test",
        timestamp="now",
        value=100,
        baseline_value=50,
        severity="high",
        confidence=0.85,
        description="Test anomaly",
    )

    assert 0 <= anomaly.confidence <= 1


def test_severity_levels():
    """Test valid severity levels."""
    valid_severities = ["low", "medium", "high", "critical"]

    for severity in valid_severities:
        anomaly = Anomaly(
            type="test",
            metric="test",
            timestamp="now",
            value=0,
            baseline_value=0,
            severity=severity,
            confidence=0.8,
            description="Test",
        )
        assert anomaly.severity in valid_severities
