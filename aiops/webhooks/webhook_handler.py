"""Base webhook handler class."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable
import hmac
import hashlib
from pydantic import BaseModel, Field
from datetime import datetime
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class WebhookEvent(BaseModel):
    """Webhook event data"""
    event_id: str = Field(description="Unique event identifier")
    source: str = Field(description="Event source (github, gitlab, etc.)")
    event_type: str = Field(description="Event type (push, pr, issue, etc.)")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    payload: Dict[str, Any] = Field(description="Raw event payload")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class WebhookHandler(ABC):
    """
    Base class for webhook handlers.

    Provides common functionality for webhook verification, parsing, and processing.
    """

    def __init__(self, secret: Optional[str] = None):
        """
        Initialize webhook handler.

        Args:
            secret: Secret key for webhook signature verification
        """
        self.secret = secret
        self.event_handlers: Dict[str, Callable] = {}

    @abstractmethod
    def get_source_name(self) -> str:
        """Get the source name for this handler (e.g., 'github', 'gitlab')"""
        pass

    @abstractmethod
    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify webhook signature.

        Args:
            payload: Raw webhook payload
            signature: Signature from webhook headers

        Returns:
            True if signature is valid
        """
        pass

    @abstractmethod
    def parse_event(self, headers: Dict[str, str], payload: Dict[str, Any]) -> WebhookEvent:
        """
        Parse webhook payload into standardized event.

        Args:
            headers: HTTP headers
            payload: Webhook payload

        Returns:
            Parsed WebhookEvent
        """
        pass

    def register_handler(self, event_type: str, handler: Callable):
        """
        Register a handler for a specific event type.

        Args:
            event_type: Event type to handle
            handler: Async function to handle the event
        """
        self.event_handlers[event_type] = handler
        logger.info(f"Registered handler for {self.get_source_name()}:{event_type}")

    async def handle_event(self, event: WebhookEvent) -> Dict[str, Any]:
        """
        Route event to appropriate handler.

        Args:
            event: Parsed webhook event

        Returns:
            Handler result
        """
        event_type = event.event_type

        if event_type not in self.event_handlers:
            logger.warning(
                f"No handler registered for {self.get_source_name()}:{event_type}"
            )
            return {
                "status": "ignored",
                "reason": f"No handler for {event_type}",
            }

        logger.info(f"Handling {self.get_source_name()}:{event_type} event {event.event_id}")

        try:
            handler = self.event_handlers[event_type]
            result = await handler(event)

            logger.info(f"Successfully handled event {event.event_id}")
            return {
                "status": "success",
                "event_id": event.event_id,
                "result": result,
            }

        except Exception as e:
            logger.error(f"Error handling event {event.event_id}: {e}", exc_info=True)
            return {
                "status": "error",
                "event_id": event.event_id,
                "error": str(e),
            }

    def _verify_hmac_signature(
        self,
        payload: bytes,
        signature: str,
        algorithm: str = "sha256",
        prefix: str = "",
    ) -> bool:
        """
        Verify HMAC signature.

        Args:
            payload: Raw payload bytes
            signature: Signature to verify
            algorithm: Hash algorithm (sha1, sha256)
            prefix: Signature prefix (e.g., 'sha256=')

        Returns:
            True if signature is valid
        """
        if not self.secret:
            logger.warning("No secret configured for signature verification")
            return True  # Skip verification if no secret

        # Compute expected signature
        if algorithm == "sha1":
            mac = hmac.new(self.secret.encode(), payload, hashlib.sha1)
        elif algorithm == "sha256":
            mac = hmac.new(self.secret.encode(), payload, hashlib.sha256)
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

        expected_sig = f"{prefix}{mac.hexdigest()}"

        # Compare signatures (constant-time comparison)
        return hmac.compare_digest(expected_sig, signature)


class WebhookProcessor:
    """
    Process webhooks and trigger automated workflows.
    """

    def __init__(self):
        """Initialize webhook processor"""
        self.handlers: Dict[str, WebhookHandler] = {}
        self.workflows: Dict[str, Callable] = {}

    def register_handler(self, handler: WebhookHandler):
        """
        Register a webhook handler.

        Args:
            handler: WebhookHandler instance
        """
        source = handler.get_source_name()
        self.handlers[source] = handler
        logger.info(f"Registered webhook handler for {source}")

    def register_workflow(self, name: str, workflow: Callable):
        """
        Register an automated workflow.

        Args:
            name: Workflow name
            workflow: Async function that executes the workflow
        """
        self.workflows[name] = workflow
        logger.info(f"Registered workflow: {name}")

    async def process_webhook(
        self,
        source: str,
        headers: Dict[str, str],
        payload: bytes,
        signature: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process incoming webhook.

        Args:
            source: Webhook source (github, gitlab, etc.)
            headers: HTTP headers
            payload: Raw webhook payload
            signature: Webhook signature for verification

        Returns:
            Processing result
        """
        # Get handler
        if source not in self.handlers:
            logger.error(f"No handler registered for source: {source}")
            return {
                "status": "error",
                "error": f"Unknown source: {source}",
            }

        handler = self.handlers[source]

        # Verify signature
        if signature and not handler.verify_signature(payload, signature):
            logger.error(f"Invalid webhook signature for {source}")
            return {
                "status": "error",
                "error": "Invalid signature",
            }

        # Parse payload
        try:
            import json
            payload_dict = json.loads(payload.decode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to parse webhook payload: {e}")
            return {
                "status": "error",
                "error": f"Invalid payload: {e}",
            }

        # Parse event
        try:
            event = handler.parse_event(headers, payload_dict)
        except Exception as e:
            logger.error(f"Failed to parse webhook event: {e}")
            return {
                "status": "error",
                "error": f"Failed to parse event: {e}",
            }

        # Handle event
        result = await handler.handle_event(event)

        return result
