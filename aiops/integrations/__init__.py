"""Third-party Integrations Module

This module provides integrations with popular collaboration and communication
platforms like Slack, Microsoft Teams, and more.
"""

from aiops.integrations.slack import SlackNotifier, SlackClient
from aiops.integrations.teams import TeamsNotifier
from aiops.integrations.notifications import (
    NotificationManager,
    Notification,
    NotificationLevel,
    NotificationChannel,
)

__all__ = [
    "SlackNotifier",
    "SlackClient",
    "TeamsNotifier",
    "NotificationManager",
    "Notification",
    "NotificationLevel",
    "NotificationChannel",
]
