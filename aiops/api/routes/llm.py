"""LLM Provider Routes"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, List, Optional
import re

from aiops.core.structured_logger import get_structured_logger


logger = get_structured_logger(__name__)
router = APIRouter()


# Request/Response Models
class LLMGenerateRequest(BaseModel):
    """Request to generate text with LLM."""

    prompt: str = Field(
        ...,
        description="Input prompt",
        min_length=1,
        max_length=100000  # 100KB max prompt size
    )
    model: Optional[str] = Field(
        None,
        description="Model to use",
        max_length=100
    )
    max_tokens: int = Field(default=4000, ge=1, le=32000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    provider: Optional[str] = Field(
        None,
        description="Specific provider to use",
        max_length=50
    )

    @field_validator('prompt')
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        """Validate and sanitize prompt."""
        # Strip leading/trailing whitespace
        v = v.strip()

        # Ensure prompt is not empty after stripping
        if not v:
            raise ValueError("Prompt cannot be empty")

        # Check for suspicious patterns that might indicate injection attempts
        suspicious_patterns = [
            r'<script[^>]*>',  # Script tags
            r'javascript:',     # JavaScript protocol
            r'on\w+\s*=',      # Event handlers
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                logger.warning(f"Suspicious pattern detected in prompt: {pattern}")
                raise ValueError("Invalid characters or patterns in prompt")

        return v

    @field_validator('model', 'provider')
    @classmethod
    def validate_string_fields(cls, v: Optional[str]) -> Optional[str]:
        """Validate string fields."""
        if v is None:
            return v

        # Strip whitespace
        v = v.strip()

        # Only allow alphanumeric, hyphens, underscores, and dots
        if not re.match(r'^[a-zA-Z0-9._-]+$', v):
            raise ValueError("Field contains invalid characters")

        return v


class LLMGenerateResponse(BaseModel):
    """Response from LLM generation."""

    text: str = Field(..., description="Generated text response from the LLM")
    provider: str = Field(..., description="LLM provider used (e.g., openai, anthropic, google)")
    model: str = Field(..., description="Specific model used for generation")
    tokens_used: int = Field(..., description="Total number of tokens consumed")
    cost_usd: float = Field(..., description="Estimated cost in USD for this generation")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "Here is the generated response based on your prompt...",
                "provider": "openai",
                "model": "gpt-4-turbo-preview",
                "tokens_used": 150,
                "cost_usd": 0.0045
            }
        }


class ProviderHealthResponse(BaseModel):
    """Health status of LLM providers."""

    provider: str = Field(..., description="Provider name (openai, anthropic, google, etc.)")
    status: str = Field(..., description="Health status: healthy, degraded, or unhealthy")
    success_rate: float = Field(..., description="Success rate as a decimal (0.0 to 1.0)", ge=0.0, le=1.0)
    total_requests: int = Field(..., description="Total number of requests made to this provider", ge=0)
    last_success: Optional[str] = Field(None, description="ISO 8601 timestamp of last successful request")
    last_failure: Optional[str] = Field(None, description="ISO 8601 timestamp of last failed request")

    class Config:
        json_schema_extra = {
            "example": {
                "provider": "openai",
                "status": "healthy",
                "success_rate": 0.985,
                "total_requests": 1245,
                "last_success": "2024-01-15T10:30:00Z",
                "last_failure": None
            }
        }


class LLMStatsResponse(BaseModel):
    """LLM usage statistics."""

    total_requests: int = Field(..., description="Total number of LLM requests across all providers", ge=0)
    total_tokens: int = Field(..., description="Total number of tokens consumed", ge=0)
    total_cost_usd: float = Field(..., description="Total cost in USD across all providers", ge=0.0)
    requests_by_provider: Dict[str, int] = Field(..., description="Request count breakdown by provider")
    average_response_time_ms: float = Field(..., description="Average response time in milliseconds", ge=0.0)

    class Config:
        json_schema_extra = {
            "example": {
                "total_requests": 2533,
                "total_tokens": 1245678,
                "total_cost_usd": 124.56,
                "requests_by_provider": {
                    "openai": 1245,
                    "anthropic": 856,
                    "google": 432
                },
                "average_response_time_ms": 387.5
            }
        }


@router.post(
    "/generate",
    response_model=LLMGenerateResponse,
    summary="Generate text with LLM",
    description="""Generate text using an LLM with automatic failover between providers.

    Features:
    - Automatic provider failover for high availability
    - Configurable model selection
    - Temperature control for response creativity
    - Token limit configuration
    - Cost tracking and optimization
    - Input sanitization and validation
    """,
    responses={
        200: {"description": "Text generated successfully"},
        400: {
            "description": "Invalid request parameters",
            "content": {
                "application/json": {
                    "example": {
                        "error": "ValidationError",
                        "message": "Request validation failed",
                        "details": [{"field": "prompt", "message": "Prompt cannot be empty"}]
                    }
                }
            }
        },
        500: {
            "description": "LLM generation failed",
            "content": {
                "application/json": {
                    "example": {"detail": "LLM generation failed: All providers unavailable"}
                }
            }
        }
    }
)
async def generate_text(request: LLMGenerateRequest):
    """Generate text using LLM with automatic failover."""
    logger.info(
        "LLM generation request",
        prompt_length=len(request.prompt),
        max_tokens=request.max_tokens,
        provider=request.provider,
    )

    try:
        # Mock implementation - replace with actual LLM manager
        import asyncio
        await asyncio.sleep(0.3)  # Simulate LLM call

        return LLMGenerateResponse(
            text=f"Generated response for: {request.prompt[:50]}...",
            provider=request.provider or "openai",
            model=request.model or "gpt-4-turbo-preview",
            tokens_used=150,
            cost_usd=0.0045,
        )

    except Exception as e:
        logger.error(f"LLM generation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM generation failed: {str(e)}",
        )


@router.get("/providers/health", response_model=List[ProviderHealthResponse])
async def get_providers_health():
    """Get health status of all LLM providers."""
    # Mock implementation - replace with actual provider manager
    providers = [
        {
            "provider": "openai",
            "status": "healthy",
            "success_rate": 0.985,
            "total_requests": 1245,
            "last_success": "2024-01-15T10:30:00Z",
            "last_failure": None,
        },
        {
            "provider": "anthropic",
            "status": "healthy",
            "success_rate": 0.992,
            "total_requests": 856,
            "last_success": "2024-01-15T10:29:45Z",
            "last_failure": None,
        },
        {
            "provider": "google",
            "status": "degraded",
            "success_rate": 0.875,
            "total_requests": 432,
            "last_success": "2024-01-15T10:25:00Z",
            "last_failure": "2024-01-15T10:28:30Z",
        },
    ]

    return [ProviderHealthResponse(**p) for p in providers]


@router.post("/providers/{provider}/health-check")
async def check_provider_health(provider: str):
    """Run health check on a specific provider."""
    # Validate provider name (only alphanumeric and underscores)
    if not re.match(r'^[a-zA-Z0-9_-]+$', provider):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid provider name"
        )

    # Limit provider name length
    if len(provider) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider name too long"
        )

    logger.info(f"Running health check for provider: {provider}")

    # Mock implementation
    return {
        "provider": provider,
        "status": "healthy",
        "response_time_ms": 245.3,
        "checked_at": "2024-01-15T10:30:00Z",
    }


@router.get("/stats", response_model=LLMStatsResponse)
async def get_llm_stats():
    """Get LLM usage statistics."""
    # Mock implementation
    return LLMStatsResponse(
        total_requests=2533,
        total_tokens=1_245_678,
        total_cost_usd=124.56,
        requests_by_provider={
            "openai": 1245,
            "anthropic": 856,
            "google": 432,
        },
        average_response_time_ms=387.5,
    )


@router.get("/models")
async def list_models():
    """List available models for each provider."""
    return {
        "openai": [
            {"name": "gpt-4-turbo-preview", "context_length": 128000, "cost_per_1k_tokens": 0.03},
            {"name": "gpt-4", "context_length": 8192, "cost_per_1k_tokens": 0.03},
            {"name": "gpt-3.5-turbo", "context_length": 16385, "cost_per_1k_tokens": 0.002},
        ],
        "anthropic": [
            {"name": "claude-3-opus", "context_length": 200000, "cost_per_1k_tokens": 0.015},
            {"name": "claude-3-sonnet", "context_length": 200000, "cost_per_1k_tokens": 0.003},
            {"name": "claude-3-haiku", "context_length": 200000, "cost_per_1k_tokens": 0.00025},
        ],
        "google": [
            {"name": "gemini-pro", "context_length": 32000, "cost_per_1k_tokens": 0.001},
            {"name": "gemini-pro-vision", "context_length": 16000, "cost_per_1k_tokens": 0.002},
        ],
    }
