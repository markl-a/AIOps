"""Example 15: Webhook Integration System

This example demonstrates the webhook receiver system for integrating
with external services like GitHub, GitLab, Jira, and PagerDuty.
"""

import asyncio
import json
from typing import Dict, Any


async def github_webhook_example():
    """Demonstrate GitHub webhook handling"""
    from aiops.webhooks import GitHubWebhookHandler, WebhookRouter
    from aiops.webhooks.github_handler import (
        handle_push_event,
        handle_pull_request_event,
    )

    print("\n" + "=" * 70)
    print("🔗 GITHUB WEBHOOK EXAMPLE")
    print("=" * 70)

    # Initialize handler
    handler = GitHubWebhookHandler(secret="my-github-secret")

    # Register event handlers
    handler.register_handler("push", handle_push_event)
    handler.register_handler("pull_request", handle_pull_request_event)

    # Simulate GitHub pull request webhook
    print("\n📥 Simulating GitHub Pull Request Webhook")

    headers = {
        "x-github-event": "pull_request",
        "x-github-delivery": "12345-67890",
        "x-hub-signature-256": "sha256=...",  # Would be actual signature
    }

    payload = {
        "action": "opened",
        "number": 123,
        "pull_request": {
            "number": 123,
            "title": "Add new feature",
            "state": "open",
            "html_url": "https://github.com/owner/repo/pull/123",
            "base": {"ref": "main"},
            "head": {"ref": "feature/new-feature"},
            "mergeable": True,
            "merged": False,
        },
        "repository": {
            "full_name": "owner/repo",
            "html_url": "https://github.com/owner/repo",
            "default_branch": "main",
        },
        "sender": {
            "login": "developer",
            "type": "User",
        },
    }

    # Parse event
    event = handler.parse_event(headers, payload)

    print(f"\n  Event Type: {event.event_type}")
    print(f"  Event ID: {event.event_id}")
    print(f"  Repository: {event.metadata.get('repository', {}).get('name')}")
    print(f"  PR Number: #{event.metadata.get('pr_number')}")
    print(f"  PR Title: {event.metadata.get('pr_title')}")
    print(f"  Action: {event.metadata.get('pr_action')}")

    # Handle event
    result = await handler.handle_event(event)

    print(f"\n✅ Event Handled:")
    print(f"  Status: {result['status']}")
    print(f"  Result: {json.dumps(result['result'], indent=2)}")


async def gitlab_webhook_example():
    """Demonstrate GitLab webhook handling"""
    from aiops.webhooks import GitLabWebhookHandler
    from aiops.webhooks.gitlab_handler import handle_merge_request_hook

    print("\n" + "=" * 70)
    print("🔗 GITLAB WEBHOOK EXAMPLE")
    print("=" * 70)

    # Initialize handler
    handler = GitLabWebhookHandler(secret="my-gitlab-token")

    # Register event handler
    handler.register_handler("merge_request_hook", handle_merge_request_hook)

    # Simulate GitLab merge request webhook
    print("\n📥 Simulating GitLab Merge Request Webhook")

    headers = {
        "x-gitlab-event": "Merge Request Hook",
        "x-gitlab-token": "my-gitlab-token",
    }

    payload = {
        "object_kind": "merge_request",
        "object_attributes": {
            "iid": 42,
            "title": "Fix critical bug",
            "state": "opened",
            "action": "open",
            "url": "https://gitlab.com/group/project/-/merge_requests/42",
            "source_branch": "fix/critical-bug",
            "target_branch": "main",
            "merge_status": "can_be_merged",
        },
        "project": {
            "path_with_namespace": "group/project",
            "web_url": "https://gitlab.com/group/project",
            "default_branch": "main",
        },
        "user": {
            "username": "developer",
            "name": "Jane Developer",
        },
    }

    # Parse event
    event = handler.parse_event(headers, payload)

    print(f"\n  Event Type: {event.event_type}")
    print(f"  Project: {event.metadata.get('project', {}).get('name')}")
    print(f"  MR !{event.metadata.get('mr_iid')}")
    print(f"  Title: {event.metadata.get('mr_title')}")
    print(f"  Action: {event.metadata.get('mr_action')}")

    # Handle event
    result = await handler.handle_event(event)

    print(f"\n✅ Event Handled:")
    print(f"  Status: {result['status']}")
    print(f"  Result: {json.dumps(result['result'], indent=2)}")


async def pagerduty_webhook_example():
    """Demonstrate PagerDuty webhook handling"""
    from aiops.webhooks import PagerDutyWebhookHandler
    from aiops.webhooks.pagerduty_handler import handle_incident_triggered

    print("\n" + "=" * 70)
    print("🔗 PAGERDUTY WEBHOOK EXAMPLE")
    print("=" * 70)

    # Initialize handler
    handler = PagerDutyWebhookHandler(secret="my-pagerduty-secret")

    # Register event handler
    handler.register_handler("incident.triggered", handle_incident_triggered)

    # Simulate PagerDuty incident webhook
    print("\n📥 Simulating PagerDuty Incident Webhook")

    headers = {
        "x-pagerduty-signature": "v1=...",  # Would be actual signature
    }

    payload = {
        "messages": [
            {
                "id": "incident-123",
                "event": "incident.triggered",
                "incident": {
                    "id": "PD123",
                    "incident_number": 456,
                    "incident_key": "service-down",
                    "title": "Production API service down",
                    "description": "API service health check failing",
                    "status": "triggered",
                    "urgency": "high",
                    "priority": {
                        "summary": "P1",
                    },
                    "service": {
                        "id": "SVC123",
                        "summary": "Production API",
                    },
                    "assignments": [
                        {
                            "assignee": {
                                "summary": "On-Call Engineer",
                            }
                        }
                    ],
                    "created_at": "2025-01-19T10:00:00Z",
                    "updated_at": "2025-01-19T10:00:00Z",
                    "escalation_policy": {
                        "summary": "Production Escalation",
                    },
                }
            }
        ]
    }

    # Parse event
    event = handler.parse_event(headers, payload)

    print(f"\n  Event Type: {event.event_type}")
    print(f"  Incident: #{event.metadata.get('incident_number')}")
    print(f"  Title: {event.metadata.get('title')}")
    print(f"  Urgency: {event.metadata.get('urgency')}")
    print(f"  Service: {event.metadata.get('service', {}).get('name')}")

    # Handle event
    result = await handler.handle_event(event)

    print(f"\n✅ Event Handled:")
    print(f"  Status: {result['status']}")
    print(f"  Result: {json.dumps(result['result'], indent=2)}")


async def webhook_router_example():
    """Demonstrate webhook router with automated workflows"""
    from aiops.webhooks import WebhookRouter, GitHubWebhookHandler
    from aiops.webhooks.webhook_router import automated_code_review_workflow

    print("\n" + "=" * 70)
    print("🔀 WEBHOOK ROUTER WITH WORKFLOWS")
    print("=" * 70)

    # Initialize router
    router = WebhookRouter()

    # Initialize handler
    github_handler = GitHubWebhookHandler(secret="my-secret")

    # Register handler
    router.register_handler(github_handler)

    # Register workflow
    router.register_workflow("code_review", automated_code_review_workflow)

    # Map event to workflow
    router.map_event_to_workflow("github", "pull_request", "code_review")

    print("\n📊 Router Configuration:")
    print(f"  Handlers: {list(router.handlers.keys())}")
    print(f"  Workflows: {list(router.workflows.keys())}")
    print(f"  Event Mappings: {len(router.event_mappings)}")

    # Simulate webhook
    print("\n📥 Processing GitHub PR Webhook → Triggering Code Review Workflow")

    headers = {
        "x-github-event": "pull_request",
        "x-github-delivery": "123",
    }

    payload = {
        "action": "opened",
        "number": 789,
        "pull_request": {
            "number": 789,
            "title": "Refactor authentication module",
            "state": "open",
            "html_url": "https://github.com/owner/repo/pull/789",
            "base": {"ref": "main"},
            "head": {"ref": "refactor/auth"},
            "mergeable": True,
        },
        "repository": {
            "full_name": "owner/repo",
            "html_url": "https://github.com/owner/repo",
        },
        "sender": {
            "login": "developer",
        },
    }

    payload_bytes = json.dumps(payload).encode("utf-8")

    # Route webhook
    result = await router.route_webhook(
        source="github",
        headers=headers,
        payload=payload_bytes,
    )

    print(f"\n✅ Webhook Processed:")
    print(f"  Status: {result['status']}")
    print(f"  Event ID: {result.get('event_id', 'N/A')}")
    print(f"\n  ℹ️  Automated code review workflow was triggered in the background")


async def fastapi_webhook_usage_example():
    """Show how to use webhooks with FastAPI"""

    print("\n" + "=" * 70)
    print("🌐 FASTAPI WEBHOOK ENDPOINTS")
    print("=" * 70)

    print("""
The AIOps API provides webhook endpoints for various services:

1. GitHub Webhooks:
   POST /api/v1/webhooks/github

   Configure in GitHub:
   - URL: https://your-domain.com/api/v1/webhooks/github
   - Content type: application/json
   - Secret: Set GITHUB_WEBHOOK_SECRET env var
   - Events: Choose specific events (push, pull_request, issues, etc.)

2. GitLab Webhooks:
   POST /api/v1/webhooks/gitlab

   Configure in GitLab:
   - URL: https://your-domain.com/api/v1/webhooks/gitlab
   - Secret Token: Set GITLAB_WEBHOOK_SECRET env var
   - Trigger: Push events, Merge request events, Pipeline events, etc.

3. Jira Webhooks:
   POST /api/v1/webhooks/jira

   Configure in Jira:
   - URL: https://your-domain.com/api/v1/webhooks/jira
   - Events: Issue created, updated, commented, etc.

4. PagerDuty Webhooks:
   POST /api/v1/webhooks/pagerduty

   Configure in PagerDuty:
   - URL: https://your-domain.com/api/v1/webhooks/pagerduty
   - Webhook version: v3
   - Events: Incident triggered, acknowledged, resolved, etc.

Example curl request:
```bash
curl -X POST https://your-domain.com/api/v1/webhooks/github \\
  -H "X-GitHub-Event: pull_request" \\
  -H "X-Hub-Signature-256: sha256=..." \\
  -H "X-GitHub-Delivery: abc-123" \\
  -H "Content-Type: application/json" \\
  -d @webhook-payload.json
```

Check webhook status:
```bash
curl https://your-domain.com/api/v1/webhooks/status
```
""")


async def main():
    """Run all webhook examples"""
    print("\n" + "=" * 70)
    print("🔗 WEBHOOK INTEGRATION SYSTEM")
    print("=" * 70)
    print("\nDemonstrates webhook receivers for external service integration")

    try:
        # Run examples
        await github_webhook_example()
        await gitlab_webhook_example()
        await pagerduty_webhook_example()
        await webhook_router_example()
        await fastapi_webhook_usage_example()

        print("\n" + "=" * 70)
        print("✅ ALL WEBHOOK EXAMPLES COMPLETED")
        print("=" * 70)

        print("\n📚 Key Features:")
        print("  • Signature verification for security")
        print("  • Standardized event parsing across services")
        print("  • Event routing to specialized handlers")
        print("  • Automated workflow triggering")
        print("  • FastAPI integration with background tasks")

        print("\n🔧 Automated Workflows:")
        print("  • Code Review: Triggered on PR/MR creation")
        print("  • Incident Response: Triggered on high-urgency incidents")
        print("  • Release Validation: Triggered on release publication")
        print("  • Custom workflows can be easily added")

        print("\n💡 Next Steps:")
        print("  1. Configure webhook secrets in environment variables")
        print("  2. Set up webhooks in external services")
        print("  3. Monitor webhook processing via logs/metrics")
        print("  4. Create custom workflows for your use cases")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
