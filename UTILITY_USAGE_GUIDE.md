# AIOps Utilities - Quick Reference Guide

This guide provides quick examples for using the shared utility modules in `aiops/utils/`.

---

## Table of Contents

1. [Agent Helpers](#agent-helpers)
2. [Result Models](#result-models)
3. [Validation](#validation)
4. [Formatting](#formatting)
5. [Complete Agent Example](#complete-agent-example)

---

## Agent Helpers

### Error Handling

```python
from aiops.utils.agent_helpers import handle_agent_error

async def execute(self, code: str) -> AnalysisResult:
    try:
        # Your agent logic
        result = await self._generate_structured_response(...)
        return result
    except Exception as e:
        # One-line error handling
        return handle_agent_error(
            agent_name=self.name,
            operation="code analysis",
            error=e,
            result_class=AnalysisResult
        )
```

### Logging

```python
from aiops.utils.agent_helpers import log_agent_execution

async def execute(self, code: str) -> AnalysisResult:
    # Log start
    log_agent_execution(
        agent_name=self.name,
        operation="code analysis",
        phase="start",
        language="python",
        lines=len(code.split("\n"))
    )

    # ... do work ...

    # Log completion
    log_agent_execution(
        agent_name=self.name,
        operation="code analysis",
        phase="complete",
        issues_found=len(result.issues),
        score=result.overall_score
    )
```

### Prompt Creation

```python
from aiops.utils.agent_helpers import (
    create_system_prompt_template,
    create_user_prompt_template
)

# System prompt
system_prompt = create_system_prompt_template(
    role="an expert Python developer and code reviewer",
    expertise_areas=[
        "Clean Code principles",
        "Design patterns",
        "Performance optimization"
    ],
    analysis_focus=[
        "Code quality and maintainability",
        "Performance bottlenecks",
        "Security vulnerabilities",
        "Best practices compliance"
    ],
    output_requirements=[
        "Specific, actionable feedback",
        "Severity levels for each issue",
        "Code examples where applicable"
    ]
)

# User prompt
user_prompt = create_user_prompt_template(
    operation="Analyze the following Python code for quality issues",
    main_content=f"```python\n{code}\n```",
    context=f"This is a {project_type} project",
    additional_sections={
        "Dependencies": dependencies,
        "Configuration": config
    },
    requirements=[
        "Identify code smells",
        "Check for performance issues",
        "Suggest refactoring opportunities"
    ]
)
```

### Code Extraction

```python
from aiops.utils.agent_helpers import extract_code_from_response

# Get LLM response
response = await self._generate_response(prompt, system_prompt)

# Extract code block
optimized_code = extract_code_from_response(
    response,
    language="python"  # Optional: specify expected language
)
```

### Dictionary Formatting

```python
from aiops.utils.agent_helpers import format_dict_for_prompt

metrics = {
    "cpu": {"usage": 75, "cores": 4},
    "memory": {"usage": 82, "total_gb": 16},
    "disk": {"usage": 45, "total_gb": 500}
}

formatted = format_dict_for_prompt(metrics, max_depth=2)
# Output:
# - cpu:
#   - usage: 75
#   - cores: 4
# - memory:
#   - usage: 82
#   - total_gb: 16
# ...
```

---

## Result Models

### Using Base Classes

```python
from aiops.utils.result_models import (
    BaseSeverityModel,
    BaseIssueModel,
    BaseAnalysisResult,
    BaseVulnerability,
    SeverityLevel
)
from pydantic import Field
from typing import List

# Simple issue model
class CodeIssue(BaseIssueModel):
    """Code quality issue - inherits severity, category, location, description, remediation."""
    line_number: int = Field(description="Line number")
    code_snippet: str = Field(description="Affected code")
    # No need to redeclare: severity, category, description, remediation, location

# Analysis result with scoring
class CodeQualityResult(BaseAnalysisResult):
    """Inherits: summary, recommendations, overall_score."""
    issues: List[CodeIssue] = Field(default_factory=list)
    maintainability_index: float = Field(description="Maintainability score")
    # No need to redeclare: summary, recommendations, overall_score

# Security vulnerability
class SecurityFinding(BaseVulnerability):
    """Inherits: severity, category, location, description, remediation, cve_id, cwe_id, references."""
    attack_vector: str = Field(description="Attack vector (network, local, etc.)")
    # No need to redeclare common security fields
```

### Creating Default Error Results

```python
from aiops.utils.result_models import create_default_result

# Automatic empty result
error_result = create_default_result(
    result_class=CodeQualityResult,
    error_message="Analysis failed: timeout",
    # Optional overrides:
    overall_score=0,
    maintainability_index=0
)
# Automatically fills in:
# - summary = "Operation failed: Analysis failed: timeout"
# - recommendations = ["Please retry the operation..."]
# - issues = []
# - overall_score = 0
# - maintainability_index = 0
```

### Using Severity Enum

```python
from aiops.utils.result_models import SeverityLevel

issue = CodeIssue(
    severity=SeverityLevel.HIGH,  # Type-safe enum
    category="maintainability",
    description="Function too long",
    remediation="Break into smaller functions",
    line_number=45,
    code_snippet="def process_data(...):"
)
```

---

## Validation

### API Route Validation

```python
from pydantic import BaseModel, Field, field_validator
from aiops.utils.validation import (
    validate_agent_type,
    validate_callback_url,
    validate_input_data_size,
    validate_input_data_keys,
    validate_severity,
    validate_limit
)

class AgentRequest(BaseModel):
    agent_type: str
    input_data: Dict[str, Any]
    callback_url: Optional[str] = None

    @field_validator('agent_type')
    @classmethod
    def validate_agent_type_field(cls, v: str) -> str:
        return validate_agent_type(v)  # Handles whitespace, regex, length

    @field_validator('callback_url')
    @classmethod
    def validate_callback_url_field(cls, v: Optional[str]) -> Optional[str]:
        return validate_callback_url(v)  # Handles SSRF protection

    @field_validator('input_data')
    @classmethod
    def validate_input_data_field(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        validate_input_data_size(v)  # Raises if too large
        return validate_input_data_keys(v)  # Validates key format
```

### Manual Validation

```python
from aiops.utils.validation import validate_limit, validate_severity

# In route handler
@router.get("/items")
async def get_items(limit: int = 100, severity: Optional[str] = None):
    # Validate limit
    validated_limit = validate_limit(limit, min_limit=1, max_limit=1000)

    # Validate severity if provided
    if severity:
        validated_severity = validate_severity(severity)  # Returns lowercase

    # Use validated values
    items = fetch_items(limit=validated_limit, severity=validated_severity)
    return items
```

### Metric Name Validation

```python
from aiops.utils.validation import validate_metric_name
from fastapi import HTTPException

metric_names = ["cpu.usage", "memory-used", "disk_io"]

for name in metric_names:
    if not validate_metric_name(name):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid metric name: {name}"
        )
```

---

## Formatting

### Metrics Formatting

```python
from aiops.utils.formatting import format_metrics_dict

metrics = {
    "cpu": {"usage": 75.5, "cores": 4},
    "memory": {"used_gb": 13.2, "total_gb": 16}
}

formatted = format_metrics_dict(metrics)
# Output:
# cpu:
#   - usage: 75.5
#   - cores: 4
# memory:
#   - used_gb: 13.2
#   - total_gb: 16
```

### List Formatting

```python
from aiops.utils.formatting import format_list_for_prompt

issues = ["SQL injection in login", "XSS in search", "CSRF in forms"]

formatted = format_list_for_prompt(
    items=issues,
    title="Security Issues Found",
    numbered=True
)
# Output:
# Security Issues Found:
# 1. SQL injection in login
# 2. XSS in search
# 3. CSRF in forms
```

### Markdown Reports

```python
from aiops.utils.formatting import generate_markdown_report

report = generate_markdown_report(
    title="Code Quality Analysis",
    sections={
        "Summary": "Analysis of 1,234 lines of Python code",
        "Issues Found": "- 5 critical issues\n- 12 warnings",
        "Recommendations": "1. Fix SQL injection\n2. Add input validation"
    },
    metadata={
        "Date": "2025-12-31",
        "Analyzer": "CodeQualityAgent",
        "Score": "75/100"
    }
)
```

### Code Blocks

```python
from aiops.utils.formatting import format_code_block

formatted = format_code_block(
    code="def hello():\n    print('Hello')",
    language="python",
    title="Optimized Version"
)
# Output:
# **Optimized Version**:
# ```python
# def hello():
#     print('Hello')
# ```
```

### Tables

```python
from aiops.utils.formatting import format_table

headers = ["Metric", "Value", "Status"]
rows = [
    ["CPU Usage", "45%", "Good"],
    ["Memory", "82%", "Warning"],
    ["Disk", "95%", "Critical"]
]

table = format_table(headers, rows, title="System Metrics")
# Output:
# ### System Metrics
#
# | Metric | Value | Status |
# | --- | --- | --- |
# | CPU Usage | 45% | Good |
# | Memory | 82% | Warning |
# | Disk | 95% | Critical |
```

### Utility Formatters

```python
from aiops.utils.formatting import (
    format_timestamp,
    format_percentage,
    format_file_size,
    truncate_text
)

# Timestamps
ts = format_timestamp()  # "2025-12-31 14:30:45"

# Percentages
pct = format_percentage(0.8532)  # "85.32%"
pct = format_percentage(85.32)   # "85.32%"

# File sizes
size = format_file_size(1536000)  # "1.46 MB"

# Text truncation
short = truncate_text("Very long text...", max_length=20)  # "Very long text..."
```

---

## Complete Agent Example

Here's a complete example of a well-structured agent using all utilities:

```python
"""Example Agent - Demonstrates utility usage."""

from typing import Optional, List
from pydantic import Field

from aiops.agents.base_agent import BaseAgent
from aiops.utils.result_models import BaseIssueModel, BaseAnalysisResult
from aiops.utils.agent_helpers import (
    create_system_prompt_template,
    create_user_prompt_template,
    handle_agent_error,
    log_agent_execution,
    format_dict_for_prompt,
)
from aiops.core.logger import get_logger

logger = get_logger(__name__)


# Result models using base classes
class CodeIssue(BaseIssueModel):
    """Code issue - inherits common fields."""
    line_number: int = Field(description="Line number")
    impact: str = Field(description="Impact on system")


class AnalysisResult(BaseAnalysisResult):
    """Analysis result - inherits summary, recommendations, overall_score."""
    issues: List[CodeIssue] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)


class ExampleAgent(BaseAgent):
    """Example agent demonstrating utility usage."""

    def __init__(self, **kwargs):
        super().__init__(name="ExampleAgent", **kwargs)

    async def execute(
        self,
        code: str,
        language: str = "python",
        context: Optional[str] = None,
    ) -> AnalysisResult:
        """
        Analyze code using utilities.

        Args:
            code: Code to analyze
            language: Programming language
            context: Additional context

        Returns:
            Analysis result
        """
        # Log start with context
        log_agent_execution(
            agent_name=self.name,
            operation="code analysis",
            phase="start",
            language=language,
            code_length=len(code)
        )

        # Create prompts using templates
        system_prompt = create_system_prompt_template(
            role=f"an expert {language} developer",
            expertise_areas=[
                "Code quality analysis",
                "Performance optimization",
                "Security best practices"
            ],
            analysis_focus=[
                "Code smells and anti-patterns",
                "Performance issues",
                "Security vulnerabilities"
            ],
            output_requirements=[
                "Specific line numbers",
                "Severity levels",
                "Actionable remediation steps"
            ]
        )

        user_prompt = create_user_prompt_template(
            operation="Analyze the following code",
            main_content=f"```{language}\n{code}\n```",
            context=context,
            requirements=[
                "Identify all issues with severity",
                "Provide specific remediation",
                "Calculate overall quality score"
            ]
        )

        # Execute with error handling
        try:
            result = await self._generate_structured_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                schema=AnalysisResult,
            )

            # Log completion
            log_agent_execution(
                agent_name=self.name,
                operation="code analysis",
                phase="complete",
                score=result.overall_score,
                issues=len(result.issues)
            )

            return result

        except Exception as e:
            # One-line error handling
            return handle_agent_error(
                agent_name=self.name,
                operation="code analysis",
                error=e,
                result_class=AnalysisResult
            )

    async def analyze_metrics(
        self,
        metrics: dict,
    ) -> str:
        """Analyze system metrics."""
        # Format metrics using utility
        formatted_metrics = format_dict_for_prompt(metrics, max_depth=2)

        prompt = f"""Analyze these system metrics:

{formatted_metrics}

Identify any anomalies or concerns.
"""

        return await self._generate_response(prompt)
```

---

## Best Practices

### When to Use Utilities

✅ **Use utilities when:**
- Creating standard error results
- Formatting data for prompts
- Validating user input in API routes
- Generating reports
- Logging agent execution
- Creating prompts with standard structure

❌ **Don't use utilities when:**
- You need highly customized behavior
- The pattern appears only once
- Performance is absolutely critical
- The abstraction makes code less clear

### Tips

1. **Import what you need**: Don't import everything
   ```python
   # Good
   from aiops.utils.agent_helpers import handle_agent_error

   # Avoid
   from aiops.utils import *
   ```

2. **Combine utilities**: Use multiple utilities together
   ```python
   formatted = format_list_for_prompt(
       items=[format_dict_for_prompt(m) for m in metrics],
       title="Metrics"
   )
   ```

3. **Override defaults**: Most utilities accept optional parameters
   ```python
   log_agent_execution(
       agent_name=self.name,
       operation="scan",
       phase="start",
       custom_field="value"  # Add custom context
   )
   ```

4. **Type hints**: Utilities are fully typed - use type checking
   ```python
   # Type checker will catch errors
   result: AnalysisResult = create_default_result(
       AnalysisResult,  # Correct type
       "error message"
   )
   ```

---

## Migration Checklist

When refactoring an existing agent:

- [ ] Replace error handling with `handle_agent_error()`
- [ ] Use `log_agent_execution()` for consistent logging
- [ ] Refactor prompt creation with template functions
- [ ] Update result models to inherit from base classes
- [ ] Use formatting utilities for data display
- [ ] Add validation utilities to API routes
- [ ] Test thoroughly
- [ ] Update documentation

---

For more details, see `/home/user/AIOps/DUPLICATION_ANALYSIS_REPORT.md`
