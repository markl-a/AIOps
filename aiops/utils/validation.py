"""Shared validation utilities for API routes and agents."""

import re
import json
from typing import Any, Dict, Optional


# Security: Maximum size for input data (1MB)
MAX_INPUT_DATA_SIZE = 1024 * 1024  # 1MB in bytes

# Allowed patterns
ALLOWED_METRIC_PATTERNS = [
    r'^[a-zA-Z0-9._-]+$',  # Alphanumeric with dots, underscores, and hyphens
]

ALLOWED_AGENT_TYPE_PATTERN = r'^[a-zA-Z0-9_-]+$'


def validate_agent_type(agent_type: str) -> str:
    """
    Validate agent type string.

    Args:
        agent_type: Agent type to validate

    Returns:
        Validated agent type

    Raises:
        ValueError: If agent type is invalid
    """
    # Strip whitespace
    agent_type = agent_type.strip()

    # Only allow alphanumeric, underscores, and hyphens
    if not re.match(ALLOWED_AGENT_TYPE_PATTERN, agent_type):
        raise ValueError("Agent type contains invalid characters")

    if len(agent_type) < 1 or len(agent_type) > 100:
        raise ValueError("Agent type must be between 1 and 100 characters")

    return agent_type


def validate_callback_url(url: Optional[str]) -> Optional[str]:
    """
    Validate callback URL for SSRF protection.

    Args:
        url: URL to validate

    Returns:
        Validated URL or None

    Raises:
        ValueError: If URL is invalid or potentially dangerous
    """
    if url is None:
        return None

    # Strip whitespace
    url = url.strip()

    if len(url) > 500:
        raise ValueError("Callback URL too long (max 500 characters)")

    # Validate URL format (basic check)
    if not re.match(r'^https?://', url):
        raise ValueError("Callback URL must start with http:// or https://")

    # Prevent SSRF - disallow localhost, internal IPs, etc.
    dangerous_patterns = [
        r'localhost',
        r'127\.0\.0\.',
        r'0\.0\.0\.0',
        r'10\.\d+\.\d+\.\d+',      # Private 10.x.x.x
        r'172\.(1[6-9]|2[0-9]|3[01])\.\d+\.\d+',  # Private 172.16-31.x.x
        r'192\.168\.\d+\.\d+',     # Private 192.168.x.x
        r'169\.254\.\d+\.\d+',     # Link-local
        r'\[::\]',                  # IPv6 localhost
        r'\[::1\]',                 # IPv6 localhost
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, url, re.IGNORECASE):
            raise ValueError(
                "Callback URL cannot point to internal/local addresses (SSRF protection)"
            )

    return url


def validate_input_data_size(input_data: Dict[str, Any], max_size: int = MAX_INPUT_DATA_SIZE) -> None:
    """
    Validate that input data is not too large.

    Args:
        input_data: Data to validate
        max_size: Maximum allowed size in bytes

    Raises:
        ValueError: If data is too large or not serializable
    """
    try:
        json_str = json.dumps(input_data)
        size_bytes = len(json_str.encode('utf-8'))

        if size_bytes > max_size:
            raise ValueError(
                f"Input data too large: {size_bytes} bytes (max: {max_size} bytes)"
            )
    except (TypeError, ValueError) as e:
        if "Input data too large" in str(e):
            raise
        raise ValueError("Input data must be JSON serializable")


def validate_input_data_keys(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate input data keys to prevent injection attacks.

    Args:
        input_data: Data to validate

    Returns:
        Validated input data

    Raises:
        ValueError: If keys are invalid
    """
    for key in input_data.keys():
        if not isinstance(key, str):
            raise ValueError("All input data keys must be strings")

        # Limit key length
        if len(key) > 255:
            raise ValueError(f"Input data key too long: {key[:50]}...")

        # Only allow safe characters in keys
        if not re.match(r'^[a-zA-Z0-9_.-]+$', key):
            raise ValueError(f"Invalid characters in input data key: {key}")

    return input_data


def validate_metric_name(metric_name: str) -> bool:
    """
    Validate metric name against allowed patterns.

    Args:
        metric_name: Metric name to validate

    Returns:
        True if valid, False otherwise
    """
    if not metric_name or len(metric_name) > 100:
        return False

    for pattern in ALLOWED_METRIC_PATTERNS:
        if re.match(pattern, metric_name):
            return True
    return False


def validate_severity(severity: str) -> str:
    """
    Validate severity level.

    Args:
        severity: Severity level to validate

    Returns:
        Validated severity level (lowercase)

    Raises:
        ValueError: If severity is invalid
    """
    allowed_severities = ['critical', 'high', 'medium', 'low', 'info']
    severity_lower = severity.lower().strip()

    if severity_lower not in allowed_severities:
        raise ValueError(
            f"Invalid severity: {severity}. Must be one of: {', '.join(allowed_severities)}"
        )

    return severity_lower


def validate_limit(limit: int, min_limit: int = 1, max_limit: int = 1000) -> int:
    """
    Validate pagination limit parameter.

    Args:
        limit: Limit to validate
        min_limit: Minimum allowed limit
        max_limit: Maximum allowed limit

    Returns:
        Validated limit

    Raises:
        ValueError: If limit is out of range
    """
    if limit < min_limit or limit > max_limit:
        raise ValueError(f"Limit must be between {min_limit} and {max_limit}")

    return limit


def validate_status_filter(status: str, allowed_statuses: Optional[list[str]] = None) -> str:
    """
    Validate status filter parameter.

    Args:
        status: Status to validate
        allowed_statuses: List of allowed statuses

    Returns:
        Validated status

    Raises:
        ValueError: If status is invalid
    """
    if allowed_statuses is None:
        allowed_statuses = ['pending', 'running', 'completed', 'failed', 'cancelled']

    if status not in allowed_statuses:
        raise ValueError(
            f"Invalid status filter. Allowed: {', '.join(allowed_statuses)}"
        )

    return status
