"""Microsoft Teams Integration

Provides Microsoft Teams webhook integration for notifications.
"""

import asyncio
from typing import Dict, Any, Optional, List
import aiohttp
from datetime import datetime

from aiops.core.structured_logger import get_structured_logger
from aiops.core.exceptions import IntegrationError


logger = get_structured_logger(__name__)


class TeamsNotifier:
    """Microsoft Teams webhook notifier."""

    def __init__(self, webhook_url: str):
        """Initialize Teams notifier.

        Args:
            webhook_url: Teams incoming webhook URL
        """
        self.webhook_url = webhook_url

    async def send_message(
        self,
        message: Dict[str, Any],
        timeout: float = 10.0,
    ) -> bool:
        """Send message to Teams via webhook.

        Args:
            message: Message payload (Teams format)
            timeout: Request timeout in seconds

        Returns:
            True if successful

        Raises:
            IntegrationError: If sending fails
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=message,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as response:
                    if response.status == 200:
                        logger.info("Teams message sent successfully")
                        return True
                    else:
                        error_text = await response.text()
                        raise IntegrationError(
                            f"Teams webhook failed: {response.status} - {error_text}"
                        )

        except asyncio.TimeoutError:
            raise IntegrationError(f"Teams webhook timed out after {timeout}s")
        except aiohttp.ClientError as e:
            raise IntegrationError(f"Teams webhook error: {e}")

    async def send_simple_message(
        self,
        text: str,
        title: Optional[str] = None,
    ) -> bool:
        """Send a simple text message to Teams.

        Args:
            text: Message text
            title: Message title

        Returns:
            True if successful
        """
        message = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "text": text,
        }

        if title:
            message["title"] = title

        return await self.send_message(message)

    async def send_adaptive_card(
        self,
        card: Dict[str, Any],
    ) -> bool:
        """Send an Adaptive Card to Teams.

        Args:
            card: Adaptive Card JSON

        Returns:
            True if successful
        """
        message = {
            "type": "message",
            "attachments": [{
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": card,
            }],
        }

        return await self.send_message(message)

    async def send_notification(
        self,
        title: str,
        message: str,
        severity: str = "default",
        facts: Optional[List[Dict[str, str]]] = None,
        actions: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """Send a formatted notification to Teams.

        Args:
            title: Notification title
            message: Notification message
            severity: Severity level (default/good/warning/attention)
            facts: List of key-value facts
            actions: List of actions (buttons)

        Returns:
            True if successful
        """
        # Map severity to style
        style_map = {
            "default": "default",
            "info": "default",
            "success": "good",
            "good": "good",
            "warning": "warning",
            "error": "attention",
            "attention": "attention",
            "critical": "attention",
        }

        style = style_map.get(severity.lower(), "default")

        card = {
            "type": "AdaptiveCard",
            "body": [
                {
                    "type": "Container",
                    "style": style,
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": title,
                            "weight": "Bolder",
                            "size": "Large",
                        },
                        {
                            "type": "TextBlock",
                            "text": message,
                            "wrap": True,
                        },
                    ],
                },
            ],
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.4",
        }

        # Add facts if provided
        if facts:
            card["body"].append({
                "type": "FactSet",
                "facts": facts,
            })

        # Add actions if provided
        if actions:
            card["actions"] = actions

        return await self.send_adaptive_card(card)


def create_code_review_card(
    pr_number: int,
    score: float,
    issues_count: int,
    critical_issues: int,
    file_count: int,
    pr_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Create an Adaptive Card for code review results.

    Args:
        pr_number: Pull request number
        score: Code quality score (0-100)
        issues_count: Total issues found
        critical_issues: Critical issues found
        file_count: Number of files reviewed
        pr_url: URL to the pull request

    Returns:
        Adaptive Card JSON
    """
    # Determine severity based on score
    if score >= 85:
        severity = "good"
        status_emoji = "✅"
    elif score >= 70:
        severity = "warning"
        status_emoji = "⚠️"
    else:
        severity = "attention"
        status_emoji = "❌"

    facts = [
        {"title": "Quality Score", "value": f"{score:.1f}/100"},
        {"title": "Files Reviewed", "value": str(file_count)},
        {"title": "Total Issues", "value": str(issues_count)},
        {"title": "Critical Issues", "value": f"{critical_issues} 🚨" if critical_issues > 0 else "0"},
    ]

    card = {
        "type": "AdaptiveCard",
        "body": [
            {
                "type": "Container",
                "style": severity,
                "items": [
                    {
                        "type": "TextBlock",
                        "text": f"{status_emoji} Code Review: PR #{pr_number}",
                        "weight": "Bolder",
                        "size": "Large",
                    },
                ],
            },
            {
                "type": "FactSet",
                "facts": facts,
            },
        ],
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
    }

    # Add action button to view PR
    if pr_url:
        card["actions"] = [{
            "type": "Action.OpenUrl",
            "title": "View Pull Request",
            "url": pr_url,
        }]

    return card


def create_deployment_card(
    environment: str,
    version: str,
    status: str,
    duration_seconds: Optional[float] = None,
    deployed_by: Optional[str] = None,
) -> Dict[str, Any]:
    """Create an Adaptive Card for deployment notifications.

    Args:
        environment: Deployment environment
        version: Version deployed
        status: Deployment status (success/failure)
        duration_seconds: Deployment duration
        deployed_by: Person who triggered deployment

    Returns:
        Adaptive Card JSON
    """
    if status == "success":
        severity = "good"
        emoji = "🚀"
    else:
        severity = "attention"
        emoji = "❌"

    facts = [
        {"title": "Environment", "value": environment.upper()},
        {"title": "Version", "value": version},
        {"title": "Status", "value": status.upper()},
    ]

    if duration_seconds is not None:
        facts.append({"title": "Duration", "value": f"{duration_seconds:.1f}s"})

    if deployed_by:
        facts.append({"title": "Deployed By", "value": deployed_by})

    return {
        "type": "AdaptiveCard",
        "body": [
            {
                "type": "Container",
                "style": severity,
                "items": [
                    {
                        "type": "TextBlock",
                        "text": f"{emoji} Deployment to {environment.upper()}",
                        "weight": "Bolder",
                        "size": "Large",
                    },
                ],
            },
            {
                "type": "FactSet",
                "facts": facts,
            },
        ],
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
    }


def create_alert_card(
    title: str,
    message: str,
    severity: str,
    affected_system: Optional[str] = None,
    incident_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Create an Adaptive Card for system alerts.

    Args:
        title: Alert title
        message: Alert message
        severity: Severity level (critical/high/medium/low)
        affected_system: System or service affected
        incident_url: URL to incident details

    Returns:
        Adaptive Card JSON
    """
    severity_map = {
        "critical": ("attention", "🚨"),
        "high": ("attention", "⚠️"),
        "medium": ("warning", "⚠️"),
        "low": ("default", "ℹ️"),
    }

    style, emoji = severity_map.get(severity.lower(), ("default", "ℹ️"))

    card = {
        "type": "AdaptiveCard",
        "body": [
            {
                "type": "Container",
                "style": style,
                "items": [
                    {
                        "type": "TextBlock",
                        "text": f"{emoji} {title}",
                        "weight": "Bolder",
                        "size": "Large",
                    },
                    {
                        "type": "TextBlock",
                        "text": message,
                        "wrap": True,
                    },
                ],
            },
        ],
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
    }

    facts = [
        {"title": "Severity", "value": severity.upper()},
        {"title": "Time", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")},
    ]

    if affected_system:
        facts.append({"title": "Affected System", "value": affected_system})

    card["body"].append({"type": "FactSet", "facts": facts})

    # Add action button if URL provided
    if incident_url:
        card["actions"] = [{
            "type": "Action.OpenUrl",
            "title": "View Incident",
            "url": incident_url,
        }]

    return card


def create_metric_card(
    metric_name: str,
    current_value: float,
    threshold: float,
    trend: str,  # "up", "down", "stable"
    unit: str = "",
) -> Dict[str, Any]:
    """Create an Adaptive Card for metric reporting.

    Args:
        metric_name: Name of the metric
        current_value: Current metric value
        threshold: Threshold value
        trend: Trend direction
        unit: Unit of measurement

    Returns:
        Adaptive Card JSON
    """
    # Determine severity based on threshold
    if current_value > threshold:
        severity = "attention"
        status = "Above Threshold"
    else:
        severity = "good"
        status = "Within Threshold"

    # Trend emoji
    trend_emoji = {
        "up": "📈",
        "down": "📉",
        "stable": "➡️",
    }.get(trend, "")

    return {
        "type": "AdaptiveCard",
        "body": [
            {
                "type": "Container",
                "style": severity,
                "items": [
                    {
                        "type": "TextBlock",
                        "text": f"{trend_emoji} {metric_name}",
                        "weight": "Bolder",
                        "size": "Large",
                    },
                ],
            },
            {
                "type": "FactSet",
                "facts": [
                    {"title": "Current Value", "value": f"{current_value}{unit}"},
                    {"title": "Threshold", "value": f"{threshold}{unit}"},
                    {"title": "Status", "value": status},
                    {"title": "Trend", "value": trend.capitalize()},
                ],
            },
        ],
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
    }
