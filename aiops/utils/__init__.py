"""Shared utility modules for AIOps."""

from aiops.utils.agent_helpers import (
    create_default_error_result,
    log_agent_execution,
    format_dict_for_prompt,
    extract_code_from_response,
)
from aiops.utils.result_models import (
    BaseSeverityModel,
    BaseResultModel,
    SeverityLevel,
)
from aiops.utils.validation import (
    validate_agent_type,
    validate_callback_url,
    validate_input_data_size,
    validate_metric_name,
    validate_severity,
)
from aiops.utils.formatting import (
    format_metrics_dict,
    format_list_for_prompt,
    generate_markdown_report,
    format_timestamp,
)

__all__ = [
    # Agent helpers
    "create_default_error_result",
    "log_agent_execution",
    "format_dict_for_prompt",
    "extract_code_from_response",
    # Result models
    "BaseSeverityModel",
    "BaseResultModel",
    "SeverityLevel",
    # Validation
    "validate_agent_type",
    "validate_callback_url",
    "validate_input_data_size",
    "validate_metric_name",
    "validate_severity",
    # Formatting
    "format_metrics_dict",
    "format_list_for_prompt",
    "generate_markdown_report",
    "format_timestamp",
]
