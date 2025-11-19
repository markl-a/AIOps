"""Webhook API routes."""

from fastapi import APIRouter, Request, Header, HTTPException, BackgroundTasks
from typing import Optional
from aiops.webhooks import (
    WebhookRouter,
    GitHubWebhookHandler,
    GitLabWebhookHandler,
    JiraWebhookHandler,
    PagerDutyWebhookHandler,
)
from aiops.webhooks.github_handler import (
    handle_push_event,
    handle_pull_request_event,
    handle_issues_event,
    handle_workflow_run_event,
)
from aiops.webhooks.gitlab_handler import (
    handle_push_hook,
    handle_merge_request_hook,
    handle_pipeline_hook,
)
from aiops.webhooks.jira_handler import (
    handle_issue_created,
    handle_issue_updated,
    handle_sprint_started,
)
from aiops.webhooks.pagerduty_handler import (
    handle_incident_triggered,
    handle_incident_acknowledged,
    handle_incident_resolved,
)
from aiops.webhooks.webhook_router import (
    automated_code_review_workflow,
    incident_response_workflow,
    release_validation_workflow,
)
from aiops.core.logger import get_logger
import os

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Initialize webhook router
webhook_router = WebhookRouter()

# Initialize handlers
github_handler = GitHubWebhookHandler(secret=os.getenv("GITHUB_WEBHOOK_SECRET"))
gitlab_handler = GitLabWebhookHandler(secret=os.getenv("GITLAB_WEBHOOK_SECRET"))
jira_handler = JiraWebhookHandler(secret=os.getenv("JIRA_WEBHOOK_SECRET"))
pagerduty_handler = PagerDutyWebhookHandler(secret=os.getenv("PAGERDUTY_WEBHOOK_SECRET"))

# Register handlers
webhook_router.register_handler(github_handler)
webhook_router.register_handler(gitlab_handler)
webhook_router.register_handler(jira_handler)
webhook_router.register_handler(pagerduty_handler)

# Register event handlers
github_handler.register_handler("push", handle_push_event)
github_handler.register_handler("pull_request", handle_pull_request_event)
github_handler.register_handler("issues", handle_issues_event)
github_handler.register_handler("workflow_run", handle_workflow_run_event)

gitlab_handler.register_handler("push_hook", handle_push_hook)
gitlab_handler.register_handler("merge_request_hook", handle_merge_request_hook)
gitlab_handler.register_handler("pipeline_hook", handle_pipeline_hook)

jira_handler.register_handler("jira:issue_created", handle_issue_created)
jira_handler.register_handler("jira:issue_updated", handle_issue_updated)
jira_handler.register_handler("sprint_started", handle_sprint_started)

pagerduty_handler.register_handler("incident.triggered", handle_incident_triggered)
pagerduty_handler.register_handler("incident.acknowledged", handle_incident_acknowledged)
pagerduty_handler.register_handler("incident.resolved", handle_incident_resolved)

# Register workflows
webhook_router.register_workflow("code_review", automated_code_review_workflow)
webhook_router.register_workflow("incident_response", incident_response_workflow)
webhook_router.register_workflow("release_validation", release_validation_workflow)

# Map events to workflows
webhook_router.map_event_to_workflow("github", "pull_request", "code_review")
webhook_router.map_event_to_workflow("gitlab", "merge_request_hook", "code_review")
webhook_router.map_event_to_workflow("pagerduty", "incident.triggered", "incident_response")
webhook_router.map_event_to_workflow("github", "release", "release_validation")
webhook_router.map_event_to_workflow("gitlab", "release_hook", "release_validation")


@router.post("/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: Optional[str] = Header(None),
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_delivery: Optional[str] = Header(None),
):
    """
    Receive GitHub webhooks.

    Headers:
    - X-GitHub-Event: Event type
    - X-Hub-Signature-256: HMAC signature
    - X-GitHub-Delivery: Delivery ID
    """
    logger.info(f"Received GitHub webhook: {x_github_event} (delivery: {x_github_delivery})")

    # Get raw payload
    payload = await request.body()

    # Get all headers
    headers = dict(request.headers)

    # Route webhook (in background to avoid blocking)
    background_tasks.add_task(
        webhook_router.route_webhook,
        source="github",
        headers=headers,
        payload=payload,
        signature=x_hub_signature_256,
    )

    return {"status": "accepted", "event": x_github_event}


@router.post("/gitlab")
async def gitlab_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_gitlab_event: Optional[str] = Header(None),
    x_gitlab_token: Optional[str] = Header(None),
):
    """
    Receive GitLab webhooks.

    Headers:
    - X-Gitlab-Event: Event type
    - X-Gitlab-Token: Webhook token
    """
    logger.info(f"Received GitLab webhook: {x_gitlab_event}")

    # Get raw payload
    payload = await request.body()

    # Get all headers
    headers = dict(request.headers)

    # Route webhook
    background_tasks.add_task(
        webhook_router.route_webhook,
        source="gitlab",
        headers=headers,
        payload=payload,
        signature=x_gitlab_token,
    )

    return {"status": "accepted", "event": x_gitlab_event}


@router.post("/jira")
async def jira_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Receive Jira webhooks.

    Jira sends event type in the payload body.
    """
    logger.info("Received Jira webhook")

    # Get raw payload
    payload = await request.body()

    # Get all headers
    headers = dict(request.headers)

    # Route webhook
    background_tasks.add_task(
        webhook_router.route_webhook,
        source="jira",
        headers=headers,
        payload=payload,
    )

    return {"status": "accepted"}


@router.post("/pagerduty")
async def pagerduty_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_pagerduty_signature: Optional[str] = Header(None),
):
    """
    Receive PagerDuty webhooks.

    Headers:
    - X-PagerDuty-Signature: HMAC signature
    """
    logger.info("Received PagerDuty webhook")

    # Get raw payload
    payload = await request.body()

    # Get all headers
    headers = dict(request.headers)

    # Route webhook
    background_tasks.add_task(
        webhook_router.route_webhook,
        source="pagerduty",
        headers=headers,
        payload=payload,
        signature=x_pagerduty_signature,
    )

    return {"status": "accepted"}


@router.get("/status")
async def webhook_status():
    """Get webhook system status"""
    return {
        "status": "operational",
        "handlers": list(webhook_router.handlers.keys()),
        "workflows": list(webhook_router.workflows.keys()),
        "event_mappings": len(webhook_router.event_mappings),
    }
