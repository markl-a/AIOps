"""GitHub webhook handler."""

from typing import Dict, Any
from aiops.webhooks.webhook_handler import WebhookHandler, WebhookEvent
from aiops.core.logger import get_logger
import uuid

logger = get_logger(__name__)


class GitHubWebhookHandler(WebhookHandler):
    """
    Handle GitHub webhooks.

    Supported events:
    - push: Code pushed to repository
    - pull_request: Pull request opened, closed, etc.
    - pull_request_review: PR reviewed
    - issues: Issue opened, closed, etc.
    - issue_comment: Comment on issue/PR
    - release: Release published
    - workflow_run: GitHub Actions workflow completed
    """

    def get_source_name(self) -> str:
        return "github"

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify GitHub webhook signature.

        GitHub sends signature in format: sha256=<hexdigest>
        """
        return self._verify_hmac_signature(
            payload=payload,
            signature=signature,
            algorithm="sha256",
            prefix="sha256=",
        )

    def parse_event(self, headers: Dict[str, str], payload: Dict[str, Any]) -> WebhookEvent:
        """
        Parse GitHub webhook event.

        GitHub sends event type in X-GitHub-Event header.
        """
        event_type = headers.get("x-github-event", "unknown")
        event_id = headers.get("x-github-delivery", str(uuid.uuid4()))

        # Extract metadata based on event type
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

        # Repository info
        if "repository" in payload:
            repo = payload["repository"]
            metadata["repository"] = {
                "name": repo.get("full_name"),
                "url": repo.get("html_url"),
                "default_branch": repo.get("default_branch"),
            }

        # Sender info
        if "sender" in payload:
            sender = payload["sender"]
            metadata["sender"] = {
                "username": sender.get("login"),
                "type": sender.get("type"),
            }

        # Event-specific metadata
        if event_type == "push":
            metadata["branch"] = payload.get("ref", "").replace("refs/heads/", "")
            metadata["commits_count"] = len(payload.get("commits", []))
            metadata["forced"] = payload.get("forced", False)

        elif event_type == "pull_request":
            pr = payload.get("pull_request", {})
            metadata["pr_number"] = pr.get("number")
            metadata["pr_title"] = pr.get("title")
            metadata["pr_state"] = pr.get("state")
            metadata["pr_action"] = payload.get("action")
            metadata["pr_url"] = pr.get("html_url")
            metadata["base_branch"] = pr.get("base", {}).get("ref")
            metadata["head_branch"] = pr.get("head", {}).get("ref")
            metadata["mergeable"] = pr.get("mergeable")
            metadata["merged"] = pr.get("merged", False)

        elif event_type == "pull_request_review":
            review = payload.get("review", {})
            metadata["pr_number"] = payload.get("pull_request", {}).get("number")
            metadata["review_state"] = review.get("state")
            metadata["review_action"] = payload.get("action")

        elif event_type == "issues":
            issue = payload.get("issue", {})
            metadata["issue_number"] = issue.get("number")
            metadata["issue_title"] = issue.get("title")
            metadata["issue_state"] = issue.get("state")
            metadata["issue_action"] = payload.get("action")
            metadata["issue_url"] = issue.get("html_url")

        elif event_type == "issue_comment":
            comment = payload.get("comment", {})
            metadata["comment_action"] = payload.get("action")
            metadata["comment_url"] = comment.get("html_url")
            if "issue" in payload:
                metadata["issue_number"] = payload["issue"].get("number")
            elif "pull_request" in payload:
                metadata["pr_number"] = payload["pull_request"].get("number")

        elif event_type == "release":
            release = payload.get("release", {})
            metadata["release_action"] = payload.get("action")
            metadata["release_tag"] = release.get("tag_name")
            metadata["release_name"] = release.get("name")
            metadata["release_prerelease"] = release.get("prerelease", False)

        elif event_type == "workflow_run":
            workflow = payload.get("workflow_run", {})
            metadata["workflow_name"] = workflow.get("name")
            metadata["workflow_status"] = workflow.get("status")
            metadata["workflow_conclusion"] = workflow.get("conclusion")
            metadata["workflow_action"] = payload.get("action")

        return metadata


# Default event handlers
async def handle_push_event(event: WebhookEvent) -> Dict[str, Any]:
    """Handle push event"""
    logger.info(
        f"Push to {event.metadata.get('repository', {}).get('name')} "
        f"on branch {event.metadata.get('branch')}: "
        f"{event.metadata.get('commits_count')} commits"
    )

    return {
        "action": "push_received",
        "branch": event.metadata.get("branch"),
        "commits": event.metadata.get("commits_count"),
    }


async def handle_pull_request_event(event: WebhookEvent) -> Dict[str, Any]:
    """Handle pull request event"""
    action = event.metadata.get("pr_action")
    pr_number = event.metadata.get("pr_number")
    repo = event.metadata.get("repository", {}).get("name")

    logger.info(f"PR #{pr_number} {action} in {repo}")

    # If PR opened or synchronized (new commits), trigger code review
    if action in ["opened", "synchronize"]:
        logger.info(f"Triggering automated code review for PR #{pr_number}")
        return {
            "action": "code_review_triggered",
            "pr_number": pr_number,
        }

    return {
        "action": f"pr_{action}",
        "pr_number": pr_number,
    }


async def handle_issues_event(event: WebhookEvent) -> Dict[str, Any]:
    """Handle issues event"""
    action = event.metadata.get("issue_action")
    issue_number = event.metadata.get("issue_number")
    repo = event.metadata.get("repository", {}).get("name")

    logger.info(f"Issue #{issue_number} {action} in {repo}")

    return {
        "action": f"issue_{action}",
        "issue_number": issue_number,
    }


async def handle_workflow_run_event(event: WebhookEvent) -> Dict[str, Any]:
    """Handle GitHub Actions workflow run event"""
    workflow_name = event.metadata.get("workflow_name")
    status = event.metadata.get("workflow_status")
    conclusion = event.metadata.get("workflow_conclusion")

    logger.info(f"Workflow '{workflow_name}' {status} with conclusion: {conclusion}")

    # If workflow failed, could trigger incident analysis
    if conclusion == "failure":
        logger.warning(f"Workflow '{workflow_name}' failed")

    return {
        "action": "workflow_completed",
        "workflow": workflow_name,
        "status": status,
        "conclusion": conclusion,
    }
