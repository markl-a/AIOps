"""GitLab webhook handler."""

from typing import Dict, Any
from aiops.webhooks.webhook_handler import WebhookHandler, WebhookEvent
from aiops.core.logger import get_logger
import uuid

logger = get_logger(__name__)


class GitLabWebhookHandler(WebhookHandler):
    """
    Handle GitLab webhooks.

    Supported events:
    - Push Hook: Code pushed to repository
    - Merge Request Hook: MR opened, merged, etc.
    - Issue Hook: Issue created, updated, closed
    - Pipeline Hook: CI/CD pipeline status
    - Tag Push Hook: Tag created
    - Release Hook: Release created
    """

    def get_source_name(self) -> str:
        return "gitlab"

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify GitLab webhook token.

        GitLab sends token in X-Gitlab-Token header.
        """
        if not self.secret:
            return True

        return signature == self.secret

    def parse_event(self, headers: Dict[str, str], payload: Dict[str, Any]) -> WebhookEvent:
        """
        Parse GitLab webhook event.

        GitLab sends event type in X-Gitlab-Event header.
        """
        event_type = headers.get("x-gitlab-event", "unknown")
        event_id = str(uuid.uuid4())

        # Extract metadata
        metadata = self._extract_metadata(event_type, payload)

        return WebhookEvent(
            event_id=event_id,
            source=self.get_source_name(),
            event_type=event_type.lower().replace(" ", "_"),
            payload=payload,
            metadata=metadata,
        )

    def _extract_metadata(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract useful metadata from payload"""
        metadata: Dict[str, Any] = {}

        # Project info
        if "project" in payload:
            project = payload["project"]
            metadata["project"] = {
                "name": project.get("path_with_namespace"),
                "url": project.get("web_url"),
                "default_branch": project.get("default_branch"),
            }

        # User info
        if "user" in payload:
            user = payload["user"]
            metadata["user"] = {
                "username": user.get("username"),
                "name": user.get("name"),
            }

        # Event-specific metadata
        if event_type == "Push Hook":
            metadata["branch"] = payload.get("ref", "").replace("refs/heads/", "")
            metadata["commits_count"] = payload.get("total_commits_count", 0)
            metadata["before_sha"] = payload.get("before")
            metadata["after_sha"] = payload.get("after")

        elif event_type == "Merge Request Hook":
            mr = payload.get("object_attributes", {})
            metadata["mr_iid"] = mr.get("iid")
            metadata["mr_title"] = mr.get("title")
            metadata["mr_state"] = mr.get("state")
            metadata["mr_action"] = mr.get("action")
            metadata["mr_url"] = mr.get("url")
            metadata["source_branch"] = mr.get("source_branch")
            metadata["target_branch"] = mr.get("target_branch")
            metadata["merge_status"] = mr.get("merge_status")

        elif event_type == "Issue Hook":
            issue = payload.get("object_attributes", {})
            metadata["issue_iid"] = issue.get("iid")
            metadata["issue_title"] = issue.get("title")
            metadata["issue_state"] = issue.get("state")
            metadata["issue_action"] = issue.get("action")
            metadata["issue_url"] = issue.get("url")

        elif event_type == "Pipeline Hook":
            attrs = payload.get("object_attributes", {})
            metadata["pipeline_id"] = attrs.get("id")
            metadata["pipeline_status"] = attrs.get("status")
            metadata["pipeline_ref"] = attrs.get("ref")
            metadata["pipeline_duration"] = attrs.get("duration")

        elif event_type == "Tag Push Hook":
            metadata["tag"] = payload.get("ref", "").replace("refs/tags/", "")
            metadata["before_sha"] = payload.get("before")
            metadata["after_sha"] = payload.get("after")

        elif event_type == "Release Hook":
            metadata["release_action"] = payload.get("action")
            metadata["release_tag"] = payload.get("tag")
            metadata["release_name"] = payload.get("name")

        return metadata


# Default event handlers
async def handle_push_hook(event: WebhookEvent) -> Dict[str, Any]:
    """Handle GitLab push hook"""
    logger.info(
        f"Push to {event.metadata.get('project', {}).get('name')} "
        f"on branch {event.metadata.get('branch')}: "
        f"{event.metadata.get('commits_count')} commits"
    )

    return {
        "action": "push_received",
        "branch": event.metadata.get("branch"),
        "commits": event.metadata.get("commits_count"),
    }


async def handle_merge_request_hook(event: WebhookEvent) -> Dict[str, Any]:
    """Handle GitLab merge request hook"""
    action = event.metadata.get("mr_action")
    mr_iid = event.metadata.get("mr_iid")
    project = event.metadata.get("project", {}).get("name")

    logger.info(f"MR !{mr_iid} {action} in {project}")

    # Trigger code review for opened/updated MRs
    if action in ["open", "update"]:
        logger.info(f"Triggering automated code review for MR !{mr_iid}")
        return {
            "action": "code_review_triggered",
            "mr_iid": mr_iid,
        }

    return {
        "action": f"mr_{action}",
        "mr_iid": mr_iid,
    }


async def handle_pipeline_hook(event: WebhookEvent) -> Dict[str, Any]:
    """Handle GitLab pipeline hook"""
    pipeline_id = event.metadata.get("pipeline_id")
    status = event.metadata.get("pipeline_status")
    ref = event.metadata.get("pipeline_ref")

    logger.info(f"Pipeline {pipeline_id} on {ref}: {status}")

    # If pipeline failed, could trigger analysis
    if status == "failed":
        logger.warning(f"Pipeline {pipeline_id} failed")

    return {
        "action": "pipeline_completed",
        "pipeline_id": pipeline_id,
        "status": status,
    }
