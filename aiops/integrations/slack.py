"""Slack Integration

Provides Slack webhook and bot integration for notifications and alerts.
"""

import asyncio
from typing import Dict, Any, Optional, List
import aiohttp
from datetime import datetime

from aiops.core.structured_logger import get_structured_logger
from aiops.core.exceptions import IntegrationError


logger = get_structured_logger(__name__)


class SlackNotifier:
    """Slack webhook notifier for sending messages."""

    def __init__(self, webhook_url: str):
        """Initialize Slack notifier.

        Args:
            webhook_url: Slack incoming webhook URL
        """
        self.webhook_url = webhook_url

    async def send_message(
        self,
        message: Dict[str, Any],
        timeout: float = 10.0,
    ) -> bool:
        """Send message to Slack via webhook.

        Args:
            message: Message payload (Slack format)
            timeout: Request timeout in seconds

        Returns:
            True if successful, False otherwise

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
                        logger.info("Slack message sent successfully")
                        return True
                    else:
                        error_text = await response.text()
                        raise IntegrationError(
                            f"Slack webhook failed: {response.status} - {error_text}"
                        )

        except asyncio.TimeoutError:
            raise IntegrationError(f"Slack webhook timed out after {timeout}s")
        except aiohttp.ClientError as e:
            raise IntegrationError(f"Slack webhook error: {e}")

    async def send_simple_message(
        self,
        text: str,
        channel: Optional[str] = None,
        username: Optional[str] = None,
        icon_emoji: Optional[str] = None,
    ) -> bool:
        """Send a simple text message to Slack.

        Args:
            text: Message text
            channel: Override default channel
            username: Override default username
            icon_emoji: Override default icon (e.g., ":robot_face:")

        Returns:
            True if successful
        """
        message = {"text": text}

        if channel:
            message["channel"] = channel
        if username:
            message["username"] = username
        if icon_emoji:
            message["icon_emoji"] = icon_emoji

        return await self.send_message(message)

    async def send_rich_message(
        self,
        title: str,
        message: str,
        color: str = "#36a64f",
        fields: Optional[List[Dict[str, Any]]] = None,
        footer: Optional[str] = None,
    ) -> bool:
        """Send a rich formatted message to Slack.

        Args:
            title: Message title
            message: Message text
            color: Attachment color (hex color code)
            fields: Additional fields to display
            footer: Footer text

        Returns:
            True if successful
        """
        attachment = {
            "color": color,
            "title": title,
            "text": message,
            "footer": footer or "AIOps",
            "ts": int(datetime.now().timestamp()),
        }

        if fields:
            attachment["fields"] = fields

        return await self.send_message({"attachments": [attachment]})


class SlackClient:
    """Full-featured Slack API client (requires bot token)."""

    def __init__(self, bot_token: str):
        """Initialize Slack client.

        Args:
            bot_token: Slack bot OAuth token (starts with xoxb-)
        """
        self.bot_token = bot_token
        self.base_url = "https://slack.com/api"

    async def _make_request(
        self,
        endpoint: str,
        method: str = "POST",
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make request to Slack API.

        Args:
            endpoint: API endpoint (e.g., "chat.postMessage")
            method: HTTP method
            data: Request payload

        Returns:
            API response

        Raises:
            IntegrationError: If request fails
        """
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.bot_token}",
            "Content-Type": "application/json",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    json=data,
                ) as response:
                    result = await response.json()

                    if not result.get("ok"):
                        error = result.get("error", "unknown error")
                        raise IntegrationError(f"Slack API error: {error}")

                    return result

        except aiohttp.ClientError as e:
            raise IntegrationError(f"Slack API request failed: {e}")

    async def send_message(
        self,
        message: Dict[str, Any],
        channel: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send message using Slack API.

        Args:
            message: Message payload
            channel: Channel ID or name

        Returns:
            API response
        """
        if channel:
            message["channel"] = channel

        return await self._make_request("chat.postMessage", data=message)

    async def post_message(
        self,
        channel: str,
        text: str,
        blocks: Optional[List[Dict]] = None,
        attachments: Optional[List[Dict]] = None,
        thread_ts: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Post a message to a channel.

        Args:
            channel: Channel ID or name
            text: Message text (fallback)
            blocks: Block Kit blocks for rich formatting
            attachments: Legacy attachments
            thread_ts: Thread timestamp (for replies)

        Returns:
            API response including timestamp
        """
        data = {
            "channel": channel,
            "text": text,
        }

        if blocks:
            data["blocks"] = blocks
        if attachments:
            data["attachments"] = attachments
        if thread_ts:
            data["thread_ts"] = thread_ts

        return await self._make_request("chat.postMessage", data=data)

    async def upload_file(
        self,
        channels: List[str],
        file_path: Optional[str] = None,
        content: Optional[str] = None,
        filename: Optional[str] = None,
        title: Optional[str] = None,
        initial_comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload a file to Slack.

        Args:
            channels: List of channel IDs
            file_path: Path to file to upload
            content: File content (alternative to file_path)
            filename: Filename to display
            title: File title
            initial_comment: Comment to post with file

        Returns:
            API response
        """
        data = {"channels": ",".join(channels)}

        if file_path:
            # For simplicity, we'll just use content here
            # In production, you'd handle file uploads differently
            with open(file_path, "r") as f:
                data["content"] = f.read()
        elif content:
            data["content"] = content

        if filename:
            data["filename"] = filename
        if title:
            data["title"] = title
        if initial_comment:
            data["initial_comment"] = initial_comment

        return await self._make_request("files.upload", data=data)

    async def add_reaction(
        self,
        channel: str,
        timestamp: str,
        name: str,
    ) -> Dict[str, Any]:
        """Add emoji reaction to a message.

        Args:
            channel: Channel ID
            timestamp: Message timestamp
            name: Emoji name (without colons)

        Returns:
            API response
        """
        return await self._make_request(
            "reactions.add",
            data={
                "channel": channel,
                "timestamp": timestamp,
                "name": name,
            },
        )

    async def list_channels(self) -> List[Dict[str, Any]]:
        """List all channels the bot has access to.

        Returns:
            List of channel information
        """
        response = await self._make_request(
            "conversations.list",
            method="GET",
        )

        return response.get("channels", [])

    async def get_channel_info(self, channel_id: str) -> Dict[str, Any]:
        """Get information about a channel.

        Args:
            channel_id: Channel ID

        Returns:
            Channel information
        """
        response = await self._make_request(
            "conversations.info",
            method="GET",
            data={"channel": channel_id},
        )

        return response.get("channel", {})

    async def set_channel_topic(
        self,
        channel: str,
        topic: str,
    ) -> Dict[str, Any]:
        """Set channel topic.

        Args:
            channel: Channel ID
            topic: New topic

        Returns:
            API response
        """
        return await self._make_request(
            "conversations.setTopic",
            data={
                "channel": channel,
                "topic": topic,
            },
        )


def create_code_review_message(
    pr_number: int,
    score: float,
    issues_count: int,
    critical_issues: int,
    file_count: int,
) -> Dict[str, Any]:
    """Create a formatted Slack message for code review results.

    Args:
        pr_number: Pull request number
        score: Code quality score (0-100)
        issues_count: Total issues found
        critical_issues: Critical issues found
        file_count: Number of files reviewed

    Returns:
        Slack message payload
    """
    # Determine color based on score
    if score >= 85:
        color = "good"  # Green
        status_emoji = ":white_check_mark:"
    elif score >= 70:
        color = "warning"  # Yellow
        status_emoji = ":warning:"
    else:
        color = "danger"  # Red
        status_emoji = ":x:"

    return {
        "attachments": [
            {
                "color": color,
                "title": f"{status_emoji} Code Review: PR #{pr_number}",
                "fields": [
                    {
                        "title": "Quality Score",
                        "value": f"{score:.1f}/100",
                        "short": True,
                    },
                    {
                        "title": "Files Reviewed",
                        "value": str(file_count),
                        "short": True,
                    },
                    {
                        "title": "Total Issues",
                        "value": str(issues_count),
                        "short": True,
                    },
                    {
                        "title": "Critical Issues",
                        "value": f"{critical_issues} :rotating_light:" if critical_issues > 0 else "0",
                        "short": True,
                    },
                ],
                "footer": "AIOps Code Review",
                "ts": int(datetime.now().timestamp()),
            }
        ]
    }


def create_deployment_message(
    environment: str,
    version: str,
    status: str,
    duration_seconds: Optional[float] = None,
) -> Dict[str, Any]:
    """Create a formatted Slack message for deployment notifications.

    Args:
        environment: Deployment environment (dev/staging/production)
        version: Version deployed
        status: Deployment status (success/failure)
        duration_seconds: Deployment duration

    Returns:
        Slack message payload
    """
    if status == "success":
        color = "good"
        emoji = ":rocket:"
    else:
        color = "danger"
        emoji = ":x:"

    fields = [
        {"title": "Environment", "value": environment.upper(), "short": True},
        {"title": "Version", "value": version, "short": True},
        {"title": "Status", "value": status.upper(), "short": True},
    ]

    if duration_seconds is not None:
        fields.append({
            "title": "Duration",
            "value": f"{duration_seconds:.1f}s",
            "short": True,
        })

    return {
        "attachments": [
            {
                "color": color,
                "title": f"{emoji} Deployment to {environment.upper()}",
                "fields": fields,
                "footer": "AIOps Deployment",
                "ts": int(datetime.now().timestamp()),
            }
        ]
    }
