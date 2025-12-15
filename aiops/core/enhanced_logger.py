"""Enhanced structured logging with advanced features."""

import json
import time
import sys
import re
import random
import threading
import asyncio
from typing import Any, Dict, Optional, List, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from contextlib import contextmanager
from collections import deque
import traceback

from aiops.core.logger import get_logger

base_logger = get_logger(__name__)


# ==================== Sensitive Data Masking ====================

@dataclass
class MaskingRule:
    """Rule for masking sensitive data."""
    pattern: str
    replacement: str = "***REDACTED***"
    field_names: List[str] = field(default_factory=list)


class SensitiveDataMasker:
    """Mask sensitive data in logs."""

    # Default patterns to mask
    DEFAULT_PATTERNS = [
        # API keys and tokens
        MaskingRule(pattern=r'(api[_-]?key|token|secret|password|credential)["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', replacement=r'\1: ***REDACTED***'),
        # Credit card numbers
        MaskingRule(pattern=r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b', replacement='***CARD***'),
        # SSN
        MaskingRule(pattern=r'\b\d{3}-\d{2}-\d{4}\b', replacement='***SSN***'),
        # Email addresses (partial mask)
        MaskingRule(pattern=r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', replacement=r'***@\2'),
        # JWT tokens
        MaskingRule(pattern=r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*', replacement='***JWT***'),
        # Bearer tokens
        MaskingRule(pattern=r'Bearer\s+[a-zA-Z0-9_-]+', replacement='Bearer ***REDACTED***'),
    ]

    # Field names that should always be masked
    SENSITIVE_FIELDS = {
        'password', 'secret', 'token', 'api_key', 'apikey', 'auth',
        'authorization', 'credential', 'private_key', 'access_token',
        'refresh_token', 'session_id', 'ssn', 'credit_card',
    }

    def __init__(self, additional_rules: Optional[List[MaskingRule]] = None):
        """Initialize masker with optional additional rules."""
        self.rules = self.DEFAULT_PATTERNS.copy()
        if additional_rules:
            self.rules.extend(additional_rules)

        # Compile patterns
        self._compiled_patterns = [
            (re.compile(rule.pattern, re.IGNORECASE), rule.replacement)
            for rule in self.rules
        ]

    def mask_string(self, text: str) -> str:
        """Mask sensitive patterns in a string."""
        for pattern, replacement in self._compiled_patterns:
            text = pattern.sub(replacement, text)
        return text

    def mask_dict(self, data: Dict[str, Any], depth: int = 0, max_depth: int = 10) -> Dict[str, Any]:
        """Recursively mask sensitive fields in a dictionary."""
        if depth > max_depth:
            return data

        result = {}
        for key, value in data.items():
            key_lower = key.lower()

            # Check if field name is sensitive
            if any(sensitive in key_lower for sensitive in self.SENSITIVE_FIELDS):
                result[key] = "***REDACTED***"
            elif isinstance(value, dict):
                result[key] = self.mask_dict(value, depth + 1, max_depth)
            elif isinstance(value, list):
                result[key] = [
                    self.mask_dict(item, depth + 1, max_depth) if isinstance(item, dict)
                    else self.mask_string(str(item)) if isinstance(item, str)
                    else item
                    for item in value
                ]
            elif isinstance(value, str):
                result[key] = self.mask_string(value)
            else:
                result[key] = value

        return result


# ==================== Log Sampling ====================

class LogSampler:
    """Sample high-frequency log messages."""

    def __init__(
        self,
        sample_rate: float = 0.1,
        always_log_errors: bool = True,
        burst_limit: int = 100,
        burst_window: int = 60,
    ):
        """
        Initialize log sampler.

        Args:
            sample_rate: Rate of logs to keep (0-1)
            always_log_errors: Always log error level and above
            burst_limit: Max logs in burst window before sampling
            burst_window: Burst window in seconds
        """
        self.sample_rate = sample_rate
        self.always_log_errors = always_log_errors
        self.burst_limit = burst_limit
        self.burst_window = burst_window

        self._message_counts: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def _get_message_key(self, message: str) -> str:
        """Generate a key for the message (remove variable parts)."""
        # Remove numbers and UUIDs
        key = re.sub(r'\b\d+\b', 'N', message)
        key = re.sub(r'\b[0-9a-f-]{36}\b', 'UUID', key)
        return key[:100]  # Limit key length

    def should_log(self, message: str, level: str = "INFO") -> bool:
        """Determine if message should be logged."""
        # Always log errors
        if self.always_log_errors and level.upper() in ("ERROR", "CRITICAL", "EXCEPTION"):
            return True

        key = self._get_message_key(message)
        now = time.time()

        with self._lock:
            # Initialize or clean up old entries
            if key not in self._message_counts:
                self._message_counts[key] = []

            # Remove old entries
            cutoff = now - self.burst_window
            self._message_counts[key] = [t for t in self._message_counts[key] if t > cutoff]

            # Check if within burst limit
            if len(self._message_counts[key]) < self.burst_limit:
                self._message_counts[key].append(now)
                return True

            # Apply sampling
            if random.random() < self.sample_rate:
                self._message_counts[key].append(now)
                return True

            return False


# ==================== Context Propagation ====================

class LogContext:
    """Thread-local log context for context propagation."""

    _local = threading.local()
    _async_context: Dict[int, Dict[str, Any]] = {}

    @classmethod
    def get_context(cls) -> Dict[str, Any]:
        """Get current context."""
        # Check async context first
        try:
            task = asyncio.current_task()
            if task:
                task_id = id(task)
                return cls._async_context.get(task_id, {})
        except RuntimeError:
            pass

        # Fall back to thread local
        if not hasattr(cls._local, 'context'):
            cls._local.context = {}
        return cls._local.context

    @classmethod
    def set(cls, key: str, value: Any):
        """Set a context value."""
        context = cls.get_context()
        context[key] = value

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Get a context value."""
        return cls.get_context().get(key, default)

    @classmethod
    def clear(cls):
        """Clear current context."""
        try:
            task = asyncio.current_task()
            if task:
                task_id = id(task)
                cls._async_context.pop(task_id, None)
                return
        except RuntimeError:
            pass

        cls._local.context = {}

    @classmethod
    @contextmanager
    def scope(cls, **kwargs):
        """Context manager for temporary context."""
        old_values = {}
        context = cls.get_context()

        for key, value in kwargs.items():
            old_values[key] = context.get(key)
            context[key] = value

        try:
            yield
        finally:
            for key, value in old_values.items():
                if value is None:
                    context.pop(key, None)
                else:
                    context[key] = value

    @classmethod
    async def async_scope(cls, **kwargs):
        """Async context manager for temporary context."""
        task = asyncio.current_task()
        if task:
            task_id = id(task)
            if task_id not in cls._async_context:
                cls._async_context[task_id] = {}

            old_context = cls._async_context[task_id].copy()
            cls._async_context[task_id].update(kwargs)

            try:
                yield
            finally:
                cls._async_context[task_id] = old_context


# ==================== Performance Profiling ====================

@dataclass
class ProfileEntry:
    """A profiling entry."""
    name: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    parent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceProfiler:
    """Profile code execution for performance logging."""

    _local = threading.local()

    @classmethod
    def _get_stack(cls) -> List[ProfileEntry]:
        """Get current profiling stack."""
        if not hasattr(cls._local, 'stack'):
            cls._local.stack = []
        return cls._local.stack

    @classmethod
    @contextmanager
    def profile(cls, name: str, **metadata):
        """Context manager for profiling a code block."""
        stack = cls._get_stack()
        parent = stack[-1].name if stack else None

        entry = ProfileEntry(
            name=name,
            start_time=time.time(),
            parent=parent,
            metadata=metadata,
        )
        stack.append(entry)

        try:
            yield entry
        finally:
            entry.end_time = time.time()
            entry.duration_ms = (entry.end_time - entry.start_time) * 1000
            stack.pop()

            # Log if significant
            if entry.duration_ms > 100:  # Log if > 100ms
                base_logger.info(
                    f"Performance: {name} took {entry.duration_ms:.2f}ms",
                    extra={"profiling": True, "duration_ms": entry.duration_ms},
                )

    @classmethod
    def profile_async(cls, name: str, **metadata):
        """Decorator for profiling async functions."""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                with cls.profile(name, **metadata):
                    return await func(*args, **kwargs)
            return wrapper
        return decorator


# ==================== Log Aggregation ====================

class LogAggregator:
    """Aggregate and batch log messages."""

    def __init__(
        self,
        flush_interval: float = 5.0,
        max_batch_size: int = 100,
        flush_callback: Optional[Callable[[List[Dict]], None]] = None,
    ):
        """
        Initialize log aggregator.

        Args:
            flush_interval: Seconds between flushes
            max_batch_size: Maximum messages before forced flush
            flush_callback: Callback for flushing logs
        """
        self.flush_interval = flush_interval
        self.max_batch_size = max_batch_size
        self.flush_callback = flush_callback

        self._buffer: deque = deque(maxlen=max_batch_size * 2)
        self._lock = threading.Lock()
        self._last_flush = time.time()

        # Start background flush thread
        self._running = True
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()

    def add(self, log_entry: Dict[str, Any]):
        """Add a log entry to the buffer."""
        with self._lock:
            self._buffer.append(log_entry)

            if len(self._buffer) >= self.max_batch_size:
                self._flush()

    def _flush(self):
        """Flush buffered logs."""
        if not self._buffer:
            return

        logs = list(self._buffer)
        self._buffer.clear()
        self._last_flush = time.time()

        if self.flush_callback:
            try:
                self.flush_callback(logs)
            except Exception as e:
                base_logger.error(f"Log flush callback failed: {e}")

    def _flush_loop(self):
        """Background flush loop."""
        while self._running:
            time.sleep(1)
            with self._lock:
                if time.time() - self._last_flush >= self.flush_interval:
                    self._flush()

    def stop(self):
        """Stop the aggregator and flush remaining logs."""
        self._running = False
        with self._lock:
            self._flush()


# ==================== Enhanced Logger ====================

class EnhancedLogger:
    """Enhanced logger with all advanced features."""

    def __init__(
        self,
        name: str,
        masker: Optional[SensitiveDataMasker] = None,
        sampler: Optional[LogSampler] = None,
        enable_profiling: bool = True,
        json_output: bool = True,
    ):
        """
        Initialize enhanced logger.

        Args:
            name: Logger name
            masker: Sensitive data masker
            sampler: Log sampler
            enable_profiling: Enable performance profiling
            json_output: Output logs as JSON
        """
        self.name = name
        self.masker = masker or SensitiveDataMasker()
        self.sampler = sampler
        self.enable_profiling = enable_profiling
        self.json_output = json_output
        self._base_logger = get_logger(name)

    def _format_log(
        self,
        level: str,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
        exc_info: bool = False,
    ) -> Dict[str, Any]:
        """Format a log entry."""
        # Get context
        context = LogContext.get_context()

        # Build log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level.upper(),
            "logger": self.name,
            "message": self.masker.mask_string(message),
        }

        # Add context
        if context:
            log_entry["context"] = self.masker.mask_dict(context)

        # Add extra data
        if extra:
            log_entry["extra"] = self.masker.mask_dict(extra)

        # Add exception info
        if exc_info:
            log_entry["exception"] = traceback.format_exc()

        return log_entry

    def _should_log(self, message: str, level: str) -> bool:
        """Check if message should be logged."""
        if self.sampler:
            return self.sampler.should_log(message, level)
        return True

    def _log(self, level: str, message: str, **kwargs):
        """Internal log method."""
        if not self._should_log(message, level):
            return

        extra = kwargs.pop('extra', None)
        exc_info = kwargs.pop('exc_info', False)

        log_entry = self._format_log(level, message, extra, exc_info)

        # Output
        if self.json_output:
            output = json.dumps(log_entry)
        else:
            output = f"[{log_entry['timestamp']}] {log_entry['level']} - {log_entry['message']}"

        # Use base logger
        log_method = getattr(self._base_logger, level.lower(), self._base_logger.info)
        log_method(output)

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log("DEBUG", message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message."""
        self._log("ERROR", message, **kwargs)

    def exception(self, message: str, **kwargs):
        """Log exception with traceback."""
        self._log("ERROR", message, exc_info=True, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self._log("CRITICAL", message, **kwargs)

    @contextmanager
    def context(self, **kwargs):
        """Add context for a block of code."""
        with LogContext.scope(**kwargs):
            yield

    def profile(self, name: str, **metadata):
        """Profile a code block."""
        return PerformanceProfiler.profile(name, **metadata)


# ==================== Factory Functions ====================

_loggers: Dict[str, EnhancedLogger] = {}


def get_enhanced_logger(
    name: str,
    enable_sampling: bool = False,
    sample_rate: float = 0.1,
    json_output: bool = True,
) -> EnhancedLogger:
    """Get or create an enhanced logger."""
    if name not in _loggers:
        sampler = LogSampler(sample_rate=sample_rate) if enable_sampling else None
        _loggers[name] = EnhancedLogger(
            name=name,
            sampler=sampler,
            json_output=json_output,
        )
    return _loggers[name]
