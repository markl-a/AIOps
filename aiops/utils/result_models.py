"""Common Pydantic models and mixins for agent results."""

from enum import Enum
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


class SeverityLevel(str, Enum):
    """Standard severity levels used across agents."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class BaseSeverityModel(BaseModel):
    """Base model for items with severity levels."""
    severity: str = Field(
        description="Severity level: critical, high, medium, low, info"
    )
    description: str = Field(description="Detailed description")


class BaseIssueModel(BaseSeverityModel):
    """Base model for issues/findings across different agents."""
    category: str = Field(description="Issue category")
    location: Optional[str] = Field(default=None, description="Location (file:line, resource name, etc.)")
    remediation: str = Field(description="Recommended remediation steps")


class BaseResultModel(BaseModel):
    """Base model for agent execution results."""
    summary: str = Field(description="Executive summary of results")
    recommendations: List[str] = Field(
        default_factory=list,
        description="List of actionable recommendations"
    )

    class Config:
        """Pydantic config."""
        use_enum_values = True


class BaseAnalysisResult(BaseResultModel):
    """Base model for analysis results with scoring."""
    overall_score: float = Field(
        description="Overall score (0-100)",
        ge=0.0,
        le=100.0
    )


class BaseVulnerability(BaseIssueModel):
    """Base model for security/compliance vulnerabilities."""
    cve_id: Optional[str] = Field(default=None, description="CVE ID if applicable")
    cwe_id: Optional[str] = Field(default=None, description="CWE ID if applicable")
    attack_scenario: Optional[str] = Field(default=None, description="How this could be exploited")
    references: List[str] = Field(default_factory=list, description="Reference links")


def create_default_result(
    result_class: type[BaseModel],
    error_message: str,
    **kwargs: Any
) -> BaseModel:
    """
    Create a default error result for any result model class.

    Args:
        result_class: The Pydantic model class to instantiate
        error_message: Error message to include in summary
        **kwargs: Additional fields to override defaults

    Returns:
        Instance of result_class with error state
    """
    # Start with common defaults
    defaults: Dict[str, Any] = {
        "summary": f"Operation failed: {error_message}",
        "recommendations": ["Please retry the operation or check logs for details"],
    }

    # Add score if it's an analysis result
    if hasattr(result_class, "model_fields") and "overall_score" in result_class.model_fields:
        defaults["overall_score"] = 0.0

    # Add common list fields as empty lists
    for field_name, field_info in result_class.model_fields.items():
        if field_name in defaults:
            continue

        # Check if field is a list type
        annotation = field_info.annotation
        if hasattr(annotation, "__origin__") and annotation.__origin__ is list:
            defaults[field_name] = []
        # Check if field is a dict type
        elif hasattr(annotation, "__origin__") and annotation.__origin__ is dict:
            defaults[field_name] = {}
        # Check if field is optional and not set
        elif field_info.default is None:
            defaults[field_name] = None

    # Override with provided kwargs
    defaults.update(kwargs)

    return result_class(**defaults)
