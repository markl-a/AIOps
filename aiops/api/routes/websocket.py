"""WebSocket Routes for Real-Time Notifications

Provides WebSocket endpoints for real-time communication:
- Agent execution status updates
- System health notifications
- Alert broadcasting
- Connection authentication using JWT
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional, Set, List
from enum import Enum
from dataclasses import dataclass, field
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from pydantic import BaseModel, Field
import jwt
from jwt.exceptions import PyJWTError

from aiops.core.structured_logger import get_structured_logger
from aiops.api.auth import get_secret_key, ALGORITHM, UserRole


logger = get_structured_logger(__name__)
router = APIRouter()


class NotificationType(str, Enum):
    """Types of WebSocket notifications."""
    AGENT_STATUS = "agent_status"
    SYSTEM_HEALTH = "system_health"
    ALERT = "alert"
    WORKFLOW_STATUS = "workflow_status"
    HEARTBEAT = "heartbeat"
    CONNECTION = "connection"
    ERROR = "error"


class NotificationLevel(str, Enum):
    """Notification severity levels."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class WebSocketConnection:
    """Represents an active WebSocket connection."""
    connection_id: str
    websocket: WebSocket
    user_id: str
    role: UserRole
    connected_at: datetime
    subscriptions: Set[str] = field(default_factory=set)
    last_ping: Optional[datetime] = None
    last_pong: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class WebSocketMessage(BaseModel):
    """WebSocket message format."""
    type: NotificationType
    level: NotificationLevel = NotificationLevel.INFO
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    class Config:
        use_enum_values = True


class ConnectionManager:
    """
    Manages WebSocket connections for real-time notifications.

    Features:
    - Connection tracking with authentication
    - Subscription-based message routing
    - Heartbeat monitoring
    - Broadcast capabilities
    - Proper cleanup on disconnect
    """

    def __init__(self):
        # Active connections by connection_id
        self._connections: Dict[str, WebSocketConnection] = {}
        # Connections grouped by user_id for targeted messages
        self._user_connections: Dict[str, Set[str]] = {}
        # Connections by subscription topic
        self._subscriptions: Dict[str, Set[str]] = {}
        # Background tasks
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False
        # Configuration
        self.heartbeat_interval = 30  # seconds
        self.heartbeat_timeout = 60  # seconds
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    @property
    def connection_count(self) -> int:
        """Get current number of active connections."""
        return len(self._connections)

    @property
    def user_count(self) -> int:
        """Get number of unique connected users."""
        return len(self._user_connections)

    async def start(self):
        """Start the connection manager background tasks."""
        if not self._running:
            self._running = True
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            logger.info("WebSocket connection manager started")

    async def stop(self):
        """Stop the connection manager and cleanup."""
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        # Close all connections
        for conn_id in list(self._connections.keys()):
            await self.disconnect(conn_id)

        logger.info("WebSocket connection manager stopped")

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        role: UserRole,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Register a new WebSocket connection.

        Args:
            websocket: The WebSocket connection
            user_id: Authenticated user identifier
            role: User's role for authorization
            metadata: Optional connection metadata

        Returns:
            Connection ID for the new connection
        """
        connection_id = str(uuid.uuid4())

        async with self._lock:
            connection = WebSocketConnection(
                connection_id=connection_id,
                websocket=websocket,
                user_id=user_id,
                role=role,
                connected_at=datetime.utcnow(),
                metadata=metadata or {},
            )

            self._connections[connection_id] = connection

            # Track by user
            if user_id not in self._user_connections:
                self._user_connections[user_id] = set()
            self._user_connections[user_id].add(connection_id)

            # Auto-subscribe to default topics based on role
            default_subscriptions = ["alerts", "system_health"]
            if role in [UserRole.ADMIN, UserRole.USER]:
                default_subscriptions.append("agent_status")
            if role == UserRole.ADMIN:
                default_subscriptions.append("admin_notifications")

            for topic in default_subscriptions:
                await self._subscribe_internal(connection_id, topic)

        logger.info(
            f"WebSocket connected",
            connection_id=connection_id,
            user_id=user_id,
            role=role.value,
        )

        # Send connection confirmation
        await self.send_personal(
            connection_id,
            WebSocketMessage(
                type=NotificationType.CONNECTION,
                level=NotificationLevel.SUCCESS,
                payload={
                    "status": "connected",
                    "connection_id": connection_id,
                    "subscriptions": list(connection.subscriptions),
                },
            ),
        )

        return connection_id

    async def disconnect(self, connection_id: str):
        """
        Remove a WebSocket connection and cleanup.

        Args:
            connection_id: The connection to remove
        """
        async with self._lock:
            if connection_id not in self._connections:
                return

            connection = self._connections[connection_id]

            # Remove from user tracking
            if connection.user_id in self._user_connections:
                self._user_connections[connection.user_id].discard(connection_id)
                if not self._user_connections[connection.user_id]:
                    del self._user_connections[connection.user_id]

            # Remove from all subscriptions
            for topic in list(connection.subscriptions):
                if topic in self._subscriptions:
                    self._subscriptions[topic].discard(connection_id)
                    if not self._subscriptions[topic]:
                        del self._subscriptions[topic]

            # Close websocket if still open
            try:
                await connection.websocket.close()
            except Exception:
                pass

            del self._connections[connection_id]

        logger.info(
            f"WebSocket disconnected",
            connection_id=connection_id,
            user_id=connection.user_id,
        )

    async def _subscribe_internal(self, connection_id: str, topic: str):
        """Internal method to subscribe to a topic (must be called with lock held)."""
        if connection_id in self._connections:
            self._connections[connection_id].subscriptions.add(topic)
            if topic not in self._subscriptions:
                self._subscriptions[topic] = set()
            self._subscriptions[topic].add(connection_id)

    async def subscribe(self, connection_id: str, topic: str):
        """
        Subscribe a connection to a topic.

        Args:
            connection_id: The connection ID
            topic: Topic to subscribe to
        """
        async with self._lock:
            await self._subscribe_internal(connection_id, topic)

        logger.debug(
            f"Connection subscribed to topic",
            connection_id=connection_id,
            topic=topic,
        )

    async def unsubscribe(self, connection_id: str, topic: str):
        """
        Unsubscribe a connection from a topic.

        Args:
            connection_id: The connection ID
            topic: Topic to unsubscribe from
        """
        async with self._lock:
            if connection_id in self._connections:
                self._connections[connection_id].subscriptions.discard(topic)
            if topic in self._subscriptions:
                self._subscriptions[topic].discard(connection_id)
                if not self._subscriptions[topic]:
                    del self._subscriptions[topic]

        logger.debug(
            f"Connection unsubscribed from topic",
            connection_id=connection_id,
            topic=topic,
        )

    async def send_personal(self, connection_id: str, message: WebSocketMessage):
        """
        Send a message to a specific connection.

        Args:
            connection_id: Target connection ID
            message: Message to send
        """
        if connection_id not in self._connections:
            logger.warning(f"Cannot send to unknown connection: {connection_id}")
            return

        connection = self._connections[connection_id]
        try:
            await connection.websocket.send_json(message.model_dump(mode="json"))
        except Exception as e:
            logger.error(f"Failed to send message to {connection_id}: {e}")
            await self.disconnect(connection_id)

    async def send_to_user(self, user_id: str, message: WebSocketMessage):
        """
        Send a message to all connections of a specific user.

        Args:
            user_id: Target user ID
            message: Message to send
        """
        connection_ids = self._user_connections.get(user_id, set()).copy()
        for connection_id in connection_ids:
            await self.send_personal(connection_id, message)

    async def broadcast(self, message: WebSocketMessage, topic: Optional[str] = None):
        """
        Broadcast a message to all connections or specific topic subscribers.

        Args:
            message: Message to broadcast
            topic: Optional topic to filter recipients
        """
        if topic:
            connection_ids = self._subscriptions.get(topic, set()).copy()
        else:
            connection_ids = set(self._connections.keys())

        # Send to all relevant connections
        tasks = [
            self.send_personal(conn_id, message)
            for conn_id in connection_ids
        ]

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        logger.debug(
            f"Broadcast message sent",
            topic=topic,
            recipients=len(connection_ids),
            message_type=message.type,
        )

    async def _heartbeat_loop(self):
        """Background task for sending heartbeats and checking connection health."""
        while self._running:
            try:
                await asyncio.sleep(self.heartbeat_interval)

                current_time = datetime.utcnow()
                stale_connections = []

                # Check all connections
                for conn_id, connection in list(self._connections.items()):
                    try:
                        # Send ping
                        ping_message = WebSocketMessage(
                            type=NotificationType.HEARTBEAT,
                            payload={"ping": True, "server_time": current_time.isoformat()},
                        )
                        await connection.websocket.send_json(ping_message.model_dump(mode="json"))
                        connection.last_ping = current_time

                        # Check for stale connections (no pong received)
                        if connection.last_pong:
                            time_since_pong = (current_time - connection.last_pong).total_seconds()
                            if time_since_pong > self.heartbeat_timeout:
                                stale_connections.append(conn_id)

                    except Exception as e:
                        logger.warning(f"Heartbeat failed for {conn_id}: {e}")
                        stale_connections.append(conn_id)

                # Cleanup stale connections
                for conn_id in stale_connections:
                    logger.info(f"Removing stale connection: {conn_id}")
                    await self.disconnect(conn_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")

    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific connection."""
        if connection_id not in self._connections:
            return None

        conn = self._connections[connection_id]
        return {
            "connection_id": conn.connection_id,
            "user_id": conn.user_id,
            "role": conn.role.value,
            "connected_at": conn.connected_at.isoformat(),
            "subscriptions": list(conn.subscriptions),
            "last_ping": conn.last_ping.isoformat() if conn.last_ping else None,
            "last_pong": conn.last_pong.isoformat() if conn.last_pong else None,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get connection manager statistics."""
        return {
            "total_connections": self.connection_count,
            "unique_users": self.user_count,
            "subscriptions": {
                topic: len(connections)
                for topic, connections in self._subscriptions.items()
            },
            "running": self._running,
        }


# Global connection manager instance
connection_manager = ConnectionManager()


class NotificationManager:
    """
    High-level notification manager for broadcasting events.

    Provides convenient methods for sending different types of notifications
    through the WebSocket connection manager.
    """

    def __init__(self, conn_manager: ConnectionManager):
        self._connection_manager = conn_manager

    async def notify_agent_status(
        self,
        execution_id: str,
        agent_type: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        """
        Send agent execution status update.

        Args:
            execution_id: Unique execution identifier
            agent_type: Type of agent being executed
            status: Current status (running, completed, failed, timeout)
            result: Execution result if completed
            error: Error message if failed
            user_id: Optional specific user to notify
        """
        level = NotificationLevel.INFO
        if status == "completed":
            level = NotificationLevel.SUCCESS
        elif status in ["failed", "timeout"]:
            level = NotificationLevel.ERROR

        message = WebSocketMessage(
            type=NotificationType.AGENT_STATUS,
            level=level,
            payload={
                "execution_id": execution_id,
                "agent_type": agent_type,
                "status": status,
                "result": result,
                "error": error,
            },
        )

        if user_id:
            await self._connection_manager.send_to_user(user_id, message)
        else:
            await self._connection_manager.broadcast(message, topic="agent_status")

    async def notify_workflow_status(
        self,
        workflow_id: str,
        status: str,
        progress: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ):
        """
        Send workflow execution status update.

        Args:
            workflow_id: Unique workflow identifier
            status: Current workflow status
            progress: Progress information (tasks completed, etc.)
            user_id: Optional specific user to notify
        """
        level = NotificationLevel.INFO
        if status == "completed":
            level = NotificationLevel.SUCCESS
        elif status in ["failed", "cancelled"]:
            level = NotificationLevel.ERROR

        message = WebSocketMessage(
            type=NotificationType.WORKFLOW_STATUS,
            level=level,
            payload={
                "workflow_id": workflow_id,
                "status": status,
                "progress": progress,
            },
        )

        if user_id:
            await self._connection_manager.send_to_user(user_id, message)
        else:
            await self._connection_manager.broadcast(message, topic="agent_status")

    async def notify_system_health(
        self,
        status: str,
        services: Dict[str, Any],
        system_metrics: Optional[Dict[str, Any]] = None,
    ):
        """
        Broadcast system health status update.

        Args:
            status: Overall health status
            services: Individual service health statuses
            system_metrics: Optional system resource metrics
        """
        level = NotificationLevel.INFO
        if status == "degraded":
            level = NotificationLevel.WARNING
        elif status == "unhealthy":
            level = NotificationLevel.ERROR

        message = WebSocketMessage(
            type=NotificationType.SYSTEM_HEALTH,
            level=level,
            payload={
                "status": status,
                "services": services,
                "system": system_metrics,
            },
        )

        await self._connection_manager.broadcast(message, topic="system_health")

    async def send_alert(
        self,
        title: str,
        message_text: str,
        level: NotificationLevel = NotificationLevel.WARNING,
        metadata: Optional[Dict[str, Any]] = None,
        target_users: Optional[List[str]] = None,
        target_roles: Optional[List[UserRole]] = None,
    ):
        """
        Send an alert notification.

        Args:
            title: Alert title
            message_text: Alert message body
            level: Alert severity level
            metadata: Additional alert metadata
            target_users: Optional list of specific users to notify
            target_roles: Optional list of roles to notify
        """
        message = WebSocketMessage(
            type=NotificationType.ALERT,
            level=level,
            payload={
                "title": title,
                "message": message_text,
                "metadata": metadata or {},
            },
        )

        if target_users:
            for user_id in target_users:
                await self._connection_manager.send_to_user(user_id, message)
        else:
            await self._connection_manager.broadcast(message, topic="alerts")


# Global notification manager instance
notification_manager = NotificationManager(connection_manager)


def verify_websocket_token(token: str) -> Dict[str, Any]:
    """
    Verify a JWT token for WebSocket authentication.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload with user info

    Raises:
        ValueError: If token is invalid
    """
    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=[ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role", UserRole.USER.value)

        if not username:
            raise ValueError("Token missing required claims")

        return {
            "user_id": username,
            "role": UserRole(role),
        }
    except PyJWTError as e:
        logger.warning(f"WebSocket token verification failed: {e}")
        raise ValueError(f"Invalid token: {e}")


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="JWT authentication token"),
):
    """
    Main WebSocket endpoint for real-time notifications.

    Authentication:
        Pass JWT token as query parameter: /ws?token=<jwt_token>

    Message Types:
        - agent_status: Agent execution updates
        - system_health: System health changes
        - alert: Alert notifications
        - workflow_status: Workflow progress updates
        - heartbeat: Connection health checks

    Client Commands:
        - {"action": "subscribe", "topic": "<topic_name>"}
        - {"action": "unsubscribe", "topic": "<topic_name>"}
        - {"action": "pong"} - Response to heartbeat ping
    """
    # Verify authentication
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        user_info = verify_websocket_token(token)
    except ValueError as e:
        logger.warning(f"WebSocket authentication failed: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Accept the connection
    await websocket.accept()

    # Register with connection manager
    connection_id = await connection_manager.connect(
        websocket=websocket,
        user_id=user_info["user_id"],
        role=user_info["role"],
    )

    try:
        # Start heartbeat if not already running
        if not connection_manager._running:
            await connection_manager.start()

        # Message handling loop
        while True:
            try:
                data = await websocket.receive_json()
                await handle_client_message(connection_id, data)
            except json.JSONDecodeError:
                await connection_manager.send_personal(
                    connection_id,
                    WebSocketMessage(
                        type=NotificationType.ERROR,
                        level=NotificationLevel.ERROR,
                        payload={"error": "Invalid JSON message"},
                    ),
                )
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {connection_id}: {e}")
    finally:
        await connection_manager.disconnect(connection_id)


async def handle_client_message(connection_id: str, data: Dict[str, Any]):
    """
    Handle incoming client messages.

    Args:
        connection_id: The sender's connection ID
        data: Parsed JSON message data
    """
    action = data.get("action")

    if action == "subscribe":
        topic = data.get("topic")
        if topic:
            await connection_manager.subscribe(connection_id, topic)
            await connection_manager.send_personal(
                connection_id,
                WebSocketMessage(
                    type=NotificationType.CONNECTION,
                    level=NotificationLevel.SUCCESS,
                    payload={"subscribed": topic},
                ),
            )

    elif action == "unsubscribe":
        topic = data.get("topic")
        if topic:
            await connection_manager.unsubscribe(connection_id, topic)
            await connection_manager.send_personal(
                connection_id,
                WebSocketMessage(
                    type=NotificationType.CONNECTION,
                    level=NotificationLevel.SUCCESS,
                    payload={"unsubscribed": topic},
                ),
            )

    elif action == "pong":
        # Update last pong time for heartbeat tracking
        if connection_id in connection_manager._connections:
            connection_manager._connections[connection_id].last_pong = datetime.utcnow()

    elif action == "ping":
        # Client-initiated ping
        await connection_manager.send_personal(
            connection_id,
            WebSocketMessage(
                type=NotificationType.HEARTBEAT,
                payload={"pong": True, "server_time": datetime.utcnow().isoformat()},
            ),
        )

    else:
        logger.debug(f"Unknown action from {connection_id}: {action}")


@router.get("/ws/stats")
async def websocket_stats():
    """Get WebSocket connection statistics."""
    return connection_manager.get_stats()


@router.get("/ws/connections")
async def list_connections():
    """
    List all active WebSocket connections.

    Note: This endpoint is for debugging/admin purposes.
    """
    connections = []
    for conn_id in connection_manager._connections:
        info = connection_manager.get_connection_info(conn_id)
        if info:
            connections.append(info)

    return {
        "connections": connections,
        "total": len(connections),
    }
