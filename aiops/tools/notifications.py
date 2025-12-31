"""Notification system for AIOps framework."""

import aiohttp
import asyncio
from typing import Dict, Any, Optional
from aiops.core.logger import get_logger
from aiops.core.config import get_config

logger = get_logger(__name__)

# Default timeout for HTTP requests
DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=30, connect=10, sock_read=10)


class NotificationService:
    """Service for sending notifications to various platforms."""

    @staticmethod
    async def send_slack(
        message: str,
        webhook_url: Optional[str] = None,
        attachments: Optional[list] = None,
    ) -> bool:
        """
        Send notification to Slack.

        Args:
            message: Message to send
            webhook_url: Slack webhook URL (uses config if not provided)
            attachments: Optional Slack attachments

        Returns:
            Success status
        """
        config = get_config()
        webhook_url = webhook_url or config.slack_webhook_url

        if not webhook_url:
            logger.warning("Slack webhook URL not configured")
            return False

        payload = {"text": message}
        if attachments:
            payload["attachments"] = attachments

        try:
            async with aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT) as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info("Slack notification sent successfully")
                        return True
                    else:
                        logger.error(f"Slack notification failed: {response.status}")
                        return False

        except asyncio.TimeoutError:
            logger.error("Slack notification timed out")
            return False
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
            return False

    @staticmethod
    async def send_discord(
        message: str,
        webhook_url: Optional[str] = None,
        embeds: Optional[list] = None,
    ) -> bool:
        """
        Send notification to Discord.

        Args:
            message: Message to send
            webhook_url: Discord webhook URL
            embeds: Optional Discord embeds

        Returns:
            Success status
        """
        config = get_config()
        webhook_url = webhook_url or config.discord_webhook_url

        if not webhook_url:
            logger.warning("Discord webhook URL not configured")
            return False

        payload = {"content": message}
        if embeds:
            payload["embeds"] = embeds

        try:
            async with aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT) as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status in [200, 204]:
                        logger.info("Discord notification sent successfully")
                        return True
                    else:
                        logger.error(f"Discord notification failed: {response.status}")
                        return False

        except asyncio.TimeoutError:
            logger.error("Discord notification timed out")
            return False
        except Exception as e:
            logger.error(f"Error sending Discord notification: {e}")
            return False

    @staticmethod
    async def send_webhook(
        url: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Send generic webhook notification.

        Args:
            url: Webhook URL
            payload: JSON payload
            headers: Optional HTTP headers

        Returns:
            Success status
        """
        headers = headers or {"Content-Type": "application/json"}

        try:
            async with aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT) as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status in [200, 201, 204]:
                        logger.info(f"Webhook notification sent to {url}")
                        return True
                    else:
                        logger.error(f"Webhook notification failed: {response.status}")
                        return False

        except asyncio.TimeoutError:
            logger.error(f"Webhook notification to {url} timed out")
            return False
        except Exception as e:
            logger.error(f"Error sending webhook: {e}")
            return False

    @staticmethod
    async def notify_code_review_complete(
        file_name: str,
        score: float,
        issues_count: int,
        critical_count: int,
    ):
        """Send notification when code review is complete."""
        message = f"""🤖 Code Review Complete

**File**: {file_name}
**Score**: {score}/100
**Issues**: {issues_count} total, {critical_count} critical

{"✅ Looks good!" if score >= 80 else "⚠️ Needs attention" if score >= 60 else "❌ Significant issues found"}
"""

        slack_attachments = [
            {
                "color": "good" if score >= 80 else "warning" if score >= 60 else "danger",
                "fields": [
                    {"title": "File", "value": file_name, "short": True},
                    {"title": "Score", "value": f"{score}/100", "short": True},
                    {"title": "Total Issues", "value": str(issues_count), "short": True},
                    {"title": "Critical Issues", "value": str(critical_count), "short": True},
                ],
            }
        ]

        # Send notifications in parallel for better performance
        await asyncio.gather(
            NotificationService.send_slack(message, attachments=slack_attachments),
            NotificationService.send_discord(message),
            return_exceptions=True
        )

    @staticmethod
    async def notify_security_issue(
        severity: str,
        title: str,
        description: str,
        file: Optional[str] = None,
    ):
        """Send notification for security issues."""
        emoji = "🔴" if severity == "critical" else "🟠" if severity == "high" else "🟡"

        message = f"""{emoji} Security Alert - {severity.upper()}

**{title}**

{description}

{f"**File**: {file}" if file else ""}
"""

        # Send notifications in parallel for better performance
        await asyncio.gather(
            NotificationService.send_slack(message),
            NotificationService.send_discord(message),
            return_exceptions=True
        )

    @staticmethod
    async def notify_pipeline_optimization(
        pipeline_name: str,
        current_duration: float,
        estimated_duration: float,
        improvements: list,
    ):
        """Send notification for pipeline optimization suggestions."""
        improvement_pct = (
            (current_duration - estimated_duration) / current_duration * 100
        )

        message = f"""⚡ Pipeline Optimization Available

**Pipeline**: {pipeline_name}
**Current Duration**: {current_duration:.1f}m
**Estimated After Optimization**: {estimated_duration:.1f}m
**Improvement**: {improvement_pct:.1f}%

**Top Recommendations**:
"""

        for i, improvement in enumerate(improvements[:3], 1):
            message += f"{i}. {improvement}\n"

        # Send notifications in parallel for better performance
        await asyncio.gather(
            NotificationService.send_slack(message),
            NotificationService.send_discord(message),
            return_exceptions=True
        )

    @staticmethod
    async def notify_anomaly_detected(
        metric_name: str,
        current_value: Any,
        baseline_value: Any,
        severity: str,
    ):
        """Send notification for detected anomalies."""
        emoji = "🚨" if severity == "critical" else "⚠️" if severity == "high" else "ℹ️"

        message = f"""{emoji} Anomaly Detected - {severity.upper()}

**Metric**: {metric_name}
**Current Value**: {current_value}
**Baseline**: {baseline_value}

Immediate attention may be required!
"""

        if severity in ["critical", "high"]:
            # Send notifications in parallel for better performance
            await asyncio.gather(
                NotificationService.send_slack(message),
                NotificationService.send_discord(message),
                return_exceptions=True
            )

    @staticmethod
    async def notify_test_generation(
        file_name: str,
        tests_generated: int,
        coverage_estimate: Optional[str] = None,
    ):
        """Send notification when tests are generated."""
        message = f"""🧪 Tests Generated

**File**: {file_name}
**Tests Created**: {tests_generated}
{f"**Estimated Coverage**: {coverage_estimate}" if coverage_estimate else ""}

Review and run the generated tests!
"""

        await NotificationService.send_slack(message)


# Alias for backward compatibility
NotificationManager = NotificationService
