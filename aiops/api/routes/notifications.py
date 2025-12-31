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

    notification_id: str = Field(..., description="Unique identifier for this notification")
    title: str = Field(..., description="Notification title")
    level: str = Field(..., description="Notification level (info, warning, error, success)")
    channels_sent: Dict[str, bool] = Field(..., description="Status of notification delivery per channel")
    sent_at: datetime = Field(..., description="Timestamp when notification was sent")

    class Config:
        json_schema_extra = {
            "example": {
                "notification_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Deployment Successful",
                "level": "success",
                "channels_sent": {
                    "slack": True,
                    "teams": True,
                    "email": False
                },
                "sent_at": "2024-01-15T10:30:00Z"
            }
        }


class NotificationHistoryItem(BaseModel):
    """Notification history item."""

    notification_id: str = Field(..., description="Unique notification identifier")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Full notification message")
    level: str = Field(..., description="Notification level (info, warning, error, success)")
    channels: List[str] = Field(..., description="Channels where notification was sent")
    sent_at: datetime = Field(..., description="Timestamp when notification was sent")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional notification metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "notification_id": "notif-1",
                "title": "High CPU Usage",
                "message": "CPU usage exceeded 80% on prod-server-01",
                "level": "warning",
                "channels": ["slack", "pagerduty"],
                "sent_at": "2024-01-15T10:30:00Z",
                "metadata": {
                    "server": "prod-server-01",
                    "cpu_percent": 85.3
                }
            }
        }


@router.post("/send", response_model=NotificationResponse)
async def send_notification(request: SendNotificationRequest):
    """Send a notification to specified channels."""
    try:
        logger.info(
            f"Sending notification: {request.title}",
            level=request.level,
            channels=request.channels,
        )

        import uuid

        notification_id = str(uuid.uuid4())

        # Validate channels
        if not request.channels:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one channel must be specified"
            )

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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send notification: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send notification: {str(e)}"
        )


@router.get("/history", response_model=List[NotificationHistoryItem])
async def get_notification_history(
    level: Optional[str] = None,
    limit: int = 100,
):
    """Get notification history."""
    try:
        # Validate limit parameter
        if limit < 1 or limit > 1000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Limit must be between 1 and 1000"
            )

        # Validate level parameter if provided
        if level:
            valid_levels = ["info", "success", "warning", "error", "critical"]
            if level not in valid_levels:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid level. Must be one of: {', '.join(valid_levels)}"
                )

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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get notification history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve notification history: {str(e)}"
        )


@router.get("/channels")
async def list_channels():
    """List available notification channels."""
    try:
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
    except Exception as e:
        logger.error(f"Failed to list channels: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list notification channels: {str(e)}"
        )


@router.post("/test/{channel}")
async def test_channel(channel: str):
    """Send a test notification to a channel."""
    try:
        # Validate channel name
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', channel):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid channel name"
            )

        if len(channel) > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Channel name too long (max 50 characters)"
            )

        logger.info(f"Sending test notification to {channel}")

        # Mock implementation
        return {
            "channel": channel,
            "status": "success",
            "message": f"Test notification sent to {channel}",
            "sent_at": datetime.now(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test channel {channel}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test notification channel: {str(e)}"
        )
