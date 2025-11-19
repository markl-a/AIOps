"""Prometheus metrics for AIOps."""

from typing import Dict, Any
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
from functools import wraps
import time
from loguru import logger


# Create custom registry
registry = CollectorRegistry()

# Application info
app_info = Info("aiops_application", "AIOps application information", registry=registry)
app_info.info({
    "version": "0.1.0",
    "name": "aiops",
})

# ==================== API Metrics ====================

# HTTP request counter
http_requests_total = Counter(
    "aiops_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
    registry=registry,
)

# HTTP request duration
http_request_duration_seconds = Histogram(
    "aiops_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=registry,
)

# HTTP requests in progress
http_requests_in_progress = Gauge(
    "aiops_http_requests_in_progress",
    "HTTP requests currently being processed",
    ["method", "endpoint"],
    registry=registry,
)

# ==================== Agent Metrics ====================

# Agent execution counter
agent_executions_total = Counter(
    "aiops_agent_executions_total",
    "Total agent executions",
    ["agent_name", "operation", "status"],
    registry=registry,
)

# Agent execution duration
agent_execution_duration_seconds = Histogram(
    "aiops_agent_execution_duration_seconds",
    "Agent execution duration in seconds",
    ["agent_name", "operation"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
    registry=registry,
)

# Active agent executions
agent_executions_active = Gauge(
    "aiops_agent_executions_active",
    "Currently active agent executions",
    ["agent_name"],
    registry=registry,
)

# ==================== LLM Metrics ====================

# LLM request counter
llm_requests_total = Counter(
    "aiops_llm_requests_total",
    "Total LLM requests",
    ["provider", "model", "status"],
    registry=registry,
)

# LLM request duration
llm_request_duration_seconds = Histogram(
    "aiops_llm_request_duration_seconds",
    "LLM request duration in seconds",
    ["provider", "model"],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0),
    registry=registry,
)

# Token usage
llm_tokens_total = Counter(
    "aiops_llm_tokens_total",
    "Total LLM tokens consumed",
    ["provider", "model", "token_type"],
    registry=registry,
)

# LLM cost
llm_cost_total = Counter(
    "aiops_llm_cost_total",
    "Total LLM cost in USD",
    ["provider", "model"],
    registry=registry,
)

# ==================== Database Metrics ====================

# Database query counter
db_queries_total = Counter(
    "aiops_db_queries_total",
    "Total database queries",
    ["operation", "table"],
    registry=registry,
)

# Database query duration
db_query_duration_seconds = Histogram(
    "aiops_db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0),
    registry=registry,
)

# Database connections
db_connections_active = Gauge(
    "aiops_db_connections_active",
    "Active database connections",
    registry=registry,
)

db_connections_total = Gauge(
    "aiops_db_connections_total",
    "Total database connections in pool",
    registry=registry,
)

# ==================== Task Queue Metrics ====================

# Celery task counter
celery_tasks_total = Counter(
    "aiops_celery_tasks_total",
    "Total Celery tasks",
    ["task_name", "status"],
    registry=registry,
)

# Celery task duration
celery_task_duration_seconds = Histogram(
    "aiops_celery_task_duration_seconds",
    "Celery task duration in seconds",
    ["task_name"],
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0),
    registry=registry,
)

# Celery queue size
celery_queue_size = Gauge(
    "aiops_celery_queue_size",
    "Number of tasks in queue",
    ["queue_name"],
    registry=registry,
)

# ==================== Cache Metrics ====================

# Cache hits/misses
cache_operations_total = Counter(
    "aiops_cache_operations_total",
    "Total cache operations",
    ["operation", "result"],
    registry=registry,
)

# Cache operation duration
cache_operation_duration_seconds = Histogram(
    "aiops_cache_operation_duration_seconds",
    "Cache operation duration in seconds",
    ["operation"],
    buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1),
    registry=registry,
)

# ==================== Error Metrics ====================

# Error counter
errors_total = Counter(
    "aiops_errors_total",
    "Total errors",
    ["error_type", "component"],
    registry=registry,
)

# Error rate
error_rate = Gauge(
    "aiops_error_rate",
    "Current error rate (errors per minute)",
    ["component"],
    registry=registry,
)

# ==================== System Metrics ====================

# System health
system_health_status = Gauge(
    "aiops_system_health_status",
    "System health status (1=healthy, 0=unhealthy)",
    registry=registry,
)

# Active users
active_users = Gauge(
    "aiops_active_users",
    "Number of active users",
    registry=registry,
)

# API keys active
api_keys_active = Gauge(
    "aiops_api_keys_active",
    "Number of active API keys",
    registry=registry,
)


class MetricsCollector:
    """Metrics collector helper."""

    @staticmethod
    def track_http_request(method: str, endpoint: str, status_code: int, duration: float):
        """Track HTTP request metrics.

        Args:
            method: HTTP method
            endpoint: API endpoint
            status_code: Response status code
            duration: Request duration in seconds
        """
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code,
        ).inc()

        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint,
        ).observe(duration)

    @staticmethod
    def track_agent_execution(
        agent_name: str,
        operation: str,
        status: str,
        duration: float,
    ):
        """Track agent execution metrics.

        Args:
            agent_name: Name of the agent
            operation: Operation performed
            status: Execution status
            duration: Execution duration in seconds
        """
        agent_executions_total.labels(
            agent_name=agent_name,
            operation=operation,
            status=status,
        ).inc()

        agent_execution_duration_seconds.labels(
            agent_name=agent_name,
            operation=operation,
        ).observe(duration)

    @staticmethod
    def track_llm_request(
        provider: str,
        model: str,
        status: str,
        duration: float,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cost: float = 0.0,
    ):
        """Track LLM request metrics.

        Args:
            provider: LLM provider
            model: Model name
            status: Request status
            duration: Request duration
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            cost: Request cost
        """
        llm_requests_total.labels(
            provider=provider,
            model=model,
            status=status,
        ).inc()

        llm_request_duration_seconds.labels(
            provider=provider,
            model=model,
        ).observe(duration)

        if prompt_tokens > 0:
            llm_tokens_total.labels(
                provider=provider,
                model=model,
                token_type="prompt",
            ).inc(prompt_tokens)

        if completion_tokens > 0:
            llm_tokens_total.labels(
                provider=provider,
                model=model,
                token_type="completion",
            ).inc(completion_tokens)

        if cost > 0:
            llm_cost_total.labels(
                provider=provider,
                model=model,
            ).inc(cost)

    @staticmethod
    def track_error(error_type: str, component: str):
        """Track error occurrence.

        Args:
            error_type: Type of error
            component: Component where error occurred
        """
        errors_total.labels(
            error_type=error_type,
            component=component,
        ).inc()


def metrics_middleware(func):
    """Decorator to track API request metrics.

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        # Extract request info from kwargs
        request = kwargs.get("request")
        if not request:
            return await func(*args, **kwargs)

        method = request.method
        endpoint = request.url.path

        # Track in-progress
        http_requests_in_progress.labels(
            method=method,
            endpoint=endpoint,
        ).inc()

        start_time = time.time()
        status_code = 500  # Default to error

        try:
            response = await func(*args, **kwargs)
            status_code = getattr(response, "status_code", 200)
            return response
        finally:
            duration = time.time() - start_time

            # Track metrics
            MetricsCollector.track_http_request(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                duration=duration,
            )

            # Remove from in-progress
            http_requests_in_progress.labels(
                method=method,
                endpoint=endpoint,
            ).dec()

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start_time
        return result

    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


def get_metrics() -> bytes:
    """Get Prometheus metrics in text format.

    Returns:
        Metrics in Prometheus exposition format
    """
    return generate_latest(registry)


def get_metrics_content_type() -> str:
    """Get metrics content type.

    Returns:
        Content type string
    """
    return CONTENT_TYPE_LATEST
