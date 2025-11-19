"""Notification Management System

Provides a unified interface for sending notifications across multiple channels.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from aiops.core.structured_logger import get_structured_logger


logger = get_structured_logger(__name__)


class NotificationLevel(str, Enum):
    """Notification severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    SUCCESS = "success"


class NotificationChannel(str, Enum):
    """Supported notification channels."""
    SLACK = "slack"
    TEAMS = "teams"
    EMAIL = "email"
    WEBHOOK = "webhook"
    CONSOLE = "console"


class Notification(BaseModel):
    """A notification message."""

    title: str
    message: str
    level: NotificationLevel = NotificationLevel.INFO
    timestamp: datetime = Field(default_factory=datetime.now)
    channels: List[NotificationChannel] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)

    def to_slack_format(self) -> Dict[str, Any]:
        """Convert to Slack message format."""
        color_map = {
            NotificationLevel.INFO: "#36a64f",  # Green
            NotificationLevel.SUCCESS: "#2eb886",  # Teal
            NotificationLevel.WARNING: "#ff9800",  # Orange
            NotificationLevel.ERROR: "#ff5252",  # Red
            NotificationLevel.CRITICAL: "#d32f2f",  # Dark Red
        }

        icon_map = {
            NotificationLevel.INFO: ":information_source:",
            NotificationLevel.SUCCESS: ":white_check_mark:",
            NotificationLevel.WARNING: ":warning:",
            NotificationLevel.ERROR: ":x:",
            NotificationLevel.CRITICAL: ":rotating_light:",
        }

        attachments = [{
            "color": color_map.get(self.level, "#808080"),
            "title": f"{icon_map.get(self.level, '')} {self.title}",
            "text": self.message,
            "footer": "AIOps Notification",
            "ts": int(self.timestamp.timestamp()),
            "fields": [],
        }]

        # Add metadata as fields
        for key, value in self.metadata.items():
            attachments[0]["fields"].append({
                "title": key.replace("_", " ").title(),
                "value": str(value),
                "short": len(str(value)) < 30,
            })

        # Add tags
        if self.tags:
            attachments[0]["fields"].append({
                "title": "Tags",
                "value": ", ".join(f"`{tag}`" for tag in self.tags),
                "short": False,
            })

        return {
            "attachments": attachments,
        }

    def to_teams_format(self) -> Dict[str, Any]:
        """Convert to Microsoft Teams message format (Adaptive Card)."""
        color_map = {
            NotificationLevel.INFO: "Accent",
            NotificationLevel.SUCCESS: "Good",
            NotificationLevel.WARNING: "Warning",
            NotificationLevel.ERROR: "Attention",
            NotificationLevel.CRITICAL": "Attention",
        }

        icon_map = {
            NotificationLevel.INFO: "ℹ️",
            NotificationLevel.SUCCESS: "✅",
            NotificationLevel.WARNING: "⚠️",
            NotificationLevel.ERROR: "❌",
            NotificationLevel.CRITICAL: "🚨",
        }

        # Build facts for metadata
        facts = []
        for key, value in self.metadata.items():
            facts.append({
                "title": key.replace("_", " ").title(),
                "value": str(value),
            })

        # Add timestamp
        facts.append({
            "title": "Time",
            "value": self.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
        })

        message = {
            "type": "message",
            "attachments": [{
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "type": "AdaptiveCard",
                    "body": [
                        {
                            "type": "Container",
                            "style": color_map.get(self.level, "default"),
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": f"{icon_map.get(self.level, '')} {self.title}",
                                    "weight": "Bolder",
                                    "size": "Medium",
                                },
                                {
                                    "type": "TextBlock",
                                    "text": self.message,
                                    "wrap": True,
                                },
                            ],
                        },
                    ],
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "version": "1.4",
                },
            }],
        }

        # Add facts if present
        if facts:
            message["attachments"][0]["content"]["body"].append({
                "type": "FactSet",
                "facts": facts,
            })

        # Add tags
        if self.tags:
            message["attachments"][0]["content"]["body"].append({
                "type": "TextBlock",
                "text": f"**Tags:** {', '.join(self.tags)}",
                "wrap": True,
                "size": "Small",
            })

        return message


class NotificationManager:
    """Manages sending notifications across multiple channels."""

    def __init__(self):
        """Initialize notification manager."""
        self.channels: Dict[NotificationChannel, Any] = {}
        self.sent_notifications: List[Notification] = []

    def register_channel(
        self,
        channel: NotificationChannel,
        client: Any,
    ):
        """Register a notification channel.

        Args:
            channel: Channel type
            client: Client instance for the channel
        """
        self.channels[channel] = client
        logger.info(
            f"Registered notification channel: {channel}",
            channel=channel,
        )

    async def send(
        self,
        notification: Notification,
        channels: Optional[List[NotificationChannel]] = None,
    ) -> Dict[NotificationChannel, bool]:
        """Send notification to specified channels.

        Args:
            notification: Notification to send
            channels: Channels to send to (defaults to notification.channels)

        Returns:
            Dictionary mapping channels to success status
        """
        target_channels = channels or notification.channels
        results = {}

        if not target_channels:
            logger.warning("No channels specified for notification")
            return results

        for channel in target_channels:
            if channel not in self.channels:
                logger.warning(
                    f"Channel {channel} not registered",
                    channel=channel,
                )
                results[channel] = False
                continue

            try:
                client = self.channels[channel]

                if channel == NotificationChannel.SLACK:
                    await client.send_message(notification.to_slack_format())
                elif channel == NotificationChannel.TEAMS:
                    await client.send_message(notification.to_teams_format())
                elif channel == NotificationChannel.CONSOLE:
                    self._print_to_console(notification)
                else:
                    logger.warning(f"Unsupported channel: {channel}")
                    results[channel] = False
                    continue

                results[channel] = True
                logger.info(
                    f"Notification sent via {channel}",
                    channel=channel,
                    title=notification.title,
                    level=notification.level,
                )

            except Exception as e:
                logger.error(
                    f"Failed to send notification via {channel}: {e}",
                    channel=channel,
                    error=str(e),
                )
                results[channel] = False

        # Record sent notification
        self.sent_notifications.append(notification)

        return results

    def _print_to_console(self, notification: Notification):
        """Print notification to console."""
        icon_map = {
            NotificationLevel.INFO: "ℹ️",
            NotificationLevel.SUCCESS: "✅",
            NotificationLevel.WARNING: "⚠️ ",
            NotificationLevel.ERROR: "❌",
            NotificationLevel.CRITICAL: "🚨",
        }

        icon = icon_map.get(notification.level, "")
        print(f"\n{icon} [{notification.level.upper()}] {notification.title}")
        print(f"   {notification.message}")

        if notification.metadata:
            print("   Metadata:")
            for key, value in notification.metadata.items():
                print(f"     • {key}: {value}")

        if notification.tags:
            print(f"   Tags: {', '.join(notification.tags)}")

    async def send_alert(
        self,
        title: str,
        message: str,
        level: NotificationLevel = NotificationLevel.WARNING,
        channels: Optional[List[NotificationChannel]] = None,
        **metadata,
    ) -> Dict[NotificationChannel, bool]:
        """Convenience method to send an alert.

        Args:
            title: Alert title
            message: Alert message
            level: Alert level
            channels: Channels to send to
            **metadata: Additional metadata

        Returns:
            Dictionary mapping channels to success status
        """
        notification = Notification(
            title=title,
            message=message,
            level=level,
            channels=channels or list(self.channels.keys()),
            metadata=metadata,
        )

        return await self.send(notification)

    def get_recent_notifications(
        self,
        limit: int = 10,
        level: Optional[NotificationLevel] = None,
    ) -> List[Notification]:
        """Get recent notifications.

        Args:
            limit: Maximum number of notifications to return
            level: Filter by notification level

        Returns:
            List of recent notifications
        """
        notifications = self.sent_notifications

        if level:
            notifications = [n for n in notifications if n.level == level]

        return notifications[-limit:]
