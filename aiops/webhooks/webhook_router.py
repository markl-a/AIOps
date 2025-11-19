"""Webhook router for managing multiple webhook handlers and workflows."""

from typing import Dict, Any, Optional, Callable
from aiops.webhooks.webhook_handler import WebhookHandler, WebhookEvent
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class WebhookRouter:
    """
    Route webhooks to handlers and trigger automated workflows.

    This class manages webhook handlers for different sources and
    can trigger AI agent workflows based on webhook events.
    """

    def __init__(self):
        """Initialize webhook router"""
        self.handlers: Dict[str, WebhookHandler] = {}
        self.workflows: Dict[str, Callable] = {}
        self.event_mappings: Dict[str, str] = {}  # Map event types to workflows

    def register_handler(self, handler: WebhookHandler):
        """
        Register a webhook handler.

        Args:
            handler: WebhookHandler instance
        """
        source = handler.get_source_name()
        self.handlers[source] = handler
        logger.info(f"Registered webhook handler: {source}")

    def register_workflow(self, name: str, workflow: Callable):
        """
        Register an automated workflow.

        Args:
            name: Workflow name
            workflow: Async callable that executes the workflow
        """
        self.workflows[name] = workflow
        logger.info(f"Registered workflow: {name}")

    def map_event_to_workflow(self, source: str, event_type: str, workflow_name: str):
        """
        Map an event type to a workflow.

        Args:
            source: Event source (github, gitlab, etc.)
            event_type: Event type
            workflow_name: Workflow to trigger
        """
        key = f"{source}:{event_type}"
        self.event_mappings[key] = workflow_name
        logger.info(f"Mapped {key} → {workflow_name}")

    async def route_webhook(
        self,
        source: str,
        headers: Dict[str, str],
        payload: bytes,
        signature: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Route incoming webhook to appropriate handler.

        Args:
            source: Webhook source (github, gitlab, etc.)
            headers: HTTP headers
            payload: Raw webhook payload
            signature: Webhook signature for verification

        Returns:
            Processing result
        """
        # Validate source
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

        # Trigger workflows if mapped
        await self._trigger_workflows(event)

        return result

    async def _trigger_workflows(self, event: WebhookEvent):
        """
        Trigger workflows mapped to this event.

        Args:
            event: Webhook event
        """
        # Check for exact match
        key = f"{event.source}:{event.event_type}"

        if key in self.event_mappings:
            workflow_name = self.event_mappings[key]

            if workflow_name not in self.workflows:
                logger.error(f"Workflow {workflow_name} not registered")
                return

            logger.info(f"Triggering workflow {workflow_name} for event {key}")

            try:
                workflow = self.workflows[workflow_name]
                await workflow(event)
            except Exception as e:
                logger.error(f"Error executing workflow {workflow_name}: {e}", exc_info=True)


# Built-in workflows
async def automated_code_review_workflow(event: WebhookEvent):
    """
    Automated code review workflow.

    Triggered by:
    - GitHub pull_request (opened, synchronize)
    - GitLab merge_request_hook (open, update)
    """
    from aiops.agents import CodeReviewAgent

    logger.info(f"Starting automated code review for event {event.event_id}")

    # Extract PR/MR information
    if event.source == "github":
        pr_number = event.metadata.get("pr_number")
        repo = event.metadata.get("repository", {}).get("name")
        logger.info(f"Reviewing GitHub PR #{pr_number} in {repo}")

    elif event.source == "gitlab":
        mr_iid = event.metadata.get("mr_iid")
        project = event.metadata.get("project", {}).get("name")
        logger.info(f"Reviewing GitLab MR !{mr_iid} in {project}")

    # Initialize code review agent
    agent = CodeReviewAgent()

    # In a real implementation, would fetch code from the PR/MR
    # and run the code review agent
    # result = await agent.execute(code=code, context=context)

    logger.info("Code review completed (simulated)")


async def incident_response_workflow(event: WebhookEvent):
    """
    Automated incident response workflow.

    Triggered by:
    - PagerDuty incident.triggered (high urgency)
    """
    from aiops.agents import IncidentResponseAgent

    logger.info(f"Starting automated incident response for event {event.event_id}")

    incident_id = event.metadata.get("incident_number")
    title = event.metadata.get("title")
    urgency = event.metadata.get("urgency")

    logger.info(f"Analyzing incident #{incident_id}: {title} ({urgency})")

    # Initialize incident response agent
    agent = IncidentResponseAgent()

    # Build incident data
    incident_data = {
        "incident_id": f"PD-{incident_id}",
        "title": title,
        "severity": "critical" if urgency == "high" else "high",
        "description": event.metadata.get("description", ""),
    }

    # In a real implementation, would fetch logs, metrics, and alerts
    # result = await agent.execute(incident_data=incident_data, logs=logs, metrics=metrics)

    logger.info("Incident analysis completed (simulated)")


async def release_validation_workflow(event: WebhookEvent):
    """
    Automated release validation workflow.

    Triggered by:
    - GitHub release (published)
    - GitLab release_hook
    """
    from aiops.agents import ReleaseManagerAgent

    logger.info(f"Starting release validation for event {event.event_id}")

    if event.source == "github":
        tag = event.metadata.get("release_tag")
        logger.info(f"Validating GitHub release {tag}")

    elif event.source == "gitlab":
        tag = event.metadata.get("release_tag")
        logger.info(f"Validating GitLab release {tag}")

    # In a real implementation, would validate the release
    logger.info("Release validation completed (simulated)")
