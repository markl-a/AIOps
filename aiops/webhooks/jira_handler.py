"""Jira webhook handler."""

from typing import Dict, Any
from aiops.webhooks.webhook_handler import WebhookHandler, WebhookEvent
from aiops.core.logger import get_logger
import uuid

logger = get_logger(__name__)


class JiraWebhookHandler(WebhookHandler):
    """
    Handle Jira webhooks.

    Supported events:
    - jira:issue_created
    - jira:issue_updated
    - jira:issue_deleted
    - comment_created
    - comment_updated
    - sprint_started
    - sprint_closed
    """

    def get_source_name(self) -> str:
        return "jira"

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify Jira webhook signature.

        Jira can use HMAC SHA256 for verification.
        """
        if not signature or not self.secret:
            return True

        return self._verify_hmac_signature(
            payload=payload,
            signature=signature,
            algorithm="sha256",
        )

    def parse_event(self, headers: Dict[str, str], payload: Dict[str, Any]) -> WebhookEvent:
        """Parse Jira webhook event"""
        # Jira webhook event type
        event_type = payload.get("webhookEvent", "unknown")
        event_id = str(uuid.uuid4())

        # Extract metadata
        metadata = self._extract_metadata(event_type, payload)

        return WebhookEvent(
            event_id=event_id,
            source=self.get_source_name(),
            event_type=event_type,
            payload=payload,
            metadata=metadata,
        )

    def _extract_metadata(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract useful metadata from payload"""
        metadata: Dict[str, Any] = {}

        # User info
        if "user" in payload:
            user = payload["user"]
            metadata["user"] = {
                "name": user.get("displayName"),
                "email": user.get("emailAddress"),
            }

        # Issue events
        if "issue" in payload:
            issue = payload["issue"]
            fields = issue.get("fields", {})

            metadata["issue_key"] = issue.get("key")
            metadata["issue_type"] = fields.get("issuetype", {}).get("name")
            metadata["issue_status"] = fields.get("status", {}).get("name")
            metadata["issue_priority"] = fields.get("priority", {}).get("name")
            metadata["issue_summary"] = fields.get("summary")
            metadata["project_key"] = fields.get("project", {}).get("key")

            # For updated issues, include changelog
            if "changelog" in payload:
                metadata["changes"] = []
                for item in payload["changelog"].get("items", []):
                    metadata["changes"].append({
                        "field": item.get("field"),
                        "from": item.get("fromString"),
                        "to": item.get("toString"),
                    })

        # Comment events
        if "comment" in payload:
            comment = payload["comment"]
            metadata["comment_id"] = comment.get("id")
            metadata["comment_body"] = comment.get("body")

        # Sprint events
        if "sprint" in payload:
            sprint = payload["sprint"]
            metadata["sprint_id"] = sprint.get("id")
            metadata["sprint_name"] = sprint.get("name")
            metadata["sprint_state"] = sprint.get("state")

        return metadata


# Default event handlers
async def handle_issue_created(event: WebhookEvent) -> Dict[str, Any]:
    """Handle Jira issue created event"""
    issue_key = event.metadata.get("issue_key")
    issue_type = event.metadata.get("issue_type")
    priority = event.metadata.get("issue_priority")

    logger.info(f"Jira issue created: {issue_key} ({issue_type}, {priority})")

    # Could trigger automated workflows based on issue type/priority
    if issue_type == "Bug" and priority in ["Critical", "Blocker"]:
        logger.info(f"Critical bug detected: {issue_key}")
        return {
            "action": "critical_bug_detected",
            "issue_key": issue_key,
        }

    return {
        "action": "issue_created",
        "issue_key": issue_key,
    }


async def handle_issue_updated(event: WebhookEvent) -> Dict[str, Any]:
    """Handle Jira issue updated event"""
    issue_key = event.metadata.get("issue_key")
    changes = event.metadata.get("changes", [])

    logger.info(f"Jira issue updated: {issue_key} ({len(changes)} changes)")

    # Check for status transitions
    status_changes = [c for c in changes if c["field"] == "status"]
    if status_changes:
        for change in status_changes:
            logger.info(f"{issue_key} status: {change['from']} → {change['to']}")

    return {
        "action": "issue_updated",
        "issue_key": issue_key,
        "changes_count": len(changes),
    }


async def handle_sprint_started(event: WebhookEvent) -> Dict[str, Any]:
    """Handle sprint started event"""
    sprint_name = event.metadata.get("sprint_name")
    logger.info(f"Sprint started: {sprint_name}")

    return {
        "action": "sprint_started",
        "sprint_name": sprint_name,
    }
