"""Shared formatting utilities for prompts and reports."""

from datetime import datetime
from typing import Any, Dict, List, Optional


def format_metrics_dict(
    metrics: Dict[str, Any],
    indent: int = 0,
    max_depth: int = 3
) -> str:
    """
    Format metrics dictionary for display in prompts.

    Args:
        metrics: Metrics dictionary
        indent: Current indentation level
        max_depth: Maximum nesting depth

    Returns:
        Formatted metrics string
    """
    formatted = ""
    indent_str = "  " * indent

    for key, value in metrics.items():
        if isinstance(value, dict) and indent < max_depth:
            formatted += f"{indent_str}{key}:\n"
            for sub_key, sub_value in value.items():
                formatted += f"{indent_str}  - {sub_key}: {sub_value}\n"
        else:
            formatted += f"{indent_str}- {key}: {value}\n"

    return formatted


def format_list_for_prompt(
    items: List[Any],
    title: Optional[str] = None,
    max_items: Optional[int] = None,
    numbered: bool = True
) -> str:
    """
    Format list for inclusion in prompts.

    Args:
        items: List of items to format
        title: Optional title for the list
        max_items: Maximum number of items to include
        numbered: Use numbered list (vs bullet points)

    Returns:
        Formatted list string
    """
    lines = []

    if title:
        lines.append(f"{title}:")

    display_items = items[:max_items] if max_items else items

    for i, item in enumerate(display_items, 1):
        if numbered:
            lines.append(f"{i}. {item}")
        else:
            lines.append(f"- {item}")

    if max_items and len(items) > max_items:
        lines.append(f"... and {len(items) - max_items} more")

    return "\n".join(lines)


def format_timestamp(
    dt: Optional[datetime] = None,
    format_str: str = "%Y-%m-%d %H:%M:%S"
) -> str:
    """
    Format timestamp consistently.

    Args:
        dt: Datetime to format (uses now if None)
        format_str: Format string

    Returns:
        Formatted timestamp string
    """
    if dt is None:
        dt = datetime.now()

    return dt.strftime(format_str)


def generate_markdown_report(
    title: str,
    sections: Dict[str, str],
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate a markdown report with consistent formatting.

    Args:
        title: Report title
        sections: Dictionary of section_title: section_content
        metadata: Optional metadata to include at top

    Returns:
        Formatted markdown report
    """
    lines = [f"# {title}\n"]

    if metadata:
        lines.append("## Metadata\n")
        for key, value in metadata.items():
            lines.append(f"- **{key}**: {value}")
        lines.append("")

    for section_title, section_content in sections.items():
        lines.append(f"## {section_title}\n")
        lines.append(section_content)
        lines.append("")

    return "\n".join(lines)


def format_code_block(
    code: str,
    language: Optional[str] = None,
    title: Optional[str] = None
) -> str:
    """
    Format code in markdown code block.

    Args:
        code: Code to format
        language: Programming language for syntax highlighting
        title: Optional title for the code block

    Returns:
        Formatted code block
    """
    lines = []

    if title:
        lines.append(f"**{title}**:")

    lang_str = language if language else ""
    lines.append(f"```{lang_str}")
    lines.append(code)
    lines.append("```")

    return "\n".join(lines)


def format_table(
    headers: List[str],
    rows: List[List[Any]],
    title: Optional[str] = None
) -> str:
    """
    Format data as markdown table.

    Args:
        headers: Table headers
        rows: Table rows
        title: Optional title

    Returns:
        Formatted markdown table
    """
    lines = []

    if title:
        lines.append(f"### {title}\n")

    # Header row
    lines.append("| " + " | ".join(str(h) for h in headers) + " |")

    # Separator row
    lines.append("| " + " | ".join("---" for _ in headers) + " |")

    # Data rows
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")

    return "\n".join(lines)


def truncate_text(
    text: str,
    max_length: int,
    suffix: str = "..."
) -> str:
    """
    Truncate text to maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def format_percentage(
    value: float,
    decimals: int = 2
) -> str:
    """
    Format value as percentage.

    Args:
        value: Value to format (0-1 or 0-100)
        decimals: Number of decimal places

    Returns:
        Formatted percentage string
    """
    # If value is between 0 and 1, convert to percentage
    if 0 <= value <= 1:
        value = value * 100

    return f"{value:.{decimals}f}%"


def format_file_size(
    size_bytes: int,
    precision: int = 2
) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes
        precision: Decimal precision

    Returns:
        Formatted size string
    """
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(size_bytes)
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    return f"{size:.{precision}f} {units[unit_index]}"
