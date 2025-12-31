"""Helper utilities for agent implementations."""

import re
from typing import Any, Dict, Optional, Type, Callable
from functools import wraps
from pydantic import BaseModel
from aiops.core.logger import get_logger
from aiops.utils.result_models import create_default_result

logger = get_logger(__name__)


def create_default_error_result(
    result_class: Type[BaseModel],
    error: Exception,
    **kwargs: Any
) -> BaseModel:
    """
    Create a default error result for an agent execution failure.

    Args:
        result_class: The Pydantic model class for the result
        error: The exception that occurred
        **kwargs: Additional fields to set on the result

    Returns:
        Instance of result_class with error details
    """
    error_message = str(error)
    return create_default_result(
        result_class=result_class,
        error_message=error_message,
        **kwargs
    )


def log_agent_execution(
    agent_name: str,
    operation: str,
    phase: str = "start",
    **context: Any
) -> None:
    """
    Log agent execution with consistent formatting.

    Args:
        agent_name: Name of the agent
        operation: Operation being performed
        phase: Execution phase (start, complete, error)
        **context: Additional context to log
    """
    context_str = ", ".join(f"{k}={v}" for k, v in context.items()) if context else ""

    if phase == "start":
        message = f"{agent_name}: Starting {operation}"
    elif phase == "complete":
        message = f"{agent_name}: Completed {operation}"
    elif phase == "error":
        message = f"{agent_name}: Error in {operation}"
    else:
        message = f"{agent_name}: {operation} - {phase}"

    if context_str:
        message += f" ({context_str})"

    if phase == "error":
        logger.error(message)
    else:
        logger.info(message)


def format_dict_for_prompt(
    data: Dict[str, Any],
    indent: int = 0,
    max_depth: int = 3
) -> str:
    """
    Format a dictionary for inclusion in LLM prompts.

    Args:
        data: Dictionary to format
        indent: Current indentation level
        max_depth: Maximum nesting depth to display

    Returns:
        Formatted string representation
    """
    if indent >= max_depth:
        return str(data)

    lines = []
    indent_str = "  " * indent

    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{indent_str}- {key}:")
            lines.append(format_dict_for_prompt(value, indent + 1, max_depth))
        elif isinstance(value, (list, tuple)):
            lines.append(f"{indent_str}- {key}: [{len(value)} items]")
            if indent < max_depth - 1:
                for i, item in enumerate(list(value)[:5]):  # Limit to 5 items
                    if isinstance(item, dict):
                        lines.append(f"{indent_str}  {i+1}. {format_dict_for_prompt(item, indent + 2, max_depth)}")
                    else:
                        lines.append(f"{indent_str}  {i+1}. {item}")
                if len(value) > 5:
                    lines.append(f"{indent_str}  ... and {len(value) - 5} more")
        else:
            lines.append(f"{indent_str}- {key}: {value}")

    return "\n".join(lines)


def extract_code_from_response(
    response: str,
    language: Optional[str] = None
) -> str:
    """
    Extract code block from LLM response.

    Args:
        response: LLM response text
        language: Expected programming language (optional)

    Returns:
        Extracted code or original response if no code block found
    """
    # Look for markdown code blocks
    if "```" in response:
        blocks = response.split("```")
        for i in range(1, len(blocks), 2):  # Every odd index is inside code block
            block = blocks[i].strip()

            # Check if block starts with language identifier
            if language:
                if block.startswith(language):
                    # Remove language identifier and return code
                    return block[len(language):].strip()
            else:
                # Skip first line if it looks like a language identifier
                lines = block.split("\n")
                if lines and len(lines[0].split()) == 1 and lines[0].isalpha():
                    return "\n".join(lines[1:]).strip()
                return block

    return response


def create_system_prompt_template(
    role: str,
    expertise_areas: list[str],
    analysis_focus: list[str],
    output_requirements: Optional[list[str]] = None,
    additional_context: Optional[str] = None
) -> str:
    """
    Create a standardized system prompt template for agents.

    Args:
        role: The role/persona for the LLM (e.g., "expert security researcher")
        expertise_areas: List of expertise areas
        analysis_focus: List of focus areas for analysis
        output_requirements: List of output requirements
        additional_context: Additional context to include

    Returns:
        Formatted system prompt
    """
    prompt_parts = [f"You are {role}.\n"]

    if expertise_areas:
        prompt_parts.append("\nExpertise Areas:")
        for area in expertise_areas:
            prompt_parts.append(f"- {area}")

    if analysis_focus:
        prompt_parts.append("\n\nAnalysis Focus:")
        for i, focus in enumerate(analysis_focus, 1):
            prompt_parts.append(f"{i}. {focus}")

    if output_requirements:
        prompt_parts.append("\n\nOutput Requirements:")
        for req in output_requirements:
            prompt_parts.append(f"- {req}")

    if additional_context:
        prompt_parts.append(f"\n\n{additional_context}")

    return "\n".join(prompt_parts)


def create_user_prompt_template(
    operation: str,
    main_content: str,
    context: Optional[str] = None,
    additional_sections: Optional[Dict[str, str]] = None,
    requirements: Optional[list[str]] = None
) -> str:
    """
    Create a standardized user prompt template for agents.

    Args:
        operation: The operation to perform (e.g., "Analyze the following code")
        main_content: The main content to analyze
        context: Optional context information
        additional_sections: Additional sections as {title: content}
        requirements: List of specific requirements

    Returns:
        Formatted user prompt
    """
    prompt_parts = [f"{operation}:\n"]

    if context:
        prompt_parts.append(f"\n**Context**: {context}\n")

    prompt_parts.append(f"\n{main_content}\n")

    if additional_sections:
        for title, content in additional_sections.items():
            prompt_parts.append(f"\n**{title}**:\n{content}\n")

    if requirements:
        prompt_parts.append("\nRequirements:")
        for i, req in enumerate(requirements, 1):
            prompt_parts.append(f"{i}. {req}")

    return "\n".join(prompt_parts)


def handle_agent_error(
    agent_name: str,
    operation: str,
    error: Exception,
    result_class: Type[BaseModel],
    **result_overrides: Any
) -> BaseModel:
    """
    Standard error handling for agent operations.

    Args:
        agent_name: Name of the agent
        operation: Operation that failed
        error: The exception that occurred
        result_class: Result class to instantiate
        **result_overrides: Additional fields to set on result

    Returns:
        Error result instance
    """
    log_agent_execution(
        agent_name=agent_name,
        operation=operation,
        phase="error",
        error=str(error)
    )

    return create_default_error_result(
        result_class=result_class,
        error=error,
        **result_overrides
    )
