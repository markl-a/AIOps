"""Observability module for AIOps."""

from aiops.observability.tracing import (
    init_tracing,
    get_tracer,
    trace_span,
    trace_agent_execution,
    trace_llm_request,
    add_span_event,
    set_span_attribute,
)

from aiops.observability.metrics import (
    MetricsCollector,
    get_metrics,
    get_metrics_content_type,
    metrics_middleware,
    # Individual metrics
    http_requests_total,
    agent_executions_total,
    llm_requests_total,
    system_health_status,
)

__all__ = [
    # Tracing
    "init_tracing",
    "get_tracer",
    "trace_span",
    "trace_agent_execution",
    "trace_llm_request",
    "add_span_event",
    "set_span_attribute",
    # Metrics
    "MetricsCollector",
    "get_metrics",
    "get_metrics_content_type",
    "metrics_middleware",
    "http_requests_total",
    "agent_executions_total",
    "llm_requests_total",
    "system_health_status",
]
