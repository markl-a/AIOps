"""Notification Routes"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from aiops.core.structured_logger import get_structured_logger


logger = get_structured_logger(__name__)
router = APIRouter()


# Request/Response Models
class SendNotificationRequest(BaseModel):
    """Request to send a notification."""

    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    level: str = Field(default="info", description="Notification level")
    channels: List[str] = Field(..., description="Channels to send to")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    tags: Optional[List[str]] = Field(default_factory=list)


class NotificationResponse(BaseModel):
    """Response from sending notification."""

    notification_id: str
    title: str
    level: str
    channels_sent: Dict[str, bool]
    sent_at: datetime


class NotificationHistoryItem(BaseModel):
    """Notification history item."""

    notification_id: str
    title: str
    message: str
    level: str
    channels: List[str]
    sent_at: datetime
    metadata: Dict[str, Any]


@router.post("/send", response_model=NotificationResponse)
async def send_notification(request: SendNotificationRequest):
    """Send a notification to specified channels."""
    logger.info(
        f"Sending notification: {request.title}",
        level=request.level,
        channels=request.channels,
    )

    import uuid

    notification_id = str(uuid.uuid4())

    # Mock implementation - replace with actual notification manager
    channels_sent = {}
    for channel in request.channels:
        try:
            # Simulate sending to channel
            import asyncio
            await asyncio.sleep(0.1)
            channels_sent[channel] = True
        except Exception as e:
            logger.error(f"Failed to send to {channel}: {e}")
            channels_sent[channel] = False

    return NotificationResponse(
        notification_id=notification_id,
        title=request.title,
        level=request.level,
        channels_sent=channels_sent,
        sent_at=datetime.now(),
    )


@router.get("/history", response_model=List[NotificationHistoryItem])
async def get_notification_history(
    level: Optional[str] = None,
    limit: int = 100,
):
    """Get notification history."""
    # Mock implementation
    notifications = [
        {
            "notification_id": "notif-1",
            "title": "Deployment Successful",
            "message": "Application deployed to production",
            "level": "success",
            "channels": ["slack", "teams"],
            "sent_at": datetime.now(),
            "metadata": {"environment": "production"},
        },
        {
            "notification_id": "notif-2",
            "title": "High CPU Usage",
            "message": "CPU usage exceeded 80%",
            "level": "warning",
            "channels": ["slack"],
            "sent_at": datetime.now(),
            "metadata": {"server": "prod-01"},
        },
    ]

    if level:
        notifications = [n for n in notifications if n["level"] == level]

    return [
        NotificationHistoryItem(**n)
        for n in notifications[:limit]
    ]


@router.get("/channels")
async def list_channels():
    """List available notification channels."""
    return {
        "channels": [
            {
                "name": "slack",
                "enabled": True,
                "configured": True,
                "description": "Slack webhook notifications",
            },
            {
                "name": "teams",
                "enabled": True,
                "configured": True,
                "description": "Microsoft Teams notifications",
            },
            {
                "name": "email",
                "enabled": False,
                "configured": False,
                "description": "Email notifications",
            },
        ]
    }


@router.post("/test/{channel}")
async def test_channel(channel: str):
    """Send a test notification to a channel."""
    logger.info(f"Sending test notification to {channel}")

    # Mock implementation
    return {
        "channel": channel,
        "status": "success",
        "message": f"Test notification sent to {channel}",
        "sent_at": datetime.now(),
    }
