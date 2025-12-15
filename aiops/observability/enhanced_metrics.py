"""Enhanced Prometheus metrics for comprehensive AIOps monitoring."""

import time
import threading
from typing import Dict, Any, Optional, List, Callable
from functools import wraps
from dataclasses import dataclass
from enum import Enum

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Summary,
    Info,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

from aiops.core.logger import get_logger

logger = get_logger(__name__)

# Create custom registry
enhanced_registry = CollectorRegistry()


# ==================== Application Info ====================

app_info = Info(
    "aiops_app",
    "AIOps application information",
    registry=enhanced_registry,
)
app_info.info({
    "version": "1.0.0",
    "name": "aiops",
    "environment": "production",
})

# ==================== Agent Performance Metrics ====================

# Per-agent execution histogram with detailed buckets
agent_execution_histogram = Histogram(
    "aiops_agent_execution_duration_histogram_seconds",
    "Detailed agent execution duration distribution",
    ["agent_name", "operation", "status"],
    buckets=(0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, 15.0, 30.0, 45.0, 60.0, 120.0),
    registry=enhanced_registry,
)

# Agent success/failure summary
agent_success_rate = Gauge(
    "aiops_agent_success_rate",
    "Agent success rate (0-1)",
    ["agent_name"],
    registry=enhanced_registry,
)

# Agent queue depth
agent_queue_depth = Gauge(
    "aiops_agent_queue_depth",
    "Number of pending agent executions",
    ["agent_name"],
    registry=enhanced_registry,
)

# Agent memory usage estimate
agent_memory_bytes = Gauge(
    "aiops_agent_memory_bytes",
    "Estimated memory usage by agent",
    ["agent_name"],
    registry=enhanced_registry,
)

# ==================== LLM Provider Metrics ====================

# Provider switch counter
llm_provider_switches = Counter(
    "aiops_llm_provider_switches_total",
    "Number of provider switches (failover events)",
    ["from_provider", "to_provider", "reason"],
    registry=enhanced_registry,
)

# Provider availability gauge
llm_provider_available = Gauge(
    "aiops_llm_provider_available",
    "Provider availability status (1=available, 0=unavailable)",
    ["provider"],
    registry=enhanced_registry,
)

# Provider latency percentiles
llm_provider_latency_summary = Summary(
    "aiops_llm_provider_latency_seconds",
    "LLM provider request latency",
    ["provider", "model"],
    registry=enhanced_registry,
)

# Token throughput
llm_tokens_per_second = Gauge(
    "aiops_llm_tokens_per_second",
    "Token processing throughput",
    ["provider", "model", "token_type"],
    registry=enhanced_registry,
)

# Cost tracking by time bucket
llm_cost_hourly = Gauge(
    "aiops_llm_cost_hourly_usd",
    "Hourly LLM cost in USD",
    ["provider", "model"],
    registry=enhanced_registry,
)

# ==================== Cache Metrics ====================

# Cache hit rate gauge
cache_hit_rate = Gauge(
    "aiops_cache_hit_rate",
    "Cache hit rate (0-1)",
    ["cache_type"],
    registry=enhanced_registry,
)

# Semantic cache specific metrics
semantic_cache_similarity = Histogram(
    "aiops_semantic_cache_similarity",
    "Similarity scores for semantic cache matches",
    ["match_type"],
    buckets=(0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.99, 1.0),
    registry=enhanced_registry,
)

# Cache memory usage
cache_memory_bytes = Gauge(
    "aiops_cache_memory_bytes",
    "Cache memory usage in bytes",
    ["cache_type"],
    registry=enhanced_registry,
)

# Cache evictions
cache_evictions = Counter(
    "aiops_cache_evictions_total",
    "Total cache evictions",
    ["cache_type", "reason"],
    registry=enhanced_registry,
)

# ==================== API Endpoint Metrics ====================

# Endpoint response time percentiles
api_endpoint_latency = Summary(
    "aiops_api_endpoint_latency_seconds",
    "API endpoint latency by percentile",
    ["method", "endpoint", "status_code"],
    registry=enhanced_registry,
)

# Endpoint error rate
api_endpoint_error_rate = Gauge(
    "aiops_api_endpoint_error_rate",
    "API endpoint error rate (0-1)",
    ["method", "endpoint"],
    registry=enhanced_registry,
)

# Request payload size
api_request_size_bytes = Histogram(
    "aiops_api_request_size_bytes",
    "API request payload size",
    ["method", "endpoint"],
    buckets=(100, 500, 1000, 5000, 10000, 50000, 100000, 500000, 1000000),
    registry=enhanced_registry,
)

# Response payload size
api_response_size_bytes = Histogram(
    "aiops_api_response_size_bytes",
    "API response payload size",
    ["method", "endpoint"],
    buckets=(100, 500, 1000, 5000, 10000, 50000, 100000, 500000, 1000000),
    registry=enhanced_registry,
)

# ==================== Rate Limiting Metrics ====================

# Rate limit hits
rate_limit_hits = Counter(
    "aiops_rate_limit_hits_total",
    "Total rate limit violations",
    ["identifier_type", "endpoint"],
    registry=enhanced_registry,
)

# Current rate utilization
rate_limit_utilization = Gauge(
    "aiops_rate_limit_utilization",
    "Current rate limit utilization (0-1)",
    ["identifier_type"],
    registry=enhanced_registry,
)

# ==================== Circuit Breaker Metrics ====================

# Circuit breaker state
circuit_breaker_state = Gauge(
    "aiops_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=half-open, 2=open)",
    ["circuit_name"],
    registry=enhanced_registry,
)

# Circuit breaker transitions
circuit_breaker_transitions = Counter(
    "aiops_circuit_breaker_transitions_total",
    "Circuit breaker state transitions",
    ["circuit_name", "from_state", "to_state"],
    registry=enhanced_registry,
)

# ==================== Error Classification Metrics ====================

# Error counter by category
errors_by_category = Counter(
    "aiops_errors_by_category_total",
    "Errors classified by category",
    ["category", "subcategory", "component"],
    registry=enhanced_registry,
)

# Error categories
class ErrorCategory(Enum):
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RATE_LIMIT = "rate_limit"
    LLM_ERROR = "llm_error"
    DATABASE = "database"
    NETWORK = "network"
    INTERNAL = "internal"
    EXTERNAL_SERVICE = "external_service"

# ==================== SLA Metrics ====================

# SLA compliance gauge
sla_compliance = Gauge(
    "aiops_sla_compliance",
    "SLA compliance rate (0-1)",
    ["sla_type"],
    registry=enhanced_registry,
)

# Response time SLO breaches
slo_response_time_breaches = Counter(
    "aiops_slo_response_time_breaches_total",
    "SLO response time breaches",
    ["endpoint", "threshold_ms"],
    registry=enhanced_registry,
)

# Availability SLO
slo_availability = Gauge(
    "aiops_slo_availability",
    "Service availability (0-1)",
    registry=enhanced_registry,
)

# ==================== Resource Usage Metrics ====================

# Active connections
active_connections = Gauge(
    "aiops_active_connections",
    "Number of active connections",
    ["connection_type"],
    registry=enhanced_registry,
)

# Worker pool utilization
worker_pool_utilization = Gauge(
    "aiops_worker_pool_utilization",
    "Worker pool utilization (0-1)",
    ["pool_name"],
    registry=enhanced_registry,
)

# Background task count
background_tasks = Gauge(
    "aiops_background_tasks",
    "Number of background tasks",
    ["task_type", "status"],
    registry=enhanced_registry,
)


class EnhancedMetricsCollector:
    """Collector for enhanced metrics with helper methods."""

    _instance = None
    _lock = threading.Lock()

    # Track agent statistics
    _agent_stats: Dict[str, Dict[str, int]] = {}

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def track_agent_execution(
        cls,
        agent_name: str,
        operation: str,
        status: str,
        duration: float,
    ):
        """Track detailed agent execution metrics."""
        # Record histogram
        agent_execution_histogram.labels(
            agent_name=agent_name,
            operation=operation,
            status=status,
        ).observe(duration)

        # Update success rate tracking
        with cls._lock:
            if agent_name not in cls._agent_stats:
                cls._agent_stats[agent_name] = {"success": 0, "total": 0}

            cls._agent_stats[agent_name]["total"] += 1
            if status == "success":
                cls._agent_stats[agent_name]["success"] += 1

            # Update success rate gauge
            stats = cls._agent_stats[agent_name]
            rate = stats["success"] / stats["total"] if stats["total"] > 0 else 0
            agent_success_rate.labels(agent_name=agent_name).set(rate)

    @classmethod
    def track_llm_provider_switch(
        cls,
        from_provider: str,
        to_provider: str,
        reason: str,
    ):
        """Track LLM provider failover events."""
        llm_provider_switches.labels(
            from_provider=from_provider,
            to_provider=to_provider,
            reason=reason,
        ).inc()

        # Update availability gauges
        llm_provider_available.labels(provider=from_provider).set(0)
        llm_provider_available.labels(provider=to_provider).set(1)

    @classmethod
    def track_cache_operation(
        cls,
        cache_type: str,
        hit: bool,
        similarity: Optional[float] = None,
    ):
        """Track cache operation with optional semantic similarity."""
        if similarity is not None:
            semantic_cache_similarity.labels(
                match_type="semantic" if hit else "miss",
            ).observe(similarity)

    @classmethod
    def track_api_request(
        cls,
        method: str,
        endpoint: str,
        status_code: int,
        duration: float,
        request_size: int = 0,
        response_size: int = 0,
    ):
        """Track API request with comprehensive metrics."""
        api_endpoint_latency.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code),
        ).observe(duration)

        if request_size > 0:
            api_request_size_bytes.labels(
                method=method,
                endpoint=endpoint,
            ).observe(request_size)

        if response_size > 0:
            api_response_size_bytes.labels(
                method=method,
                endpoint=endpoint,
            ).observe(response_size)

    @classmethod
    def track_rate_limit_hit(
        cls,
        identifier_type: str,
        endpoint: str,
    ):
        """Track rate limit violation."""
        rate_limit_hits.labels(
            identifier_type=identifier_type,
            endpoint=endpoint,
        ).inc()

    @classmethod
    def track_circuit_breaker(
        cls,
        circuit_name: str,
        state: str,
        from_state: Optional[str] = None,
    ):
        """Track circuit breaker state and transitions."""
        state_map = {"closed": 0, "half_open": 1, "open": 2}
        circuit_breaker_state.labels(circuit_name=circuit_name).set(
            state_map.get(state, 0)
        )

        if from_state:
            circuit_breaker_transitions.labels(
                circuit_name=circuit_name,
                from_state=from_state,
                to_state=state,
            ).inc()

    @classmethod
    def track_error(
        cls,
        category: ErrorCategory,
        subcategory: str,
        component: str,
    ):
        """Track categorized errors."""
        errors_by_category.labels(
            category=category.value,
            subcategory=subcategory,
            component=component,
        ).inc()

    @classmethod
    def update_sla_metrics(
        cls,
        sla_type: str,
        compliance_rate: float,
    ):
        """Update SLA compliance metrics."""
        sla_compliance.labels(sla_type=sla_type).set(compliance_rate)


def track_execution_time(
    agent_name: Optional[str] = None,
    operation: Optional[str] = None,
):
    """
    Decorator to track function execution time.

    Args:
        agent_name: Optional agent name for metrics
        operation: Optional operation name for metrics
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time
                if agent_name:
                    EnhancedMetricsCollector.track_agent_execution(
                        agent_name=agent_name,
                        operation=operation or func.__name__,
                        status=status,
                        duration=duration,
                    )

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            try:
                result = func(*args, **kwargs)
                return result
            except Exception:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time
                if agent_name:
                    EnhancedMetricsCollector.track_agent_execution(
                        agent_name=agent_name,
                        operation=operation or func.__name__,
                        status=status,
                        duration=duration,
                    )

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def get_enhanced_metrics() -> bytes:
    """Get enhanced Prometheus metrics in text format."""
    return generate_latest(enhanced_registry)


def get_enhanced_metrics_content_type() -> str:
    """Get metrics content type."""
    return CONTENT_TYPE_LATEST
