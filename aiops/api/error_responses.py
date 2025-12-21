"""Unified error response handling for API endpoints."""
import uuid
import logging
from typing import Optional, Dict, Any
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_429_TOO_MANY_REQUESTS,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

logger = logging.getLogger(__name__)


class APIErrorResponse:
    """Standardized API error response builder."""

    @staticmethod
    def create(
        status_code: int,
        error_type: str,
        message: str,
        error_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        retry_after: Optional[int] = None,
    ) -> JSONResponse:
        """Create a standardized error response.

        Args:
            status_code: HTTP status code
            error_type: Type of error (e.g., 'ValidationError', 'AuthenticationError')
            message: Human-readable error message
            error_id: Unique error ID for tracking
            details: Additional error details
            retry_after: Seconds to wait before retrying (for rate limit errors)

        Returns:
            JSONResponse with standardized error format
        """
        error_id = error_id or str(uuid.uuid4())[:8]

        content = {
            "error": error_type,
            "message": message,
            "error_id": error_id,
        }

        if details:
            content["details"] = details

        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)
            content["retry_after"] = retry_after

        return JSONResponse(
            status_code=status_code,
            content=content,
            headers=headers or None,
        )

    @classmethod
    def bad_request(cls, message: str, details: Optional[Dict] = None) -> JSONResponse:
        """400 Bad Request error."""
        return cls.create(HTTP_400_BAD_REQUEST, "BadRequest", message, details=details)

    @classmethod
    def unauthorized(cls, message: str = "Authentication required") -> JSONResponse:
        """401 Unauthorized error."""
        return cls.create(HTTP_401_UNAUTHORIZED, "Unauthorized", message)

    @classmethod
    def forbidden(cls, message: str = "Access denied") -> JSONResponse:
        """403 Forbidden error."""
        return cls.create(HTTP_403_FORBIDDEN, "Forbidden", message)

    @classmethod
    def not_found(cls, resource: str = "Resource") -> JSONResponse:
        """404 Not Found error."""
        return cls.create(HTTP_404_NOT_FOUND, "NotFound", f"{resource} not found")

    @classmethod
    def validation_error(cls, errors: Dict[str, Any]) -> JSONResponse:
        """422 Validation Error."""
        return cls.create(
            HTTP_422_UNPROCESSABLE_ENTITY,
            "ValidationError",
            "Validation failed",
            details=errors,
        )

    @classmethod
    def rate_limited(cls, retry_after: int = 60) -> JSONResponse:
        """429 Too Many Requests error."""
        return cls.create(
            HTTP_429_TOO_MANY_REQUESTS,
            "RateLimitExceeded",
            "Too many requests. Please try again later.",
            retry_after=retry_after,
        )

    @classmethod
    def internal_error(
        cls,
        request: Optional[Request] = None,
        exc: Optional[Exception] = None,
    ) -> JSONResponse:
        """500 Internal Server Error."""
        error_id = str(uuid.uuid4())[:8]

        # Log the actual error for debugging
        if exc:
            logger.error(
                f"Internal error {error_id}: {type(exc).__name__}: {exc}",
                exc_info=True,
            )

        # Return safe message to user
        return cls.create(
            HTTP_500_INTERNAL_SERVER_ERROR,
            "InternalError",
            "An unexpected error occurred. Please try again later.",
            error_id=error_id,
        )
