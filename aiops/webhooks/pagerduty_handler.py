"""PagerDuty webhook handler."""

from typing import Dict, Any
from aiops.webhooks.webhook_handler import WebhookHandler, WebhookEvent
from aiops.core.logger import get_logger
import uuid

logger = get_logger(__name__)


class PagerDutyWebhookHandler(WebhookHandler):
    """
    Handle PagerDuty webhooks.

    Supported events:
    - incident.triggered
    - incident.acknowledged
    - incident.resolved
    - incident.escalated
    - incident.assigned
    - incident.annotated
    """

    def get_source_name(self) -> str:
        return "pagerduty"

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify PagerDuty webhook signature.

        PagerDuty uses HMAC SHA256 for webhook verification.
        Signature format: v1=<hexdigest>
        """
        if not signature or not self.secret:
            return True

        return self._verify_hmac_signature(
            payload=payload,
            signature=signature,
            algorithm="sha256",
            prefix="v1=",
        )

    def parse_event(self, headers: Dict[str, str], payload: Dict[str, Any]) -> WebhookEvent:
        """Parse PagerDuty webhook event"""
        # PagerDuty sends array of messages
        messages = payload.get("messages", [])

        if not messages:
            logger.warning("PagerDuty webhook with no messages")
            return WebhookEvent(
                event_id=str(uuid.uuid4()),
                source=self.get_source_name(),
                event_type="unknown",
                payload=payload,
                metadata={},
            )

        # Process first message (usually only one)
        message = messages[0]
        event_type = message.get("event", "unknown")
        event_id = message.get("id", str(uuid.uuid4()))

        # Extract metadata
        metadata = self._extract_metadata(message)

        return WebhookEvent(
            event_id=event_id,
            source=self.get_source_name(),
            event_type=event_type,
            payload=payload,
            metadata=metadata,
        )

    def _extract_metadata(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Extract useful metadata from message"""
        metadata: Dict[str, Any] = {}

        # Incident data
        if "incident" in message:
            incident = message["incident"]

            metadata["incident_id"] = incident.get("id")
            metadata["incident_number"] = incident.get("incident_number")
            metadata["incident_key"] = incident.get("incident_key")
            metadata["title"] = incident.get("title")
            metadata["description"] = incident.get("description")
            metadata["status"] = incident.get("status")
            metadata["urgency"] = incident.get("urgency")
            metadata["priority"] = incident.get("priority", {}).get("summary")

            # Service info
            if "service" in incident:
                service = incident["service"]
                metadata["service"] = {
                    "id": service.get("id"),
                    "name": service.get("summary"),
                }

            # Assignees
            if "assignments" in incident:
                metadata["assignees"] = [
                    a.get("assignee", {}).get("summary")
                    for a in incident["assignments"]
                ]

            # Timestamps
            metadata["created_at"] = incident.get("created_at")
            metadata["updated_at"] = incident.get("updated_at")

            # Escalation info
            if "escalation_policy" in incident:
                policy = incident["escalation_policy"]
                metadata["escalation_policy"] = policy.get("summary")

        return metadata


# Default event handlers
async def handle_incident_triggered(event: WebhookEvent) -> Dict[str, Any]:
    """Handle incident triggered event"""
    incident_id = event.metadata.get("incident_number")
    title = event.metadata.get("title")
    urgency = event.metadata.get("urgency")
    service = event.metadata.get("service", {}).get("name")

    logger.info(
        f"PagerDuty incident #{incident_id} triggered: {title} "
        f"({urgency} urgency, service: {service})"
    )

    # For high urgency incidents, could trigger automated incident response
    if urgency == "high":
        logger.warning(f"High urgency incident: #{incident_id}")
        return {
            "action": "incident_response_triggered",
            "incident_id": incident_id,
            "urgency": urgency,
        }

    return {
        "action": "incident_triggered",
        "incident_id": incident_id,
    }


async def handle_incident_acknowledged(event: WebhookEvent) -> Dict[str, Any]:
    """Handle incident acknowledged event"""
    incident_id = event.metadata.get("incident_number")
    assignees = event.metadata.get("assignees", [])

    logger.info(f"PagerDuty incident #{incident_id} acknowledged by {', '.join(assignees)}")

    return {
        "action": "incident_acknowledged",
        "incident_id": incident_id,
        "assignees": assignees,
    }


async def handle_incident_resolved(event: WebhookEvent) -> Dict[str, Any]:
    """Handle incident resolved event"""
    incident_id = event.metadata.get("incident_number")
    title = event.metadata.get("title")

    logger.info(f"PagerDuty incident #{incident_id} resolved: {title}")

    # Could trigger postmortem generation
    return {
        "action": "incident_resolved",
        "incident_id": incident_id,
        "postmortem_recommended": True,
    }
