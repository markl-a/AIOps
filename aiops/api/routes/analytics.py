"""Analytics and Metrics Routes"""

from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import re

from aiops.core.structured_logger import get_structured_logger


logger = get_structured_logger(__name__)
router = APIRouter()

# Security: Allowed metric names (whitelist approach)
ALLOWED_METRIC_PATTERNS = [
    r'^[a-zA-Z0-9._-]+$',  # Alphanumeric with dots, underscores, and hyphens
]

def validate_metric_name(metric_name: str) -> bool:
    """Validate metric name against allowed patterns."""
    if not metric_name or len(metric_name) > 100:
        return False

    for pattern in ALLOWED_METRIC_PATTERNS:
        if re.match(pattern, metric_name):
            return True
    return False


# Response Models
class MetricDataPoint(BaseModel):
    """Single metric data point."""

    timestamp: datetime
    value: float
    labels: Optional[Dict[str, str]] = None


class MetricResponse(BaseModel):
    """Metric response."""

    metric_name: str
    data_points: List[MetricDataPoint]
    unit: str
    aggregation: str


class SystemMetrics(BaseModel):
    """System-wide metrics."""

    total_agents_executed: int
    total_llm_requests: int
    total_cost_usd: float
    average_execution_time_ms: float
    error_rate: float
    uptime_percentage: float


class AgentMetrics(BaseModel):
    """Metrics for a specific agent."""

    agent_type: str
    total_executions: int
    success_rate: float
    average_duration_ms: float
    total_cost_usd: float


@router.get("/metrics/system", response_model=SystemMetrics)
async def get_system_metrics():
    """Get system-wide metrics."""
    # Mock implementation
    return SystemMetrics(
        total_agents_executed=2533,
        total_llm_requests=15678,
        total_cost_usd=245.67,
        average_execution_time_ms=1250.5,
        error_rate=0.015,
        uptime_percentage=99.95,
    )


@router.get("/metrics/agents", response_model=List[AgentMetrics])
async def get_agent_metrics():
    """Get metrics for all agents."""
    # Mock implementation
    agents = [
        {
            "agent_type": "code_reviewer",
            "total_executions": 456,
            "success_rate": 0.985,
            "average_duration_ms": 2350.5,
            "total_cost_usd": 45.67,
        },
        {
            "agent_type": "security_scanner",
            "total_executions": 289,
            "success_rate": 0.992,
            "average_duration_ms": 3150.2,
            "total_cost_usd": 38.92,
        },
        {
            "agent_type": "k8s_optimizer",
            "total_executions": 123,
            "success_rate": 0.975,
            "average_duration_ms": 1850.8,
            "total_cost_usd": 15.45,
        },
    ]

    return [AgentMetrics(**a) for a in agents]


@router.get("/metrics/timeseries", response_model=List[MetricResponse])
async def get_timeseries_metrics(
    metric_names: List[str] = Query(..., description="Metric names to fetch", max_length=50),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    aggregation: str = Query("avg", regex="^(avg|sum|min|max|count)$"),
):
    """Get time series metrics."""
    # Validate number of metrics requested (prevent DoS)
    if len(metric_names) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot request more than 20 metrics at once"
        )

    # Validate each metric name
    for metric_name in metric_names:
        if not validate_metric_name(metric_name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid metric name: {metric_name}"
            )

    # Validate time range
    if not start_time:
        start_time = datetime.now() - timedelta(hours=24)
    if not end_time:
        end_time = datetime.now()

    # Prevent querying too far in the past (max 90 days)
    max_range = timedelta(days=90)
    if (end_time - start_time) > max_range:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Time range cannot exceed 90 days"
        )

    # Ensure start_time is before end_time
    if start_time >= end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_time must be before end_time"
        )

    # Mock implementation
    responses = []
    for metric_name in metric_names:
        # Generate mock data points
        data_points = []
        current_time = start_time
        while current_time <= end_time:
            data_points.append(
                MetricDataPoint(
                    timestamp=current_time,
                    value=85.5,  # Mock value
                    labels={"environment": "production"},
                )
            )
            current_time += timedelta(minutes=5)

        responses.append(
            MetricResponse(
                metric_name=metric_name,
                data_points=data_points[:100],  # Limit data points
                unit="percent" if "rate" in metric_name else "count",
                aggregation=aggregation,
            )
        )

    return responses


@router.get("/analytics/cost-breakdown")
async def get_cost_breakdown():
    """Get cost breakdown by provider and agent."""
    return {
        "total_cost_usd": 245.67,
        "by_provider": {
            "openai": 145.23,
            "anthropic": 78.45,
            "google": 21.99,
        },
        "by_agent": {
            "code_reviewer": 45.67,
            "security_scanner": 38.92,
            "k8s_optimizer": 15.45,
            "test_generator": 28.34,
            "performance_analyzer": 32.11,
            "other": 85.18,
        },
        "period": {
            "start": (datetime.now() - timedelta(days=30)).isoformat(),
            "end": datetime.now().isoformat(),
        },
    }


@router.get("/analytics/usage-trends")
async def get_usage_trends(days: int = Query(30, ge=1, le=90)):
    """Get usage trends over time."""
    # Validate days parameter
    if days < 1 or days > 90:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Days must be between 1 and 90"
        )

    # Mock implementation
    daily_data = []
    for i in range(days):
        date = datetime.now() - timedelta(days=days-i-1)
        daily_data.append({
            "date": date.date().isoformat(),
            "total_executions": 50 + i * 2,
            "total_llm_requests": 300 + i * 10,
            "total_cost_usd": 5.5 + i * 0.3,
            "average_response_time_ms": 1200 + (i % 7) * 50,
        })

    return {
        "period_days": days,
        "daily_data": daily_data,
        "trends": {
            "executions_growth": "+15.2%",
            "cost_growth": "+8.5%",
            "response_time_trend": "stable",
        },
    }


@router.get("/analytics/top-errors")
async def get_top_errors(limit: int = Query(10, ge=1, le=100)):
    """Get most common errors."""
    # Validate limit parameter
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 100"
        )

    # Mock implementation
    errors = [
        {
            "error_type": "LLMTimeoutError",
            "count": 45,
            "last_occurred": datetime.now(),
            "affected_agents": ["code_reviewer", "test_generator"],
        },
        {
            "error_type": "AgentValidationError",
            "count": 23,
            "last_occurred": datetime.now() - timedelta(hours=2),
            "affected_agents": ["k8s_optimizer"],
        },
        {
            "error_type": "LLMRateLimitError",
            "count": 12,
            "last_occurred": datetime.now() - timedelta(hours=5),
            "affected_agents": ["security_scanner", "performance_analyzer"],
        },
    ]

    return {"errors": errors[:limit]}


@router.get("/analytics/performance")
async def get_performance_metrics():
    """Get performance metrics."""
    return {
        "response_times": {
            "p50_ms": 1150.5,
            "p90_ms": 2350.2,
            "p95_ms": 3150.8,
            "p99_ms": 4850.3,
        },
        "throughput": {
            "requests_per_second": 12.5,
            "agents_per_minute": 8.3,
        },
        "resource_usage": {
            "cpu_percent": 45.2,
            "memory_percent": 62.8,
            "disk_percent": 38.1,
        },
        "cache_stats": {
            "hit_rate": 0.85,
            "miss_rate": 0.15,
            "total_requests": 5678,
        },
    }
