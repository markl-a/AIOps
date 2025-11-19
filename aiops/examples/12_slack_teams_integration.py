"""Example 12: Slack and Teams Integration

This example demonstrates how to send notifications and alerts to Slack and
Microsoft Teams.
"""

import asyncio
import os
from datetime import datetime

from aiops.integrations.slack import (
    SlackNotifier,
    SlackClient,
    create_code_review_message,
    create_deployment_message,
)
from aiops.integrations.teams import (
    TeamsNotifier,
    create_code_review_card,
    create_deployment_card,
    create_alert_card,
    create_metric_card,
)
from aiops.integrations.notifications import (
    NotificationManager,
    Notification,
    NotificationLevel,
    NotificationChannel,
)


async def slack_webhook_example():
    """Example of sending messages via Slack webhook."""

    print("💬 Slack Webhook Integration")
    print("="*60)

    # Get webhook URL from environment
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    if not webhook_url:
        print("\n⚠️  SLACK_WEBHOOK_URL not set. Using mock example.\n")
        print("To use real Slack integration:")
        print("1. Create a Slack app at https://api.slack.com/apps")
        print("2. Enable Incoming Webhooks")
        print("3. Set SLACK_WEBHOOK_URL environment variable")
        return

    notifier = SlackNotifier(webhook_url)

    # Example 1: Simple message
    print("\n📤 Sending simple message...")
    try:
        await notifier.send_simple_message(
            text="🤖 AIOps is now running!",
            username="AIOps Bot",
            icon_emoji=":robot_face:",
        )
        print("✅ Message sent successfully")
    except Exception as e:
        print(f"❌ Failed to send message: {e}")

    # Example 2: Rich message
    print("\n📤 Sending rich formatted message...")
    try:
        await notifier.send_rich_message(
            title="Deployment Successful",
            message="Application deployed to production successfully",
            color="#2eb886",  # Green
            fields=[
                {"title": "Environment", "value": "Production", "short": True},
                {"title": "Version", "value": "v1.2.3", "short": True},
            ],
        )
        print("✅ Rich message sent successfully")
    except Exception as e:
        print(f"❌ Failed to send rich message: {e}")

    # Example 3: Code review notification
    print("\n📤 Sending code review notification...")
    try:
        message = create_code_review_message(
            pr_number=123,
            score=87.5,
            issues_count=5,
            critical_issues=0,
            file_count=12,
        )
        await notifier.send_message(message)
        print("✅ Code review notification sent")
    except Exception as e:
        print(f"❌ Failed to send code review: {e}")

    # Example 4: Deployment notification
    print("\n📤 Sending deployment notification...")
    try:
        message = create_deployment_message(
            environment="production",
            version="v1.2.3",
            status="success",
            duration_seconds=145.2,
        )
        await notifier.send_message(message)
        print("✅ Deployment notification sent")
    except Exception as e:
        print(f"❌ Failed to send deployment notification: {e}")


async def slack_bot_example():
    """Example of using Slack Bot API."""

    print("\n\n🤖 Slack Bot API Integration")
    print("="*60)

    bot_token = os.getenv("SLACK_BOT_TOKEN")

    if not bot_token:
        print("\n⚠️  SLACK_BOT_TOKEN not set. Using mock example.\n")
        print("To use real Slack Bot:")
        print("1. Create a Slack app")
        print("2. Add Bot Token Scopes (chat:write, channels:read, etc.)")
        print("3. Install app to workspace")
        print("4. Set SLACK_BOT_TOKEN environment variable")
        return

    client = SlackClient(bot_token)

    # Example 1: Post message to channel
    print("\n📤 Posting message to channel...")
    try:
        response = await client.post_message(
            channel="#general",
            text="Hello from AIOps!",
        )
        print(f"✅ Message posted with timestamp: {response.get('ts')}")

        # Add reaction to the message
        if response.get('ts'):
            await client.add_reaction(
                channel="#general",
                timestamp=response['ts'],
                name="robot_face",
            )
            print("✅ Reaction added")

    except Exception as e:
        print(f"❌ Failed to post message: {e}")

    # Example 2: List channels
    print("\n📋 Listing channels...")
    try:
        channels = await client.list_channels()
        print(f"✅ Found {len(channels)} channels:")
        for channel in channels[:5]:  # Show first 5
            print(f"   • {channel.get('name')}")
    except Exception as e:
        print(f"❌ Failed to list channels: {e}")


async def teams_webhook_example():
    """Example of sending messages via Teams webhook."""

    print("\n\n💼 Microsoft Teams Webhook Integration")
    print("="*60)

    webhook_url = os.getenv("TEAMS_WEBHOOK_URL")

    if not webhook_url:
        print("\n⚠️  TEAMS_WEBHOOK_URL not set. Using mock example.\n")
        print("To use real Teams integration:")
        print("1. Open Teams channel")
        print("2. Click '...' > Connectors > Incoming Webhook")
        print("3. Configure webhook and copy URL")
        print("4. Set TEAMS_WEBHOOK_URL environment variable")
        return

    notifier = TeamsNotifier(webhook_url)

    # Example 1: Simple message
    print("\n📤 Sending simple message...")
    try:
        await notifier.send_simple_message(
            title="AIOps Alert",
            text="System is running normally",
        )
        print("✅ Message sent successfully")
    except Exception as e:
        print(f"❌ Failed to send message: {e}")

    # Example 2: Formatted notification
    print("\n📤 Sending formatted notification...")
    try:
        await notifier.send_notification(
            title="High CPU Usage Detected",
            message="CPU usage has exceeded 80% for the last 5 minutes",
            severity="warning",
            facts=[
                {"title": "Current CPU", "value": "85%"},
                {"title": "Threshold", "value": "80%"},
                {"title": "Server", "value": "prod-server-01"},
            ],
        )
        print("✅ Notification sent successfully")
    except Exception as e:
        print(f"❌ Failed to send notification: {e}")

    # Example 3: Code review card
    print("\n📤 Sending code review card...")
    try:
        card = create_code_review_card(
            pr_number=123,
            score=87.5,
            issues_count=5,
            critical_issues=0,
            file_count=12,
            pr_url="https://github.com/org/repo/pull/123",
        )
        await notifier.send_adaptive_card(card)
        print("✅ Code review card sent")
    except Exception as e:
        print(f"❌ Failed to send code review card: {e}")

    # Example 4: Deployment card
    print("\n📤 Sending deployment card...")
    try:
        card = create_deployment_card(
            environment="production",
            version="v1.2.3",
            status="success",
            duration_seconds=145.2,
            deployed_by="DevOps Team",
        )
        await notifier.send_adaptive_card(card)
        print("✅ Deployment card sent")
    except Exception as e:
        print(f"❌ Failed to send deployment card: {e}")

    # Example 5: Alert card
    print("\n📤 Sending alert card...")
    try:
        card = create_alert_card(
            title="Database Connection Pool Exhausted",
            message="All database connections are in use. New requests are being queued.",
            severity="critical",
            affected_system="PostgreSQL Database",
            incident_url="https://monitoring.example.com/incidents/123",
        )
        await notifier.send_adaptive_card(card)
        print("✅ Alert card sent")
    except Exception as e:
        print(f"❌ Failed to send alert card: {e}")

    # Example 6: Metric card
    print("\n📤 Sending metric card...")
    try:
        card = create_metric_card(
            metric_name="API Response Time",
            current_value=1250.5,
            threshold=1000.0,
            trend="up",
            unit="ms",
        )
        await notifier.send_adaptive_card(card)
        print("✅ Metric card sent")
    except Exception as e:
        print(f"❌ Failed to send metric card: {e}")


async def unified_notification_example():
    """Example of using unified notification manager."""

    print("\n\n🔔 Unified Notification Manager")
    print("="*60)

    # Create notification manager
    manager = NotificationManager()

    # Register channels (mocked for demonstration)
    print("\n⚙️  Registering notification channels...")
    print("   • Console (for demonstration)")

    # For demonstration, we'll just use console
    from aiops.integrations.notifications import NotificationChannel

    class MockChannel:
        async def send_message(self, msg):
            print(f"   📨 Mock channel received message")

    manager.register_channel(NotificationChannel.CONSOLE, MockChannel())

    # Send different types of notifications
    print("\n📤 Sending INFO notification...")
    notification1 = Notification(
        title="System Started",
        message="AIOps system has started successfully",
        level=NotificationLevel.INFO,
        channels=[NotificationChannel.CONSOLE],
        metadata={
            "version": "1.2.3",
            "environment": "production",
        },
        tags=["startup", "system"],
    )
    await manager.send(notification1)

    print("\n📤 Sending WARNING notification...")
    notification2 = Notification(
        title="High Memory Usage",
        message="Memory usage is at 85%, approaching threshold",
        level=NotificationLevel.WARNING,
        channels=[NotificationChannel.CONSOLE],
        metadata={
            "current_memory": "85%",
            "threshold": "90%",
            "server": "prod-01",
        },
        tags=["performance", "memory"],
    )
    await manager.send(notification2)

    print("\n📤 Sending ERROR notification...")
    notification3 = Notification(
        title="Database Connection Failed",
        message="Unable to connect to PostgreSQL database",
        level=NotificationLevel.ERROR,
        channels=[NotificationChannel.CONSOLE],
        metadata={
            "database": "postgres://prod-db:5432",
            "error": "Connection refused",
        },
        tags=["database", "error"],
    )
    await manager.send(notification3)

    print("\n📤 Sending CRITICAL notification...")
    notification4 = Notification(
        title="Service Down",
        message="API service is not responding",
        level=NotificationLevel.CRITICAL,
        channels=[NotificationChannel.CONSOLE],
        metadata={
            "service": "aiops-api",
            "last_heartbeat": "2 minutes ago",
        },
        tags=["outage", "critical"],
    )
    await manager.send(notification4)

    # Show recent notifications
    print("\n\n📊 Recent Notifications:")
    recent = manager.get_recent_notifications(limit=5)
    for i, notif in enumerate(recent, 1):
        print(f"  {i}. [{notif.level.upper()}] {notif.title}")

    # Show only critical notifications
    print("\n\n🚨 Critical Notifications:")
    critical = manager.get_recent_notifications(
        limit=10,
        level=NotificationLevel.CRITICAL,
    )
    if critical:
        for notif in critical:
            print(f"  • {notif.title}: {notif.message}")
    else:
        print("  None")


async def real_world_scenario():
    """Demonstrate real-world notification scenarios."""

    print("\n\n🌍 Real-World Notification Scenarios")
    print("="*60)

    manager = NotificationManager()

    # Scenario 1: Code Review Completed
    print("\n📝 Scenario 1: Code Review Completed")
    print("-" * 60)

    await manager.send_alert(
        title="Code Review Completed",
        message="PR #123 has been reviewed and is ready for merge",
        level=NotificationLevel.SUCCESS,
        channels=[NotificationChannel.CONSOLE],
        pr_number=123,
        reviewer="AI Agent",
        score=87.5,
        issues_found=5,
    )

    # Scenario 2: Deployment Started
    print("\n🚀 Scenario 2: Deployment Started")
    print("-" * 60)

    await manager.send_alert(
        title="Deployment Started",
        message="Deploying version v1.2.3 to production",
        level=NotificationLevel.INFO,
        channels=[NotificationChannel.CONSOLE],
        environment="production",
        version="v1.2.3",
        triggered_by="DevOps Team",
    )

    # Scenario 3: Security Vulnerability Detected
    print("\n🔒 Scenario 3: Security Vulnerability Detected")
    print("-" * 60)

    await manager.send_alert(
        title="Critical Security Vulnerability",
        message="SQL Injection vulnerability detected in authentication module",
        level=NotificationLevel.CRITICAL,
        channels=[NotificationChannel.CONSOLE],
        vulnerability_type="SQL Injection",
        severity="CRITICAL",
        affected_file="auth/login.py",
        cve="CVE-2024-1234",
    )

    # Scenario 4: Performance Degradation
    print("\n⚡ Scenario 4: Performance Degradation")
    print("-" * 60)

    await manager.send_alert(
        title="Performance Degradation Detected",
        message="API response time has increased by 150% in the last hour",
        level=NotificationLevel.WARNING,
        channels=[NotificationChannel.CONSOLE],
        endpoint="/api/v1/users",
        current_p95="1500ms",
        baseline_p95="600ms",
        increase="150%",
    )


if __name__ == "__main__":
    print("💬 Slack & Teams Integration Examples")
    print("="*60)

    # Run examples
    asyncio.run(slack_webhook_example())
    asyncio.run(slack_bot_example())
    asyncio.run(teams_webhook_example())
    asyncio.run(unified_notification_example())
    asyncio.run(real_world_scenario())

    print("\n\n" + "="*60)
    print("✅ All integration examples complete!")
    print("="*60)

    print("\n📚 Next Steps:")
    print("  1. Set up Slack/Teams webhooks")
    print("  2. Configure environment variables")
    print("  3. Integrate with your CI/CD pipeline")
    print("  4. Set up alerting rules")
    print("\n")
