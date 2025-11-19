"""Enhanced structured logging system with trace IDs and context."""

import sys
import json
import uuid
from typing import Optional, Dict, Any
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from loguru import logger

from aiops.core.config import get_config


# Context variable for request/trace ID
_trace_id: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
_request_context: ContextVar[Dict[str, Any]] = ContextVar("request_context", default={})


class StructuredLogger:
    """Structured logger with trace ID and context support."""

    def __init__(self, name: str = __name__):
        """Initialize structured logger.

        Args:
            name: Logger name
        """
        self.name = name
        self.logger = logger.bind(logger_name=name)

    def _add_context(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Add trace ID and context to log record.

        Args:
            extra: Additional context

        Returns:
            Complete context dictionary
        """
        context = {
            "trace_id": get_trace_id(),
            "timestamp_iso": datetime.utcnow().isoformat(),
            "logger_name": self.name,
        }

        # Add request context
        request_ctx = _request_context.get()
        if request_ctx:
            context.update(request_ctx)

        # Add custom extra
        if extra:
            context.update(extra)

        return context

    def debug(self, message: str, **kwargs):
        """Log debug message.

        Args:
            message: Log message
            **kwargs: Additional context
        """
        context = self._add_context(kwargs)
        self.logger.bind(**context).debug(message)

    def info(self, message: str, **kwargs):
        """Log info message.

        Args:
            message: Log message
            **kwargs: Additional context
        """
        context = self._add_context(kwargs)
        self.logger.bind(**context).info(message)

    def warning(self, message: str, **kwargs):
        """Log warning message.

        Args:
            message: Log message
            **kwargs: Additional context
        """
        context = self._add_context(kwargs)
        self.logger.bind(**context).warning(message)

    def error(self, message: str, **kwargs):
        """Log error message.

        Args:
            message: Log message
            **kwargs: Additional context
        """
        context = self._add_context(kwargs)
        self.logger.bind(**context).error(message)

    def critical(self, message: str, **kwargs):
        """Log critical message.

        Args:
            message: Log message
            **kwargs: Additional context
        """
        context = self._add_context(kwargs)
        self.logger.bind(**context).critical(message)

    def exception(self, message: str, exc_info=True, **kwargs):
        """Log exception with traceback.

        Args:
            message: Log message
            exc_info: Include exception info
            **kwargs: Additional context
        """
        context = self._add_context(kwargs)
        if exc_info:
            self.logger.bind(**context).exception(message)
        else:
            self.logger.bind(**context).error(message)

    def log_agent_execution(
        self,
        agent_name: str,
        operation: str,
        status: str,
        duration_ms: Optional[float] = None,
        **kwargs,
    ):
        """Log agent execution.

        Args:
            agent_name: Name of the agent
            operation: Operation performed
            status: Status (started, completed, failed)
            duration_ms: Execution duration in milliseconds
            **kwargs: Additional context
        """
        context = {
            "agent_name": agent_name,
            "operation": operation,
            "status": status,
            "event_type": "agent_execution",
        }

        if duration_ms is not None:
            context["duration_ms"] = duration_ms

        context.update(kwargs)

        level = "info" if status == "completed" else "error" if status == "failed" else "debug"
        message = f"Agent {agent_name}.{operation}: {status}"

        getattr(self, level)(message, **context)

    def log_llm_request(
        self,
        provider: str,
        model: str,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_cost: Optional[float] = None,
        duration_ms: Optional[float] = None,
        **kwargs,
    ):
        """Log LLM request.

        Args:
            provider: LLM provider
            model: Model name
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            total_cost: Total cost
            duration_ms: Request duration
            **kwargs: Additional context
        """
        context = {
            "provider": provider,
            "model": model,
            "event_type": "llm_request",
        }

        if prompt_tokens is not None:
            context["prompt_tokens"] = prompt_tokens
        if completion_tokens is not None:
            context["completion_tokens"] = completion_tokens
        if total_cost is not None:
            context["total_cost"] = total_cost
        if duration_ms is not None:
            context["duration_ms"] = duration_ms

        context.update(kwargs)

        self.info(f"LLM request to {provider}/{model}", **context)

    def log_api_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration_ms: float,
        user_id: Optional[str] = None,
        **kwargs,
    ):
        """Log API request.

        Args:
            method: HTTP method
            endpoint: API endpoint
            status_code: HTTP status code
            duration_ms: Request duration
            user_id: User ID
            **kwargs: Additional context
        """
        context = {
            "method": method,
            "endpoint": endpoint,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "event_type": "api_request",
        }

        if user_id:
            context["user_id"] = user_id

        context.update(kwargs)

        level = "info" if 200 <= status_code < 400 else "warning" if status_code < 500 else "error"
        message = f"{method} {endpoint} {status_code} ({duration_ms:.2f}ms)"

        getattr(self, level)(message, **context)


def setup_structured_logger(
    log_level: str = "INFO",
    enable_json: bool = False,
    log_file: Optional[str] = None,
):
    """Setup structured logging system.

    Args:
        log_level: Logging level
        enable_json: Whether to enable JSON output
        log_file: Path to log file
    """
    config = get_config()

    # Remove default logger
    logger.remove()

    # JSON format for structured logging
    def json_formatter(record):
        """Format log record as JSON."""
        log_record = {
            "timestamp": record["time"].isoformat(),
            "level": record["level"].name,
            "logger": record["extra"].get("logger_name", record["name"]),
            "message": record["message"],
            "trace_id": record["extra"].get("trace_id"),
            "file": record["file"].name,
            "function": record["function"],
            "line": record["line"],
        }

        # Add all extra fields
        for key, value in record["extra"].items():
            if key not in ["logger_name", "trace_id"] and not key.startswith("_"):
                log_record[key] = value

        # Add exception info if present
        if record["exception"]:
            log_record["exception"] = {
                "type": record["exception"].type.__name__,
                "value": str(record["exception"].value),
                "traceback": record["exception"].traceback,
            }

        return json.dumps(log_record) + "\n"

    # Human-readable format
    def human_formatter(record):
        """Format log record for humans."""
        trace_id = record["extra"].get("trace_id", "no-trace")
        agent_name = record["extra"].get("agent_name", "")
        event_type = record["extra"].get("event_type", "")

        extra_parts = []
        if agent_name:
            extra_parts.append(f"agent={agent_name}")
        if event_type:
            extra_parts.append(f"type={event_type}")

        extra_str = f" [{', '.join(extra_parts)}]" if extra_parts else ""

        return (
            f"<green>{record['time']:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            f"<level>{record['level'].name: <8}</level> | "
            f"<cyan>[{trace_id[:8]}]</cyan> | "
            f"<cyan>{record['extra'].get('logger_name', record['name'])}</cyan>"
            f"{extra_str} - "
            f"<level>{record['message']}</level>\n"
        )

    # Console output
    logger.add(
        sys.stderr,
        level=log_level,
        format=json_formatter if enable_json else human_formatter,
        colorize=not enable_json,
    )

    # File output (always JSON for parsing)
    log_path = log_file or "logs/aiops_{time:YYYY-MM-DD}.log"
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)

    logger.add(
        log_path,
        rotation="1 day",
        retention="30 days",
        level="DEBUG",
        format=json_formatter,
        compression="zip",
    )

    # Separate error log
    logger.add(
        "logs/aiops_errors_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="90 days",
        level="ERROR",
        format=json_formatter,
        compression="zip",
    )

    logger.info("Structured logging initialized", log_level=log_level, json_output=enable_json)


def get_structured_logger(name: str = __name__) -> StructuredLogger:
    """Get structured logger instance.

    Args:
        name: Logger name

    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name=name)


def generate_trace_id() -> str:
    """Generate a new trace ID.

    Returns:
        UUID-based trace ID
    """
    return str(uuid.uuid4())


def get_trace_id() -> str:
    """Get current trace ID or generate a new one.

    Returns:
        Trace ID
    """
    trace_id = _trace_id.get()
    if trace_id is None:
        trace_id = generate_trace_id()
        set_trace_id(trace_id)
    return trace_id


def set_trace_id(trace_id: str):
    """Set trace ID for current context.

    Args:
        trace_id: Trace ID to set
    """
    _trace_id.set(trace_id)


def clear_trace_id():
    """Clear trace ID from current context."""
    _trace_id.set(None)


def set_request_context(**kwargs):
    """Set request context variables.

    Args:
        **kwargs: Context variables to set
    """
    current = _request_context.get().copy()
    current.update(kwargs)
    _request_context.set(current)


def clear_request_context():
    """Clear request context."""
    _request_context.set({})


def get_request_context() -> Dict[str, Any]:
    """Get current request context.

    Returns:
        Request context dictionary
    """
    return _request_context.get().copy()


# Context managers
class TraceContext:
    """Context manager for trace IDs."""

    def __init__(self, trace_id: Optional[str] = None):
        """Initialize trace context.

        Args:
            trace_id: Trace ID (generated if not provided)
        """
        self.trace_id = trace_id or generate_trace_id()
        self.previous_trace_id = None

    def __enter__(self):
        """Enter context."""
        self.previous_trace_id = _trace_id.get()
        set_trace_id(self.trace_id)
        return self.trace_id

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        if self.previous_trace_id:
            set_trace_id(self.previous_trace_id)
        else:
            clear_trace_id()


class RequestContext:
    """Context manager for request context."""

    def __init__(self, **context):
        """Initialize request context.

        Args:
            **context: Context variables
        """
        self.context = context
        self.previous_context = None

    def __enter__(self):
        """Enter context."""
        self.previous_context = get_request_context()
        set_request_context(**self.context)
        return self.context

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        _request_context.set(self.previous_context)
