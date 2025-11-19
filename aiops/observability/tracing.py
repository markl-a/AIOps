"""OpenTelemetry tracing integration for AIOps."""

from typing import Optional, Dict, Any
from contextlib import contextmanager
import os

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.trace import Status, StatusCode

from loguru import logger
from aiops.core.config import get_config


class TracingManager:
    """Manage OpenTelemetry tracing configuration."""

    def __init__(
        self,
        service_name: str = "aiops",
        service_version: str = "0.1.0",
        enable_console_exporter: bool = False,
        otlp_endpoint: Optional[str] = None,
    ):
        """Initialize tracing manager.

        Args:
            service_name: Name of the service
            service_version: Version of the service
            enable_console_exporter: Enable console span exporter
            otlp_endpoint: OTLP endpoint URL (e.g., http://jaeger:4317)
        """
        self.service_name = service_name
        self.service_version = service_version
        self.enable_console_exporter = enable_console_exporter
        self.otlp_endpoint = otlp_endpoint or os.getenv("OTLP_ENDPOINT")
        self.tracer_provider = None
        self.tracer = None

    def setup_tracing(self):
        """Setup OpenTelemetry tracing."""
        # Create resource
        resource = Resource(
            attributes={
                SERVICE_NAME: self.service_name,
                SERVICE_VERSION: self.service_version,
                "environment": os.getenv("ENVIRONMENT", "development"),
            }
        )

        # Create tracer provider
        self.tracer_provider = TracerProvider(resource=resource)

        # Add console exporter if enabled
        if self.enable_console_exporter:
            console_exporter = ConsoleSpanExporter()
            self.tracer_provider.add_span_processor(
                BatchSpanProcessor(console_exporter)
            )
            logger.info("OpenTelemetry console exporter enabled")

        # Add OTLP exporter if endpoint configured
        if self.otlp_endpoint:
            try:
                otlp_exporter = OTLPSpanExporter(endpoint=self.otlp_endpoint)
                self.tracer_provider.add_span_processor(
                    BatchSpanProcessor(otlp_exporter)
                )
                logger.info(f"OpenTelemetry OTLP exporter configured: {self.otlp_endpoint}")
            except Exception as e:
                logger.error(f"Failed to configure OTLP exporter: {e}")

        # Set global tracer provider
        trace.set_tracer_provider(self.tracer_provider)

        # Get tracer instance
        self.tracer = trace.get_tracer(__name__)

        logger.info(f"OpenTelemetry tracing initialized for service: {self.service_name}")

    def instrument_app(self, app):
        """Instrument FastAPI application.

        Args:
            app: FastAPI application instance
        """
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumentation enabled")

    def instrument_sqlalchemy(self, engine):
        """Instrument SQLAlchemy engine.

        Args:
            engine: SQLAlchemy engine instance
        """
        SQLAlchemyInstrumentor().instrument(engine=engine)
        logger.info("SQLAlchemy instrumentation enabled")

    def instrument_redis(self):
        """Instrument Redis client."""
        RedisInstrumentor().instrument()
        logger.info("Redis instrumentation enabled")

    def instrument_requests(self):
        """Instrument requests library."""
        RequestsInstrumentor().instrument()
        logger.info("Requests instrumentation enabled")

    def get_tracer(self):
        """Get tracer instance.

        Returns:
            Tracer instance
        """
        if self.tracer is None:
            self.tracer = trace.get_tracer(__name__)
        return self.tracer

    def shutdown(self):
        """Shutdown tracing."""
        if self.tracer_provider:
            self.tracer_provider.shutdown()
            logger.info("OpenTelemetry tracing shutdown")


# Global tracing manager
_tracing_manager: Optional[TracingManager] = None


def init_tracing(
    service_name: str = "aiops",
    service_version: str = "0.1.0",
    enable_console: bool = False,
    otlp_endpoint: Optional[str] = None,
) -> TracingManager:
    """Initialize OpenTelemetry tracing.

    Args:
        service_name: Name of the service
        service_version: Version of the service
        enable_console: Enable console exporter
        otlp_endpoint: OTLP endpoint URL

    Returns:
        TracingManager instance
    """
    global _tracing_manager

    config = get_config()

    # Get configuration from config if not provided
    if otlp_endpoint is None:
        otlp_endpoint = getattr(config, "otlp_endpoint", None)

    _tracing_manager = TracingManager(
        service_name=service_name,
        service_version=service_version,
        enable_console_exporter=enable_console,
        otlp_endpoint=otlp_endpoint,
    )

    _tracing_manager.setup_tracing()

    # Auto-instrument common libraries
    _tracing_manager.instrument_requests()
    _tracing_manager.instrument_redis()

    return _tracing_manager


def get_tracing_manager() -> Optional[TracingManager]:
    """Get global tracing manager.

    Returns:
        TracingManager instance or None
    """
    return _tracing_manager


def get_tracer():
    """Get tracer instance.

    Returns:
        Tracer instance
    """
    if _tracing_manager:
        return _tracing_manager.get_tracer()
    return trace.get_tracer(__name__)


@contextmanager
def trace_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
    record_exception: bool = True,
):
    """Context manager for tracing a span.

    Args:
        name: Span name
        attributes: Span attributes
        record_exception: Whether to record exceptions

    Yields:
        Span instance
    """
    tracer = get_tracer()

    with tracer.start_as_current_span(name) as span:
        # Add attributes
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)

        try:
            yield span
        except Exception as e:
            if record_exception:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
            raise


def trace_agent_execution(agent_name: str, operation: str):
    """Decorator to trace agent execution.

    Args:
        agent_name: Name of the agent
        operation: Operation being performed

    Returns:
        Decorated function
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            with trace_span(
                f"{agent_name}.{operation}",
                attributes={
                    "agent.name": agent_name,
                    "agent.operation": operation,
                },
            ) as span:
                result = await func(*args, **kwargs)

                # Add result metadata
                if hasattr(result, "__dict__"):
                    span.set_attribute("result.type", type(result).__name__)

                return result

        def sync_wrapper(*args, **kwargs):
            with trace_span(
                f"{agent_name}.{operation}",
                attributes={
                    "agent.name": agent_name,
                    "agent.operation": operation,
                },
            ) as span:
                result = func(*args, **kwargs)

                # Add result metadata
                if hasattr(result, "__dict__"):
                    span.set_attribute("result.type", type(result).__name__)

                return result

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def trace_llm_request(provider: str, model: str):
    """Decorator to trace LLM requests.

    Args:
        provider: LLM provider name
        model: Model name

    Returns:
        Decorated function
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            with trace_span(
                "llm.request",
                attributes={
                    "llm.provider": provider,
                    "llm.model": model,
                },
            ) as span:
                result = await func(*args, **kwargs)

                # Add token usage if available
                if hasattr(result, "usage"):
                    usage = result.usage
                    span.set_attribute("llm.prompt_tokens", getattr(usage, "prompt_tokens", 0))
                    span.set_attribute("llm.completion_tokens", getattr(usage, "completion_tokens", 0))
                    span.set_attribute("llm.total_tokens", getattr(usage, "total_tokens", 0))

                return result

        def sync_wrapper(*args, **kwargs):
            with trace_span(
                "llm.request",
                attributes={
                    "llm.provider": provider,
                    "llm.model": model,
                },
            ) as span:
                result = func(*args, **kwargs)

                # Add token usage if available
                if hasattr(result, "usage"):
                    usage = result.usage
                    span.set_attribute("llm.prompt_tokens", getattr(usage, "prompt_tokens", 0))
                    span.set_attribute("llm.completion_tokens", getattr(usage, "completion_tokens", 0))
                    span.set_attribute("llm.total_tokens", getattr(usage, "total_tokens", 0))

                return result

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def add_span_event(name: str, attributes: Optional[Dict[str, Any]] = None):
    """Add an event to the current span.

    Args:
        name: Event name
        attributes: Event attributes
    """
    span = trace.get_current_span()
    if span:
        span.add_event(name, attributes=attributes or {})


def set_span_attribute(key: str, value: Any):
    """Set an attribute on the current span.

    Args:
        key: Attribute key
        value: Attribute value
    """
    span = trace.get_current_span()
    if span:
        span.set_attribute(key, value)
