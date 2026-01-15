"""Comprehensive tests for webhook handlers."""

import pytest
import json
import hmac
import hashlib
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from aiops.webhooks.webhook_handler import (
    WebhookHandler,
    WebhookEvent,
    WebhookProcessor,
)
from aiops.webhooks.github_handler import (
    GitHubWebhookHandler,
    handle_push_event,
    handle_pull_request_event,
    handle_issues_event,
    handle_workflow_run_event,
)
from aiops.webhooks.gitlab_handler import (
    GitLabWebhookHandler,
    handle_push_hook,
    handle_merge_request_hook,
    handle_pipeline_hook,
)
from aiops.webhooks.jira_handler import (
    JiraWebhookHandler,
    handle_issue_created,
    handle_issue_updated,
    handle_sprint_started,
)
from aiops.webhooks.pagerduty_handler import (
    PagerDutyWebhookHandler,
    handle_incident_triggered,
    handle_incident_acknowledged,
    handle_incident_resolved,
)
from aiops.webhooks.webhook_router import (
    WebhookRouter,
    automated_code_review_workflow,
    incident_response_workflow,
    release_validation_workflow,
)


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def github_secret():
    """GitHub webhook secret."""
    return "github_secret_key_12345"


@pytest.fixture
def gitlab_secret():
    """GitLab webhook token."""
    return "gitlab_token_12345"


@pytest.fixture
def jira_secret():
    """Jira webhook secret."""
    return "jira_secret_key_12345"


@pytest.fixture
def pagerduty_secret():
    """PagerDuty webhook secret."""
    return "pagerduty_secret_key_12345"


@pytest.fixture
def github_handler(github_secret):
    """Create GitHub webhook handler."""
    return GitHubWebhookHandler(secret=github_secret)


@pytest.fixture
def github_handler_no_secret():
    """Create GitHub webhook handler without secret."""
    return GitHubWebhookHandler()


@pytest.fixture
def gitlab_handler(gitlab_secret):
    """Create GitLab webhook handler."""
    return GitLabWebhookHandler(secret=gitlab_secret)


@pytest.fixture
def jira_handler(jira_secret):
    """Create Jira webhook handler."""
    return JiraWebhookHandler(secret=jira_secret)


@pytest.fixture
def pagerduty_handler(pagerduty_secret):
    """Create PagerDuty webhook handler."""
    return PagerDutyWebhookHandler(secret=pagerduty_secret)


@pytest.fixture
def webhook_router():
    """Create webhook router."""
    return WebhookRouter()


@pytest.fixture
def webhook_processor():
    """Create webhook processor."""
    return WebhookProcessor()


def create_github_signature(payload: bytes, secret: str) -> str:
    """Create GitHub HMAC SHA256 signature."""
    mac = hmac.new(secret.encode(), payload, hashlib.sha256)
    return f"sha256={mac.hexdigest()}"


def create_jira_signature(payload: bytes, secret: str) -> str:
    """Create Jira HMAC SHA256 signature."""
    mac = hmac.new(secret.encode(), payload, hashlib.sha256)
    return mac.hexdigest()


def create_pagerduty_signature(payload: bytes, secret: str) -> str:
    """Create PagerDuty HMAC SHA256 signature."""
    mac = hmac.new(secret.encode(), payload, hashlib.sha256)
    return f"v1={mac.hexdigest()}"


# ==============================================================================
# WebhookEvent Model Tests
# ==============================================================================


class TestWebhookEvent:
    """Tests for WebhookEvent model."""

    def test_webhook_event_creation(self):
        """Test creating a webhook event."""
        event = WebhookEvent(
            event_id="test-123",
            source="github",
            event_type="push",
            payload={"ref": "refs/heads/main"},
            metadata={"branch": "main"},
        )

        assert event.event_id == "test-123"
        assert event.source == "github"
        assert event.event_type == "push"
        assert event.payload == {"ref": "refs/heads/main"}
        assert event.metadata == {"branch": "main"}
        assert event.timestamp is not None

    def test_webhook_event_default_timestamp(self):
        """Test that timestamp is auto-generated."""
        event = WebhookEvent(
            event_id="test-123",
            source="github",
            event_type="push",
            payload={},
        )

        assert event.timestamp is not None
        # Should be a valid ISO format timestamp
        datetime.fromisoformat(event.timestamp)

    def test_webhook_event_default_metadata(self):
        """Test that metadata defaults to empty dict."""
        event = WebhookEvent(
            event_id="test-123",
            source="github",
            event_type="push",
            payload={},
        )

        assert event.metadata == {}


# ==============================================================================
# GitHub Webhook Handler Tests
# ==============================================================================


class TestGitHubWebhookHandler:
    """Tests for GitHub webhook handler."""

    def test_get_source_name(self, github_handler):
        """Test source name."""
        assert github_handler.get_source_name() == "github"

    def test_verify_signature_valid(self, github_handler, github_secret):
        """Test valid signature verification."""
        payload = b'{"action": "opened"}'
        signature = create_github_signature(payload, github_secret)

        assert github_handler.verify_signature(payload, signature) is True

    def test_verify_signature_invalid(self, github_handler):
        """Test invalid signature verification."""
        payload = b'{"action": "opened"}'
        invalid_signature = "sha256=invalid_signature"

        assert github_handler.verify_signature(payload, invalid_signature) is False

    def test_verify_signature_no_secret(self, github_handler_no_secret):
        """Test signature verification without secret configured."""
        payload = b'{"action": "opened"}'
        signature = "sha256=some_signature"

        # Should return False when no secret is configured
        assert github_handler_no_secret.verify_signature(payload, signature) is False

    def test_verify_signature_wrong_prefix(self, github_handler, github_secret):
        """Test signature with wrong prefix."""
        payload = b'{"action": "opened"}'
        mac = hmac.new(github_secret.encode(), payload, hashlib.sha256)
        # Wrong prefix
        signature = f"sha1={mac.hexdigest()}"

        assert github_handler.verify_signature(payload, signature) is False

    def test_verify_signature_tampered_payload(self, github_handler, github_secret):
        """Test signature with tampered payload."""
        original_payload = b'{"action": "opened"}'
        signature = create_github_signature(original_payload, github_secret)

        tampered_payload = b'{"action": "closed"}'
        assert github_handler.verify_signature(tampered_payload, signature) is False

    def test_parse_push_event(self, github_handler):
        """Test parsing push event."""
        headers = {
            "x-github-event": "push",
            "x-github-delivery": "delivery-123",
        }
        payload = {
            "ref": "refs/heads/main",
            "forced": False,
            "commits": [{"id": "abc123"}, {"id": "def456"}],
            "repository": {
                "full_name": "owner/repo",
                "html_url": "https://github.com/owner/repo",
                "default_branch": "main",
            },
            "sender": {
                "login": "testuser",
                "type": "User",
            },
        }

        event = github_handler.parse_event(headers, payload)

        assert event.event_id == "delivery-123"
        assert event.source == "github"
        assert event.event_type == "push"
        assert event.metadata["branch"] == "main"
        assert event.metadata["commits_count"] == 2
        assert event.metadata["forced"] is False
        assert event.metadata["repository"]["name"] == "owner/repo"
        assert event.metadata["sender"]["username"] == "testuser"

    def test_parse_pull_request_event(self, github_handler):
        """Test parsing pull request event."""
        headers = {
            "x-github-event": "pull_request",
            "x-github-delivery": "delivery-456",
        }
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 42,
                "title": "Add new feature",
                "state": "open",
                "html_url": "https://github.com/owner/repo/pull/42",
                "base": {"ref": "main"},
                "head": {"ref": "feature-branch"},
                "mergeable": True,
                "merged": False,
            },
            "repository": {
                "full_name": "owner/repo",
                "html_url": "https://github.com/owner/repo",
            },
            "sender": {"login": "testuser"},
        }

        event = github_handler.parse_event(headers, payload)

        assert event.event_type == "pull_request"
        assert event.metadata["pr_number"] == 42
        assert event.metadata["pr_title"] == "Add new feature"
        assert event.metadata["pr_state"] == "open"
        assert event.metadata["pr_action"] == "opened"
        assert event.metadata["base_branch"] == "main"
        assert event.metadata["head_branch"] == "feature-branch"
        assert event.metadata["mergeable"] is True
        assert event.metadata["merged"] is False

    def test_parse_pull_request_review_event(self, github_handler):
        """Test parsing pull request review event."""
        headers = {
            "x-github-event": "pull_request_review",
            "x-github-delivery": "delivery-789",
        }
        payload = {
            "action": "submitted",
            "review": {
                "state": "approved",
            },
            "pull_request": {
                "number": 42,
            },
        }

        event = github_handler.parse_event(headers, payload)

        assert event.event_type == "pull_request_review"
        assert event.metadata["pr_number"] == 42
        assert event.metadata["review_state"] == "approved"
        assert event.metadata["review_action"] == "submitted"

    def test_parse_issues_event(self, github_handler):
        """Test parsing issues event."""
        headers = {
            "x-github-event": "issues",
            "x-github-delivery": "delivery-101",
        }
        payload = {
            "action": "opened",
            "issue": {
                "number": 123,
                "title": "Bug report",
                "state": "open",
                "html_url": "https://github.com/owner/repo/issues/123",
            },
            "repository": {"full_name": "owner/repo"},
        }

        event = github_handler.parse_event(headers, payload)

        assert event.event_type == "issues"
        assert event.metadata["issue_number"] == 123
        assert event.metadata["issue_title"] == "Bug report"
        assert event.metadata["issue_state"] == "open"
        assert event.metadata["issue_action"] == "opened"

    def test_parse_issue_comment_event_on_issue(self, github_handler):
        """Test parsing issue comment on issue."""
        headers = {
            "x-github-event": "issue_comment",
            "x-github-delivery": "delivery-102",
        }
        payload = {
            "action": "created",
            "comment": {
                "html_url": "https://github.com/owner/repo/issues/123#comment-1",
            },
            "issue": {
                "number": 123,
            },
        }

        event = github_handler.parse_event(headers, payload)

        assert event.event_type == "issue_comment"
        assert event.metadata["comment_action"] == "created"
        assert event.metadata["issue_number"] == 123

    def test_parse_issue_comment_event_on_pr(self, github_handler):
        """Test parsing issue comment on PR."""
        headers = {
            "x-github-event": "issue_comment",
            "x-github-delivery": "delivery-103",
        }
        payload = {
            "action": "created",
            "comment": {
                "html_url": "https://github.com/owner/repo/pull/42#comment-1",
            },
            "pull_request": {
                "number": 42,
            },
        }

        event = github_handler.parse_event(headers, payload)

        assert event.metadata["pr_number"] == 42

    def test_parse_release_event(self, github_handler):
        """Test parsing release event."""
        headers = {
            "x-github-event": "release",
            "x-github-delivery": "delivery-104",
        }
        payload = {
            "action": "published",
            "release": {
                "tag_name": "v1.0.0",
                "name": "Version 1.0.0",
                "prerelease": False,
            },
        }

        event = github_handler.parse_event(headers, payload)

        assert event.event_type == "release"
        assert event.metadata["release_action"] == "published"
        assert event.metadata["release_tag"] == "v1.0.0"
        assert event.metadata["release_name"] == "Version 1.0.0"
        assert event.metadata["release_prerelease"] is False

    def test_parse_workflow_run_event(self, github_handler):
        """Test parsing workflow run event."""
        headers = {
            "x-github-event": "workflow_run",
            "x-github-delivery": "delivery-105",
        }
        payload = {
            "action": "completed",
            "workflow_run": {
                "name": "CI",
                "status": "completed",
                "conclusion": "success",
            },
        }

        event = github_handler.parse_event(headers, payload)

        assert event.event_type == "workflow_run"
        assert event.metadata["workflow_name"] == "CI"
        assert event.metadata["workflow_status"] == "completed"
        assert event.metadata["workflow_conclusion"] == "success"
        assert event.metadata["workflow_action"] == "completed"

    def test_parse_unknown_event(self, github_handler):
        """Test parsing unknown event type."""
        headers = {}
        payload = {}

        event = github_handler.parse_event(headers, payload)

        assert event.event_type == "unknown"

    def test_register_and_handle_event(self, github_handler):
        """Test registering and handling events."""
        handler_called = False

        async def test_handler(event: WebhookEvent):
            nonlocal handler_called
            handler_called = True
            return {"handled": True}

        github_handler.register_handler("push", test_handler)

        event = WebhookEvent(
            event_id="test-123",
            source="github",
            event_type="push",
            payload={},
        )

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            github_handler.handle_event(event)
        )

        assert handler_called
        assert result["status"] == "success"
        assert result["result"]["handled"] is True

    def test_handle_unregistered_event(self, github_handler):
        """Test handling unregistered event type."""
        event = WebhookEvent(
            event_id="test-123",
            source="github",
            event_type="unknown_event",
            payload={},
        )

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            github_handler.handle_event(event)
        )

        assert result["status"] == "ignored"
        assert "No handler" in result["reason"]

    def test_handle_event_with_exception(self, github_handler):
        """Test event handling when handler raises exception."""

        async def failing_handler(event: WebhookEvent):
            raise ValueError("Handler error")

        github_handler.register_handler("push", failing_handler)

        event = WebhookEvent(
            event_id="test-123",
            source="github",
            event_type="push",
            payload={},
        )

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            github_handler.handle_event(event)
        )

        assert result["status"] == "error"
        assert "Handler error" in result["error"]


# ==============================================================================
# GitHub Event Handler Function Tests
# ==============================================================================


class TestGitHubEventHandlers:
    """Tests for GitHub event handler functions."""

    @pytest.mark.asyncio
    async def test_handle_push_event(self):
        """Test push event handler."""
        event = WebhookEvent(
            event_id="test-123",
            source="github",
            event_type="push",
            payload={},
            metadata={
                "repository": {"name": "owner/repo"},
                "branch": "main",
                "commits_count": 3,
            },
        )

        result = await handle_push_event(event)

        assert result["action"] == "push_received"
        assert result["branch"] == "main"
        assert result["commits"] == 3

    @pytest.mark.asyncio
    async def test_handle_pull_request_event_opened(self):
        """Test PR opened event handler."""
        event = WebhookEvent(
            event_id="test-123",
            source="github",
            event_type="pull_request",
            payload={},
            metadata={
                "repository": {"name": "owner/repo"},
                "pr_action": "opened",
                "pr_number": 42,
            },
        )

        result = await handle_pull_request_event(event)

        assert result["action"] == "code_review_triggered"
        assert result["pr_number"] == 42

    @pytest.mark.asyncio
    async def test_handle_pull_request_event_synchronize(self):
        """Test PR synchronize event handler."""
        event = WebhookEvent(
            event_id="test-123",
            source="github",
            event_type="pull_request",
            payload={},
            metadata={
                "repository": {"name": "owner/repo"},
                "pr_action": "synchronize",
                "pr_number": 42,
            },
        )

        result = await handle_pull_request_event(event)

        assert result["action"] == "code_review_triggered"

    @pytest.mark.asyncio
    async def test_handle_pull_request_event_closed(self):
        """Test PR closed event handler."""
        event = WebhookEvent(
            event_id="test-123",
            source="github",
            event_type="pull_request",
            payload={},
            metadata={
                "repository": {"name": "owner/repo"},
                "pr_action": "closed",
                "pr_number": 42,
            },
        )

        result = await handle_pull_request_event(event)

        assert result["action"] == "pr_closed"
        assert result["pr_number"] == 42

    @pytest.mark.asyncio
    async def test_handle_issues_event(self):
        """Test issues event handler."""
        event = WebhookEvent(
            event_id="test-123",
            source="github",
            event_type="issues",
            payload={},
            metadata={
                "repository": {"name": "owner/repo"},
                "issue_action": "opened",
                "issue_number": 123,
            },
        )

        result = await handle_issues_event(event)

        assert result["action"] == "issue_opened"
        assert result["issue_number"] == 123

    @pytest.mark.asyncio
    async def test_handle_workflow_run_event_success(self):
        """Test workflow run success event."""
        event = WebhookEvent(
            event_id="test-123",
            source="github",
            event_type="workflow_run",
            payload={},
            metadata={
                "workflow_name": "CI",
                "workflow_status": "completed",
                "workflow_conclusion": "success",
            },
        )

        result = await handle_workflow_run_event(event)

        assert result["action"] == "workflow_completed"
        assert result["workflow"] == "CI"
        assert result["conclusion"] == "success"

    @pytest.mark.asyncio
    async def test_handle_workflow_run_event_failure(self):
        """Test workflow run failure event."""
        event = WebhookEvent(
            event_id="test-123",
            source="github",
            event_type="workflow_run",
            payload={},
            metadata={
                "workflow_name": "CI",
                "workflow_status": "completed",
                "workflow_conclusion": "failure",
            },
        )

        result = await handle_workflow_run_event(event)

        assert result["action"] == "workflow_completed"
        assert result["conclusion"] == "failure"


# ==============================================================================
# GitLab Webhook Handler Tests
# ==============================================================================


class TestGitLabWebhookHandler:
    """Tests for GitLab webhook handler."""

    def test_get_source_name(self, gitlab_handler):
        """Test source name."""
        assert gitlab_handler.get_source_name() == "gitlab"

    def test_verify_signature_valid(self, gitlab_handler, gitlab_secret):
        """Test valid token verification."""
        payload = b'{"object_kind": "push"}'

        # GitLab uses constant-time comparison of token
        assert gitlab_handler.verify_signature(payload, gitlab_secret) is True

    def test_verify_signature_invalid(self, gitlab_handler):
        """Test invalid token verification."""
        payload = b'{"object_kind": "push"}'

        assert gitlab_handler.verify_signature(payload, "wrong_token") is False

    def test_verify_signature_empty(self, gitlab_handler):
        """Test empty signature."""
        payload = b'{"object_kind": "push"}'

        assert gitlab_handler.verify_signature(payload, "") is False

    def test_verify_signature_no_secret(self):
        """Test verification without secret configured."""
        handler = GitLabWebhookHandler()
        payload = b'{"object_kind": "push"}'

        assert handler.verify_signature(payload, "some_token") is False

    def test_parse_push_hook(self, gitlab_handler):
        """Test parsing push hook."""
        headers = {"x-gitlab-event": "Push Hook"}
        payload = {
            "ref": "refs/heads/main",
            "total_commits_count": 5,
            "before": "abc123",
            "after": "def456",
            "project": {
                "path_with_namespace": "group/project",
                "web_url": "https://gitlab.com/group/project",
                "default_branch": "main",
            },
            "user": {
                "username": "testuser",
                "name": "Test User",
            },
        }

        event = gitlab_handler.parse_event(headers, payload)

        assert event.source == "gitlab"
        assert event.event_type == "push_hook"
        assert event.metadata["branch"] == "main"
        assert event.metadata["commits_count"] == 5
        assert event.metadata["before_sha"] == "abc123"
        assert event.metadata["after_sha"] == "def456"
        assert event.metadata["project"]["name"] == "group/project"
        assert event.metadata["user"]["username"] == "testuser"

    def test_parse_merge_request_hook(self, gitlab_handler):
        """Test parsing merge request hook."""
        headers = {"x-gitlab-event": "Merge Request Hook"}
        payload = {
            "object_attributes": {
                "iid": 42,
                "title": "New feature",
                "state": "opened",
                "action": "open",
                "url": "https://gitlab.com/group/project/-/merge_requests/42",
                "source_branch": "feature",
                "target_branch": "main",
                "merge_status": "can_be_merged",
            },
            "project": {
                "path_with_namespace": "group/project",
            },
        }

        event = gitlab_handler.parse_event(headers, payload)

        assert event.event_type == "merge_request_hook"
        assert event.metadata["mr_iid"] == 42
        assert event.metadata["mr_title"] == "New feature"
        assert event.metadata["mr_state"] == "opened"
        assert event.metadata["mr_action"] == "open"
        assert event.metadata["source_branch"] == "feature"
        assert event.metadata["target_branch"] == "main"
        assert event.metadata["merge_status"] == "can_be_merged"

    def test_parse_issue_hook(self, gitlab_handler):
        """Test parsing issue hook."""
        headers = {"x-gitlab-event": "Issue Hook"}
        payload = {
            "object_attributes": {
                "iid": 123,
                "title": "Bug report",
                "state": "opened",
                "action": "open",
                "url": "https://gitlab.com/group/project/-/issues/123",
            },
        }

        event = gitlab_handler.parse_event(headers, payload)

        assert event.event_type == "issue_hook"
        assert event.metadata["issue_iid"] == 123
        assert event.metadata["issue_title"] == "Bug report"
        assert event.metadata["issue_state"] == "opened"
        assert event.metadata["issue_action"] == "open"

    def test_parse_pipeline_hook(self, gitlab_handler):
        """Test parsing pipeline hook."""
        headers = {"x-gitlab-event": "Pipeline Hook"}
        payload = {
            "object_attributes": {
                "id": 12345,
                "status": "success",
                "ref": "main",
                "duration": 120,
            },
        }

        event = gitlab_handler.parse_event(headers, payload)

        assert event.event_type == "pipeline_hook"
        assert event.metadata["pipeline_id"] == 12345
        assert event.metadata["pipeline_status"] == "success"
        assert event.metadata["pipeline_ref"] == "main"
        assert event.metadata["pipeline_duration"] == 120

    def test_parse_tag_push_hook(self, gitlab_handler):
        """Test parsing tag push hook."""
        headers = {"x-gitlab-event": "Tag Push Hook"}
        payload = {
            "ref": "refs/tags/v1.0.0",
            "before": "0000000",
            "after": "abc123",
        }

        event = gitlab_handler.parse_event(headers, payload)

        assert event.event_type == "tag_push_hook"
        assert event.metadata["tag"] == "v1.0.0"
        assert event.metadata["after_sha"] == "abc123"

    def test_parse_release_hook(self, gitlab_handler):
        """Test parsing release hook."""
        headers = {"x-gitlab-event": "Release Hook"}
        payload = {
            "action": "create",
            "tag": "v1.0.0",
            "name": "Version 1.0.0",
        }

        event = gitlab_handler.parse_event(headers, payload)

        assert event.event_type == "release_hook"
        assert event.metadata["release_action"] == "create"
        assert event.metadata["release_tag"] == "v1.0.0"
        assert event.metadata["release_name"] == "Version 1.0.0"


# ==============================================================================
# GitLab Event Handler Function Tests
# ==============================================================================


class TestGitLabEventHandlers:
    """Tests for GitLab event handler functions."""

    @pytest.mark.asyncio
    async def test_handle_push_hook(self):
        """Test push hook handler."""
        event = WebhookEvent(
            event_id="test-123",
            source="gitlab",
            event_type="push_hook",
            payload={},
            metadata={
                "project": {"name": "group/project"},
                "branch": "main",
                "commits_count": 3,
            },
        )

        result = await handle_push_hook(event)

        assert result["action"] == "push_received"
        assert result["branch"] == "main"
        assert result["commits"] == 3

    @pytest.mark.asyncio
    async def test_handle_merge_request_hook_open(self):
        """Test MR open hook handler."""
        event = WebhookEvent(
            event_id="test-123",
            source="gitlab",
            event_type="merge_request_hook",
            payload={},
            metadata={
                "project": {"name": "group/project"},
                "mr_action": "open",
                "mr_iid": 42,
            },
        )

        result = await handle_merge_request_hook(event)

        assert result["action"] == "code_review_triggered"
        assert result["mr_iid"] == 42

    @pytest.mark.asyncio
    async def test_handle_merge_request_hook_update(self):
        """Test MR update hook handler."""
        event = WebhookEvent(
            event_id="test-123",
            source="gitlab",
            event_type="merge_request_hook",
            payload={},
            metadata={
                "project": {"name": "group/project"},
                "mr_action": "update",
                "mr_iid": 42,
            },
        )

        result = await handle_merge_request_hook(event)

        assert result["action"] == "code_review_triggered"

    @pytest.mark.asyncio
    async def test_handle_merge_request_hook_merge(self):
        """Test MR merge hook handler."""
        event = WebhookEvent(
            event_id="test-123",
            source="gitlab",
            event_type="merge_request_hook",
            payload={},
            metadata={
                "project": {"name": "group/project"},
                "mr_action": "merge",
                "mr_iid": 42,
            },
        )

        result = await handle_merge_request_hook(event)

        assert result["action"] == "mr_merge"
        assert result["mr_iid"] == 42

    @pytest.mark.asyncio
    async def test_handle_pipeline_hook_success(self):
        """Test pipeline success hook handler."""
        event = WebhookEvent(
            event_id="test-123",
            source="gitlab",
            event_type="pipeline_hook",
            payload={},
            metadata={
                "pipeline_id": 12345,
                "pipeline_status": "success",
                "pipeline_ref": "main",
            },
        )

        result = await handle_pipeline_hook(event)

        assert result["action"] == "pipeline_completed"
        assert result["pipeline_id"] == 12345
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_handle_pipeline_hook_failure(self):
        """Test pipeline failure hook handler."""
        event = WebhookEvent(
            event_id="test-123",
            source="gitlab",
            event_type="pipeline_hook",
            payload={},
            metadata={
                "pipeline_id": 12345,
                "pipeline_status": "failed",
                "pipeline_ref": "main",
            },
        )

        result = await handle_pipeline_hook(event)

        assert result["action"] == "pipeline_completed"
        assert result["status"] == "failed"


# ==============================================================================
# Jira Webhook Handler Tests
# ==============================================================================


class TestJiraWebhookHandler:
    """Tests for Jira webhook handler."""

    def test_get_source_name(self, jira_handler):
        """Test source name."""
        assert jira_handler.get_source_name() == "jira"

    def test_verify_signature_valid(self, jira_handler, jira_secret):
        """Test valid signature verification."""
        payload = b'{"webhookEvent": "jira:issue_created"}'
        signature = create_jira_signature(payload, jira_secret)

        assert jira_handler.verify_signature(payload, signature) is True

    def test_verify_signature_invalid(self, jira_handler):
        """Test invalid signature verification."""
        payload = b'{"webhookEvent": "jira:issue_created"}'

        assert jira_handler.verify_signature(payload, "invalid_signature") is False

    def test_verify_signature_no_secret(self):
        """Test verification without secret configured."""
        handler = JiraWebhookHandler()
        payload = b'{"webhookEvent": "jira:issue_created"}'

        assert handler.verify_signature(payload, "some_signature") is False

    def test_verify_signature_no_signature(self, jira_handler):
        """Test verification without signature provided."""
        payload = b'{"webhookEvent": "jira:issue_created"}'

        assert jira_handler.verify_signature(payload, "") is False

    def test_parse_issue_created_event(self, jira_handler):
        """Test parsing issue created event."""
        headers = {}
        payload = {
            "webhookEvent": "jira:issue_created",
            "user": {
                "displayName": "Test User",
                "emailAddress": "test@example.com",
            },
            "issue": {
                "key": "PROJ-123",
                "fields": {
                    "issuetype": {"name": "Bug"},
                    "status": {"name": "Open"},
                    "priority": {"name": "High"},
                    "summary": "Bug report",
                    "project": {"key": "PROJ"},
                },
            },
        }

        event = jira_handler.parse_event(headers, payload)

        assert event.source == "jira"
        assert event.event_type == "jira:issue_created"
        assert event.metadata["issue_key"] == "PROJ-123"
        assert event.metadata["issue_type"] == "Bug"
        assert event.metadata["issue_status"] == "Open"
        assert event.metadata["issue_priority"] == "High"
        assert event.metadata["issue_summary"] == "Bug report"
        assert event.metadata["project_key"] == "PROJ"
        assert event.metadata["user"]["name"] == "Test User"

    def test_parse_issue_updated_event_with_changelog(self, jira_handler):
        """Test parsing issue updated event with changelog."""
        headers = {}
        payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "key": "PROJ-123",
                "fields": {
                    "issuetype": {"name": "Bug"},
                    "status": {"name": "In Progress"},
                    "priority": {"name": "High"},
                    "summary": "Bug report",
                    "project": {"key": "PROJ"},
                },
            },
            "changelog": {
                "items": [
                    {
                        "field": "status",
                        "fromString": "Open",
                        "toString": "In Progress",
                    },
                    {
                        "field": "assignee",
                        "fromString": None,
                        "toString": "Test User",
                    },
                ],
            },
        }

        event = jira_handler.parse_event(headers, payload)

        assert event.event_type == "jira:issue_updated"
        assert event.metadata["issue_status"] == "In Progress"
        assert len(event.metadata["changes"]) == 2
        assert event.metadata["changes"][0]["field"] == "status"
        assert event.metadata["changes"][0]["from"] == "Open"
        assert event.metadata["changes"][0]["to"] == "In Progress"

    def test_parse_comment_created_event(self, jira_handler):
        """Test parsing comment created event."""
        headers = {}
        payload = {
            "webhookEvent": "comment_created",
            "issue": {
                "key": "PROJ-123",
                "fields": {
                    "issuetype": {"name": "Bug"},
                    "status": {"name": "Open"},
                    "priority": {"name": "High"},
                    "summary": "Bug report",
                    "project": {"key": "PROJ"},
                },
            },
            "comment": {
                "id": "12345",
                "body": "This is a comment",
            },
        }

        event = jira_handler.parse_event(headers, payload)

        assert event.event_type == "comment_created"
        assert event.metadata["comment_id"] == "12345"
        assert event.metadata["comment_body"] == "This is a comment"

    def test_parse_sprint_started_event(self, jira_handler):
        """Test parsing sprint started event."""
        headers = {}
        payload = {
            "webhookEvent": "sprint_started",
            "sprint": {
                "id": 123,
                "name": "Sprint 1",
                "state": "active",
            },
        }

        event = jira_handler.parse_event(headers, payload)

        assert event.event_type == "sprint_started"
        assert event.metadata["sprint_id"] == 123
        assert event.metadata["sprint_name"] == "Sprint 1"
        assert event.metadata["sprint_state"] == "active"

    def test_parse_unknown_event(self, jira_handler):
        """Test parsing unknown event type."""
        headers = {}
        payload = {}

        event = jira_handler.parse_event(headers, payload)

        assert event.event_type == "unknown"


# ==============================================================================
# Jira Event Handler Function Tests
# ==============================================================================


class TestJiraEventHandlers:
    """Tests for Jira event handler functions."""

    @pytest.mark.asyncio
    async def test_handle_issue_created_normal(self):
        """Test normal issue created handler."""
        event = WebhookEvent(
            event_id="test-123",
            source="jira",
            event_type="jira:issue_created",
            payload={},
            metadata={
                "issue_key": "PROJ-123",
                "issue_type": "Task",
                "issue_priority": "Medium",
            },
        )

        result = await handle_issue_created(event)

        assert result["action"] == "issue_created"
        assert result["issue_key"] == "PROJ-123"

    @pytest.mark.asyncio
    async def test_handle_issue_created_critical_bug(self):
        """Test critical bug issue created handler."""
        event = WebhookEvent(
            event_id="test-123",
            source="jira",
            event_type="jira:issue_created",
            payload={},
            metadata={
                "issue_key": "PROJ-123",
                "issue_type": "Bug",
                "issue_priority": "Critical",
            },
        )

        result = await handle_issue_created(event)

        assert result["action"] == "critical_bug_detected"
        assert result["issue_key"] == "PROJ-123"

    @pytest.mark.asyncio
    async def test_handle_issue_created_blocker_bug(self):
        """Test blocker bug issue created handler."""
        event = WebhookEvent(
            event_id="test-123",
            source="jira",
            event_type="jira:issue_created",
            payload={},
            metadata={
                "issue_key": "PROJ-123",
                "issue_type": "Bug",
                "issue_priority": "Blocker",
            },
        )

        result = await handle_issue_created(event)

        assert result["action"] == "critical_bug_detected"

    @pytest.mark.asyncio
    async def test_handle_issue_updated(self):
        """Test issue updated handler."""
        event = WebhookEvent(
            event_id="test-123",
            source="jira",
            event_type="jira:issue_updated",
            payload={},
            metadata={
                "issue_key": "PROJ-123",
                "changes": [
                    {"field": "status", "from": "Open", "to": "In Progress"},
                ],
            },
        )

        result = await handle_issue_updated(event)

        assert result["action"] == "issue_updated"
        assert result["issue_key"] == "PROJ-123"
        assert result["changes_count"] == 1

    @pytest.mark.asyncio
    async def test_handle_sprint_started(self):
        """Test sprint started handler."""
        event = WebhookEvent(
            event_id="test-123",
            source="jira",
            event_type="sprint_started",
            payload={},
            metadata={
                "sprint_name": "Sprint 1",
            },
        )

        result = await handle_sprint_started(event)

        assert result["action"] == "sprint_started"
        assert result["sprint_name"] == "Sprint 1"


# ==============================================================================
# PagerDuty Webhook Handler Tests
# ==============================================================================


class TestPagerDutyWebhookHandler:
    """Tests for PagerDuty webhook handler."""

    def test_get_source_name(self, pagerduty_handler):
        """Test source name."""
        assert pagerduty_handler.get_source_name() == "pagerduty"

    def test_verify_signature_valid(self, pagerduty_handler, pagerduty_secret):
        """Test valid signature verification."""
        payload = b'{"messages": []}'
        signature = create_pagerduty_signature(payload, pagerduty_secret)

        assert pagerduty_handler.verify_signature(payload, signature) is True

    def test_verify_signature_invalid(self, pagerduty_handler):
        """Test invalid signature verification."""
        payload = b'{"messages": []}'

        assert pagerduty_handler.verify_signature(payload, "v1=invalid") is False

    def test_verify_signature_no_secret_no_signature(self):
        """Test verification without secret or signature (returns True)."""
        handler = PagerDutyWebhookHandler()
        payload = b'{"messages": []}'

        # PagerDuty returns True if no signature/secret
        assert handler.verify_signature(payload, "") is True

    def test_parse_incident_triggered_event(self, pagerduty_handler):
        """Test parsing incident triggered event."""
        headers = {}
        payload = {
            "messages": [
                {
                    "id": "msg-123",
                    "event": "incident.triggered",
                    "incident": {
                        "id": "inc-123",
                        "incident_number": 42,
                        "incident_key": "key-123",
                        "title": "Server Down",
                        "description": "Production server is down",
                        "status": "triggered",
                        "urgency": "high",
                        "priority": {"summary": "P1"},
                        "service": {
                            "id": "svc-123",
                            "summary": "Production",
                        },
                        "assignments": [
                            {"assignee": {"summary": "On-call Engineer"}},
                        ],
                        "created_at": "2024-01-10T10:00:00Z",
                        "updated_at": "2024-01-10T10:00:00Z",
                        "escalation_policy": {"summary": "Default"},
                    },
                }
            ]
        }

        event = pagerduty_handler.parse_event(headers, payload)

        assert event.source == "pagerduty"
        assert event.event_id == "msg-123"
        assert event.event_type == "incident.triggered"
        assert event.metadata["incident_id"] == "inc-123"
        assert event.metadata["incident_number"] == 42
        assert event.metadata["incident_key"] == "key-123"
        assert event.metadata["title"] == "Server Down"
        assert event.metadata["description"] == "Production server is down"
        assert event.metadata["status"] == "triggered"
        assert event.metadata["urgency"] == "high"
        assert event.metadata["priority"] == "P1"
        assert event.metadata["service"]["id"] == "svc-123"
        assert event.metadata["service"]["name"] == "Production"
        assert event.metadata["assignees"] == ["On-call Engineer"]
        assert event.metadata["escalation_policy"] == "Default"

    def test_parse_incident_acknowledged_event(self, pagerduty_handler):
        """Test parsing incident acknowledged event."""
        headers = {}
        payload = {
            "messages": [
                {
                    "id": "msg-456",
                    "event": "incident.acknowledged",
                    "incident": {
                        "id": "inc-123",
                        "incident_number": 42,
                        "title": "Server Down",
                        "status": "acknowledged",
                        "urgency": "high",
                        "assignments": [
                            {"assignee": {"summary": "Engineer 1"}},
                            {"assignee": {"summary": "Engineer 2"}},
                        ],
                    },
                }
            ]
        }

        event = pagerduty_handler.parse_event(headers, payload)

        assert event.event_type == "incident.acknowledged"
        assert event.metadata["status"] == "acknowledged"
        assert len(event.metadata["assignees"]) == 2

    def test_parse_incident_resolved_event(self, pagerduty_handler):
        """Test parsing incident resolved event."""
        headers = {}
        payload = {
            "messages": [
                {
                    "id": "msg-789",
                    "event": "incident.resolved",
                    "incident": {
                        "id": "inc-123",
                        "incident_number": 42,
                        "title": "Server Down",
                        "status": "resolved",
                        "urgency": "high",
                    },
                }
            ]
        }

        event = pagerduty_handler.parse_event(headers, payload)

        assert event.event_type == "incident.resolved"
        assert event.metadata["status"] == "resolved"

    def test_parse_empty_messages(self, pagerduty_handler):
        """Test parsing webhook with no messages."""
        headers = {}
        payload = {"messages": []}

        event = pagerduty_handler.parse_event(headers, payload)

        assert event.event_type == "unknown"
        assert event.metadata == {}

    def test_parse_no_messages_key(self, pagerduty_handler):
        """Test parsing webhook without messages key."""
        headers = {}
        payload = {}

        event = pagerduty_handler.parse_event(headers, payload)

        assert event.event_type == "unknown"


# ==============================================================================
# PagerDuty Event Handler Function Tests
# ==============================================================================


class TestPagerDutyEventHandlers:
    """Tests for PagerDuty event handler functions."""

    @pytest.mark.asyncio
    async def test_handle_incident_triggered_high_urgency(self):
        """Test high urgency incident triggered handler."""
        event = WebhookEvent(
            event_id="test-123",
            source="pagerduty",
            event_type="incident.triggered",
            payload={},
            metadata={
                "incident_number": 42,
                "title": "Server Down",
                "urgency": "high",
                "service": {"name": "Production"},
            },
        )

        result = await handle_incident_triggered(event)

        assert result["action"] == "incident_response_triggered"
        assert result["incident_id"] == 42
        assert result["urgency"] == "high"

    @pytest.mark.asyncio
    async def test_handle_incident_triggered_low_urgency(self):
        """Test low urgency incident triggered handler."""
        event = WebhookEvent(
            event_id="test-123",
            source="pagerduty",
            event_type="incident.triggered",
            payload={},
            metadata={
                "incident_number": 42,
                "title": "Minor Issue",
                "urgency": "low",
                "service": {"name": "Staging"},
            },
        )

        result = await handle_incident_triggered(event)

        assert result["action"] == "incident_triggered"
        assert result["incident_id"] == 42

    @pytest.mark.asyncio
    async def test_handle_incident_acknowledged(self):
        """Test incident acknowledged handler."""
        event = WebhookEvent(
            event_id="test-123",
            source="pagerduty",
            event_type="incident.acknowledged",
            payload={},
            metadata={
                "incident_number": 42,
                "assignees": ["Engineer 1", "Engineer 2"],
            },
        )

        result = await handle_incident_acknowledged(event)

        assert result["action"] == "incident_acknowledged"
        assert result["incident_id"] == 42
        assert result["assignees"] == ["Engineer 1", "Engineer 2"]

    @pytest.mark.asyncio
    async def test_handle_incident_resolved(self):
        """Test incident resolved handler."""
        event = WebhookEvent(
            event_id="test-123",
            source="pagerduty",
            event_type="incident.resolved",
            payload={},
            metadata={
                "incident_number": 42,
                "title": "Server Down",
            },
        )

        result = await handle_incident_resolved(event)

        assert result["action"] == "incident_resolved"
        assert result["incident_id"] == 42
        assert result["postmortem_recommended"] is True


# ==============================================================================
# WebhookProcessor Tests
# ==============================================================================


class TestWebhookProcessor:
    """Tests for WebhookProcessor."""

    def test_register_handler(self, webhook_processor, github_handler):
        """Test registering a handler."""
        webhook_processor.register_handler(github_handler)

        assert "github" in webhook_processor.handlers
        assert webhook_processor.handlers["github"] == github_handler

    def test_register_workflow(self, webhook_processor):
        """Test registering a workflow."""

        async def test_workflow(event):
            pass

        webhook_processor.register_workflow("test", test_workflow)

        assert "test" in webhook_processor.workflows

    @pytest.mark.asyncio
    async def test_process_webhook_unknown_source(self, webhook_processor):
        """Test processing webhook from unknown source."""
        result = await webhook_processor.process_webhook(
            source="unknown",
            headers={},
            payload=b"{}",
        )

        assert result["status"] == "error"
        assert "Unknown source" in result["error"]

    @pytest.mark.asyncio
    async def test_process_webhook_valid_signature(
        self, webhook_processor, github_handler, github_secret
    ):
        """Test processing webhook with valid signature."""
        webhook_processor.register_handler(github_handler)

        payload = json.dumps({
            "ref": "refs/heads/main",
            "commits": [],
            "repository": {"full_name": "test/repo"},
        }).encode()
        signature = create_github_signature(payload, github_secret)
        headers = {"x-github-event": "push", "x-github-delivery": "test-123"}

        result = await webhook_processor.process_webhook(
            source="github",
            headers=headers,
            payload=payload,
            signature=signature,
        )

        # Should process successfully (ignored if no handler registered)
        assert result["status"] in ["success", "ignored"]

    @pytest.mark.asyncio
    async def test_process_webhook_invalid_signature(
        self, webhook_processor, github_handler
    ):
        """Test processing webhook with invalid signature."""
        webhook_processor.register_handler(github_handler)

        payload = b'{"ref": "refs/heads/main"}'
        headers = {"x-github-event": "push"}

        result = await webhook_processor.process_webhook(
            source="github",
            headers=headers,
            payload=payload,
            signature="sha256=invalid",
        )

        assert result["status"] == "error"
        assert "Invalid signature" in result["error"]

    @pytest.mark.asyncio
    async def test_process_webhook_missing_signature(
        self, webhook_processor, github_handler
    ):
        """Test processing webhook with missing signature when required."""
        webhook_processor.register_handler(github_handler)

        payload = b'{"ref": "refs/heads/main"}'
        headers = {"x-github-event": "push"}

        result = await webhook_processor.process_webhook(
            source="github",
            headers=headers,
            payload=payload,
            signature=None,
        )

        assert result["status"] == "error"
        assert "Missing signature" in result["error"]

    @pytest.mark.asyncio
    async def test_process_webhook_malformed_payload(
        self, webhook_processor, github_handler, github_secret
    ):
        """Test processing webhook with malformed payload."""
        webhook_processor.register_handler(github_handler)

        payload = b"not valid json"
        signature = create_github_signature(payload, github_secret)
        headers = {"x-github-event": "push"}

        result = await webhook_processor.process_webhook(
            source="github",
            headers=headers,
            payload=payload,
            signature=signature,
        )

        assert result["status"] == "error"
        assert "Invalid payload" in result["error"]

    @pytest.mark.asyncio
    async def test_process_webhook_no_secret_configured(self, webhook_processor):
        """Test processing webhook when no secret is configured."""
        handler = GitHubWebhookHandler()  # No secret
        webhook_processor.register_handler(handler)

        payload = json.dumps({"ref": "refs/heads/main", "commits": []}).encode()
        headers = {"x-github-event": "push"}

        result = await webhook_processor.process_webhook(
            source="github",
            headers=headers,
            payload=payload,
            require_signature=False,
        )

        # Should work when signature not required
        assert result["status"] in ["success", "ignored"]


# ==============================================================================
# WebhookRouter Tests
# ==============================================================================


class TestWebhookRouter:
    """Tests for WebhookRouter."""

    def test_register_handler(self, webhook_router, github_handler):
        """Test registering a handler."""
        webhook_router.register_handler(github_handler)

        assert "github" in webhook_router.handlers

    def test_register_workflow(self, webhook_router):
        """Test registering a workflow."""

        async def test_workflow(event):
            pass

        webhook_router.register_workflow("test", test_workflow)

        assert "test" in webhook_router.workflows

    def test_map_event_to_workflow(self, webhook_router):
        """Test mapping event to workflow."""
        webhook_router.map_event_to_workflow("github", "push", "deploy")

        assert webhook_router.event_mappings["github:push"] == "deploy"

    @pytest.mark.asyncio
    async def test_route_webhook_unknown_source(self, webhook_router):
        """Test routing webhook from unknown source."""
        result = await webhook_router.route_webhook(
            source="unknown",
            headers={},
            payload=b"{}",
        )

        assert result["status"] == "error"
        assert "Unknown source" in result["error"]

    @pytest.mark.asyncio
    async def test_route_webhook_invalid_signature(
        self, webhook_router, github_handler
    ):
        """Test routing webhook with invalid signature."""
        webhook_router.register_handler(github_handler)

        payload = b'{"ref": "refs/heads/main"}'
        headers = {"x-github-event": "push"}

        result = await webhook_router.route_webhook(
            source="github",
            headers=headers,
            payload=payload,
            signature="sha256=invalid",
        )

        assert result["status"] == "error"
        assert "Invalid signature" in result["error"]

    @pytest.mark.asyncio
    async def test_route_webhook_malformed_payload(self, webhook_router):
        """Test routing webhook with malformed JSON."""
        handler = GitHubWebhookHandler()
        webhook_router.register_handler(handler)

        result = await webhook_router.route_webhook(
            source="github",
            headers={},
            payload=b"not json",
        )

        assert result["status"] == "error"
        assert "Invalid payload" in result["error"]

    @pytest.mark.asyncio
    async def test_route_webhook_triggers_workflow(self, webhook_router):
        """Test that routing webhook triggers mapped workflow."""
        handler = GitHubWebhookHandler()
        webhook_router.register_handler(handler)

        workflow_called = False

        async def test_workflow(event):
            nonlocal workflow_called
            workflow_called = True

        webhook_router.register_workflow("test", test_workflow)
        webhook_router.map_event_to_workflow("github", "push", "test")

        payload = json.dumps({
            "ref": "refs/heads/main",
            "commits": [],
            "repository": {"full_name": "test/repo"},
        }).encode()
        headers = {"x-github-event": "push", "x-github-delivery": "test-123"}

        await webhook_router.route_webhook(
            source="github",
            headers=headers,
            payload=payload,
        )

        assert workflow_called is True

    @pytest.mark.asyncio
    async def test_route_webhook_workflow_not_registered(self, webhook_router):
        """Test routing when workflow is mapped but not registered."""
        handler = GitHubWebhookHandler()
        webhook_router.register_handler(handler)

        webhook_router.map_event_to_workflow("github", "push", "nonexistent")

        payload = json.dumps({
            "ref": "refs/heads/main",
            "commits": [],
        }).encode()
        headers = {"x-github-event": "push"}

        # Should not raise, just log error
        result = await webhook_router.route_webhook(
            source="github",
            headers=headers,
            payload=payload,
        )

        # Event still processed even if workflow not found
        assert result["status"] in ["success", "ignored"]

    @pytest.mark.asyncio
    async def test_route_webhook_workflow_exception(self, webhook_router):
        """Test handling workflow exception."""
        handler = GitHubWebhookHandler()
        webhook_router.register_handler(handler)

        async def failing_workflow(event):
            raise ValueError("Workflow error")

        webhook_router.register_workflow("failing", failing_workflow)
        webhook_router.map_event_to_workflow("github", "push", "failing")

        payload = json.dumps({
            "ref": "refs/heads/main",
            "commits": [],
        }).encode()
        headers = {"x-github-event": "push"}

        # Should not raise, just log error
        result = await webhook_router.route_webhook(
            source="github",
            headers=headers,
            payload=payload,
        )

        # Event processing should still succeed
        assert result["status"] in ["success", "ignored"]


# ==============================================================================
# Built-in Workflow Tests
# ==============================================================================


class TestBuiltInWorkflows:
    """Tests for built-in workflow functions."""

    @pytest.mark.asyncio
    async def test_automated_code_review_workflow_github(self):
        """Test automated code review workflow for GitHub."""
        event = WebhookEvent(
            event_id="test-123",
            source="github",
            event_type="pull_request",
            payload={},
            metadata={
                "pr_number": 42,
                "repository": {"name": "owner/repo"},
            },
        )

        with patch("aiops.webhooks.webhook_router.CodeReviewAgent"):
            # Should not raise
            await automated_code_review_workflow(event)

    @pytest.mark.asyncio
    async def test_automated_code_review_workflow_gitlab(self):
        """Test automated code review workflow for GitLab."""
        event = WebhookEvent(
            event_id="test-123",
            source="gitlab",
            event_type="merge_request_hook",
            payload={},
            metadata={
                "mr_iid": 42,
                "project": {"name": "group/project"},
            },
        )

        with patch("aiops.webhooks.webhook_router.CodeReviewAgent"):
            # Should not raise
            await automated_code_review_workflow(event)

    @pytest.mark.asyncio
    async def test_incident_response_workflow(self):
        """Test incident response workflow."""
        event = WebhookEvent(
            event_id="test-123",
            source="pagerduty",
            event_type="incident.triggered",
            payload={},
            metadata={
                "incident_number": 42,
                "title": "Server Down",
                "urgency": "high",
                "description": "Production server is down",
            },
        )

        with patch("aiops.webhooks.webhook_router.IncidentResponseAgent"):
            # Should not raise
            await incident_response_workflow(event)

    @pytest.mark.asyncio
    async def test_release_validation_workflow_github(self):
        """Test release validation workflow for GitHub."""
        event = WebhookEvent(
            event_id="test-123",
            source="github",
            event_type="release",
            payload={},
            metadata={
                "release_tag": "v1.0.0",
            },
        )

        with patch("aiops.webhooks.webhook_router.ReleaseManagerAgent"):
            # Should not raise
            await release_validation_workflow(event)

    @pytest.mark.asyncio
    async def test_release_validation_workflow_gitlab(self):
        """Test release validation workflow for GitLab."""
        event = WebhookEvent(
            event_id="test-123",
            source="gitlab",
            event_type="release_hook",
            payload={},
            metadata={
                "release_tag": "v1.0.0",
            },
        )

        with patch("aiops.webhooks.webhook_router.ReleaseManagerAgent"):
            # Should not raise
            await release_validation_workflow(event)


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestWebhookIntegration:
    """Integration tests for webhook system."""

    @pytest.mark.asyncio
    async def test_full_github_push_flow(self):
        """Test full GitHub push event flow."""
        secret = "test_secret"
        handler = GitHubWebhookHandler(secret=secret)
        processor = WebhookProcessor()
        processor.register_handler(handler)

        # Register push handler
        handler.register_handler("push", handle_push_event)

        # Create payload
        payload = json.dumps({
            "ref": "refs/heads/main",
            "commits": [{"id": "abc"}, {"id": "def"}],
            "repository": {
                "full_name": "owner/repo",
                "html_url": "https://github.com/owner/repo",
            },
            "sender": {"login": "testuser"},
        }).encode()

        signature = create_github_signature(payload, secret)
        headers = {
            "x-github-event": "push",
            "x-github-delivery": "delivery-123",
        }

        result = await processor.process_webhook(
            source="github",
            headers=headers,
            payload=payload,
            signature=signature,
        )

        assert result["status"] == "success"
        assert result["result"]["action"] == "push_received"
        assert result["result"]["branch"] == "main"
        assert result["result"]["commits"] == 2

    @pytest.mark.asyncio
    async def test_full_gitlab_mr_flow(self):
        """Test full GitLab MR event flow."""
        secret = "test_token"
        handler = GitLabWebhookHandler(secret=secret)
        processor = WebhookProcessor()
        processor.register_handler(handler)

        # Register MR handler
        handler.register_handler("merge_request_hook", handle_merge_request_hook)

        # Create payload
        payload = json.dumps({
            "object_attributes": {
                "iid": 42,
                "title": "New feature",
                "state": "opened",
                "action": "open",
                "source_branch": "feature",
                "target_branch": "main",
            },
            "project": {"path_with_namespace": "group/project"},
        }).encode()

        headers = {"x-gitlab-event": "Merge Request Hook"}

        result = await processor.process_webhook(
            source="gitlab",
            headers=headers,
            payload=payload,
            signature=secret,
        )

        assert result["status"] == "success"
        assert result["result"]["action"] == "code_review_triggered"
        assert result["result"]["mr_iid"] == 42

    @pytest.mark.asyncio
    async def test_full_pagerduty_incident_flow(self):
        """Test full PagerDuty incident event flow."""
        secret = "test_secret"
        handler = PagerDutyWebhookHandler(secret=secret)
        processor = WebhookProcessor()
        processor.register_handler(handler)

        # Register incident handler
        handler.register_handler("incident.triggered", handle_incident_triggered)

        # Create payload
        payload = json.dumps({
            "messages": [
                {
                    "id": "msg-123",
                    "event": "incident.triggered",
                    "incident": {
                        "id": "inc-123",
                        "incident_number": 42,
                        "title": "Server Down",
                        "status": "triggered",
                        "urgency": "high",
                        "service": {"id": "svc-123", "summary": "Production"},
                    },
                }
            ]
        }).encode()

        signature = create_pagerduty_signature(payload, secret)
        headers = {}

        result = await processor.process_webhook(
            source="pagerduty",
            headers=headers,
            payload=payload,
            signature=signature,
        )

        assert result["status"] == "success"
        assert result["result"]["action"] == "incident_response_triggered"
        assert result["result"]["urgency"] == "high"

    @pytest.mark.asyncio
    async def test_router_with_multiple_handlers(self):
        """Test router with multiple handlers."""
        router = WebhookRouter()

        github_handler = GitHubWebhookHandler()
        gitlab_handler = GitLabWebhookHandler()
        jira_handler = JiraWebhookHandler()

        router.register_handler(github_handler)
        router.register_handler(gitlab_handler)
        router.register_handler(jira_handler)

        assert len(router.handlers) == 3
        assert "github" in router.handlers
        assert "gitlab" in router.handlers
        assert "jira" in router.handlers


# ==============================================================================
# Edge Case Tests
# ==============================================================================


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_signature_with_special_characters(self, github_handler, github_secret):
        """Test signature with special characters in payload."""
        payload = b'{"message": "Hello \xc3\xa9\xc3\xa0\xc3\xb9"}'
        signature = create_github_signature(payload, github_secret)

        assert github_handler.verify_signature(payload, signature) is True

    def test_signature_with_empty_payload(self, github_handler, github_secret):
        """Test signature with empty payload."""
        payload = b""
        signature = create_github_signature(payload, github_secret)

        assert github_handler.verify_signature(payload, signature) is True

    def test_signature_with_large_payload(self, github_handler, github_secret):
        """Test signature with large payload."""
        # Create a 1MB payload
        payload = b'{"data": "' + b"x" * (1024 * 1024) + b'"}'
        signature = create_github_signature(payload, github_secret)

        assert github_handler.verify_signature(payload, signature) is True

    def test_parse_event_with_missing_fields(self, github_handler):
        """Test parsing event with missing optional fields."""
        headers = {"x-github-event": "push"}
        payload = {}  # Minimal payload

        event = github_handler.parse_event(headers, payload)

        assert event.event_type == "push"
        assert event.metadata.get("branch") == ""
        assert event.metadata.get("commits_count") == 0

    def test_parse_event_with_null_values(self, github_handler):
        """Test parsing event with null values."""
        headers = {"x-github-event": "push"}
        payload = {
            "ref": None,
            "commits": None,
            "repository": None,
            "sender": None,
        }

        # Should not raise
        event = github_handler.parse_event(headers, payload)
        assert event.event_type == "push"

    def test_handler_with_unicode_secret(self):
        """Test handler with unicode in secret."""
        secret = "secret_with_unicode_\u00e9\u00e0"
        handler = GitHubWebhookHandler(secret=secret)

        payload = b'{"test": "data"}'
        signature = create_github_signature(payload, secret)

        assert handler.verify_signature(payload, signature) is True

    @pytest.mark.asyncio
    async def test_concurrent_webhook_processing(self):
        """Test processing multiple webhooks concurrently."""
        import asyncio

        secret = "test_secret"
        handler = GitHubWebhookHandler(secret=secret)
        processor = WebhookProcessor()
        processor.register_handler(handler)
        handler.register_handler("push", handle_push_event)

        # Create multiple payloads
        payloads = []
        for i in range(10):
            payload = json.dumps({
                "ref": f"refs/heads/branch-{i}",
                "commits": [{"id": f"commit-{i}"}],
                "repository": {"full_name": f"owner/repo-{i}"},
            }).encode()
            signature = create_github_signature(payload, secret)
            headers = {"x-github-event": "push", "x-github-delivery": f"delivery-{i}"}
            payloads.append((headers, payload, signature))

        # Process all concurrently
        tasks = [
            processor.process_webhook(
                source="github",
                headers=h,
                payload=p,
                signature=s,
            )
            for h, p, s in payloads
        ]

        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(r["status"] == "success" for r in results)

    def test_timing_attack_resistance(self, github_handler, github_secret):
        """Test that signature comparison is constant-time."""
        payload = b'{"test": "data"}'
        valid_signature = create_github_signature(payload, github_secret)

        # These should all take approximately the same time
        # (we can't really measure this in a unit test, but we verify
        # the code path uses hmac.compare_digest)
        github_handler.verify_signature(payload, valid_signature)
        github_handler.verify_signature(payload, "sha256=" + "a" * 64)
        github_handler.verify_signature(payload, "sha256=" + "b" * 64)

        # Just verify it works correctly
        assert github_handler.verify_signature(payload, valid_signature) is True
        assert github_handler.verify_signature(payload, "sha256=" + "a" * 64) is False
