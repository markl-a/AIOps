"""Custom exceptions for AIOps framework."""

from typing import Optional, Dict, Any


class AIOpsException(Exception):
    """Base exception for all AIOps errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize AIOps exception.

        Args:
            message: Error message
            error_code: Unique error code for tracking
            details: Additional error details
        """
        self.message = message
        self.error_code = error_code or "AIOPS_ERROR"
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details,
        }


# Configuration Errors
class ConfigurationError(AIOpsException):
    """Raised when there's a configuration error."""

    def __init__(self, message: str, config_key: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="CONFIG_ERROR",
            details={"config_key": config_key} if config_key else {},
        )


class MissingAPIKeyError(ConfigurationError):
    """Raised when required API key is missing."""

    def __init__(self, provider: str):
        super().__init__(
            message=f"API key for {provider} is not configured",
            config_key=f"{provider.upper()}_API_KEY",
        )
        self.error_code = "MISSING_API_KEY"


# LLM Provider Errors
class LLMProviderError(AIOpsException):
    """Base class for LLM provider errors."""

    def __init__(
        self,
        message: str,
        provider: str,
        model: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        details = {"provider": provider}
        if model:
            details["model"] = model
        if original_error:
            details["original_error"] = str(original_error)

        super().__init__(
            message=message,
            error_code="LLM_PROVIDER_ERROR",
            details=details,
        )
        self.provider = provider
        self.model = model
        self.original_error = original_error


class LLMRateLimitError(LLMProviderError):
    """Raised when LLM provider rate limit is exceeded."""

    def __init__(
        self,
        provider: str,
        retry_after: Optional[int] = None,
    ):
        message = f"Rate limit exceeded for {provider}"
        if retry_after:
            message += f". Retry after {retry_after} seconds"

        super().__init__(message=message, provider=provider)
        self.error_code = "RATE_LIMIT_EXCEEDED"
        self.retry_after = retry_after
        if retry_after:
            self.details["retry_after"] = retry_after


class LLMTimeoutError(LLMProviderError):
    """Raised when LLM request times out."""

    def __init__(self, provider: str, timeout_seconds: int):
        super().__init__(
            message=f"Request to {provider} timed out after {timeout_seconds}s",
            provider=provider,
        )
        self.error_code = "LLM_TIMEOUT"
        self.timeout_seconds = timeout_seconds
        self.details["timeout_seconds"] = timeout_seconds


class LLMResponseError(LLMProviderError):
    """Raised when LLM response is invalid or cannot be parsed."""

    def __init__(
        self,
        provider: str,
        message: str = "Invalid response from LLM",
        response_data: Optional[Any] = None,
    ):
        super().__init__(message=message, provider=provider)
        self.error_code = "INVALID_LLM_RESPONSE"
        if response_data:
            self.details["response_data"] = str(response_data)


# Agent Errors
class AgentError(AIOpsException):
    """Base class for agent-related errors."""

    def __init__(
        self,
        message: str,
        agent_name: Optional[str] = None,
        operation: Optional[str] = None,
    ):
        details = {}
        if agent_name:
            details["agent_name"] = agent_name
        if operation:
            details["operation"] = operation

        super().__init__(
            message=message,
            error_code="AGENT_ERROR",
            details=details,
        )
        self.agent_name = agent_name


class AgentExecutionError(AgentError):
    """Raised when agent execution fails."""

    def __init__(
        self,
        agent_name: str,
        message: str = "Agent execution failed",
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            agent_name=agent_name,
            operation="execute",
        )
        self.error_code = "AGENT_EXECUTION_FAILED"
        if original_error:
            self.details["original_error"] = str(original_error)
            self.details["error_type"] = type(original_error).__name__


class AgentValidationError(AgentError):
    """Raised when agent input validation fails."""

    def __init__(
        self,
        agent_name: str,
        validation_errors: Dict[str, str],
    ):
        super().__init__(
            message="Agent input validation failed",
            agent_name=agent_name,
        )
        self.error_code = "VALIDATION_ERROR"
        self.details["validation_errors"] = validation_errors
        self.validation_errors = validation_errors


# Authentication & Authorization Errors
class AuthenticationError(AIOpsException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            error_code="AUTH_FAILED",
        )


class AuthorizationError(AIOpsException):
    """Raised when user is not authorized."""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        required_role: Optional[str] = None,
        user_role: Optional[str] = None,
    ):
        details = {}
        if required_role:
            details["required_role"] = required_role
        if user_role:
            details["user_role"] = user_role

        super().__init__(
            message=message,
            error_code="UNAUTHORIZED",
            details=details,
        )


class InvalidTokenError(AuthenticationError):
    """Raised when token is invalid or expired."""

    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(message=message)
        self.error_code = "INVALID_TOKEN"


# Resource Errors
class ResourceError(AIOpsException):
    """Base class for resource-related errors."""

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id

        super().__init__(
            message=message,
            error_code="RESOURCE_ERROR",
            details=details,
        )


class ResourceNotFoundError(ResourceError):
    """Raised when requested resource is not found."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
    ):
        super().__init__(
            message=f"{resource_type} with ID '{resource_id}' not found",
            resource_type=resource_type,
            resource_id=resource_id,
        )
        self.error_code = "RESOURCE_NOT_FOUND"


class ResourceExistsError(ResourceError):
    """Raised when resource already exists."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
    ):
        super().__init__(
            message=f"{resource_type} with ID '{resource_id}' already exists",
            resource_type=resource_type,
            resource_id=resource_id,
        )
        self.error_code = "RESOURCE_EXISTS"


# API Errors
class APIError(AIOpsException):
    """Base class for API-related errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        endpoint: Optional[str] = None,
    ):
        details = {"status_code": status_code}
        if endpoint:
            details["endpoint"] = endpoint

        super().__init__(
            message=message,
            error_code="API_ERROR",
            details=details,
        )
        self.status_code = status_code


class RateLimitExceededError(APIError):
    """Raised when API rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
    ):
        super().__init__(message=message, status_code=429)
        self.error_code = "RATE_LIMIT_EXCEEDED"
        if retry_after:
            self.details["retry_after"] = retry_after


class ValidationError(APIError):
    """Raised when request validation fails."""

    def __init__(
        self,
        message: str,
        validation_errors: Optional[Dict[str, str]] = None,
    ):
        super().__init__(message=message, status_code=422)
        self.error_code = "VALIDATION_ERROR"
        if validation_errors:
            self.details["validation_errors"] = validation_errors


# Budget & Cost Errors
class BudgetError(AIOpsException):
    """Raised when budget limit is exceeded."""

    def __init__(
        self,
        message: str = "Budget limit exceeded",
        current_cost: Optional[float] = None,
        budget_limit: Optional[float] = None,
    ):
        details = {}
        if current_cost is not None:
            details["current_cost"] = current_cost
        if budget_limit is not None:
            details["budget_limit"] = budget_limit

        super().__init__(
            message=message,
            error_code="BUDGET_EXCEEDED",
            details=details,
        )


class TokenLimitError(AIOpsException):
    """Raised when token limit is exceeded."""

    def __init__(
        self,
        message: str = "Token limit exceeded",
        current_tokens: Optional[int] = None,
        token_limit: Optional[int] = None,
    ):
        details = {}
        if current_tokens:
            details["current_tokens"] = current_tokens
        if token_limit:
            details["token_limit"] = token_limit

        super().__init__(
            message=message,
            error_code="TOKEN_LIMIT_EXCEEDED",
            details=details,
        )


# Database Errors
class DatabaseError(AIOpsException):
    """Base class for database-related errors."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        details = {}
        if operation:
            details["operation"] = operation
        if original_error:
            details["original_error"] = str(original_error)

        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            details=details,
        )


class ConnectionError(DatabaseError):
    """Raised when database connection fails."""

    def __init__(
        self,
        message: str = "Database connection failed",
        database: Optional[str] = None,
    ):
        super().__init__(message=message)
        self.error_code = "DB_CONNECTION_ERROR"
        if database:
            self.details["database"] = database


# Cache Errors
class CacheError(AIOpsException):
    """Base class for cache-related errors."""

    def __init__(
        self,
        message: str,
        cache_key: Optional[str] = None,
    ):
        details = {}
        if cache_key:
            details["cache_key"] = cache_key

        super().__init__(
            message=message,
            error_code="CACHE_ERROR",
            details=details,
        )


# Integration Errors
class IntegrationError(AIOpsException):
    """Base class for third-party integration errors."""

    def __init__(
        self,
        message: str,
        integration_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        integration_details = {}
        if integration_name:
            integration_details["integration_name"] = integration_name
        if details:
            integration_details.update(details)

        super().__init__(
            message=message,
            error_code="INTEGRATION_ERROR",
            details=integration_details,
        )


# Utility functions
def handle_exception(exc: Exception) -> AIOpsException:
    """Convert standard exceptions to AIOps exceptions.

    Args:
        exc: Original exception

    Returns:
        AIOps exception instance
    """
    if isinstance(exc, AIOpsException):
        return exc

    # Map common exceptions
    exception_map = {
        ValueError: lambda e: AgentValidationError(
            agent_name="Unknown",
            validation_errors={"value": str(e)},
        ),
        KeyError: lambda e: ResourceNotFoundError(
            resource_type="key",
            resource_id=str(e),
        ),
        TimeoutError: lambda e: LLMTimeoutError(
            provider="Unknown",
            timeout_seconds=0,
        ),
    }

    exception_class = exception_map.get(type(exc))
    if exception_class:
        return exception_class(exc)

    # Default: wrap in generic AIOps exception
    return AIOpsException(
        message=str(exc),
        error_code="UNKNOWN_ERROR",
        details={"original_type": type(exc).__name__},
    )
