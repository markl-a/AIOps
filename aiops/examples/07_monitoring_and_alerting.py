"""Example 7: Monitoring and Alerting Integration

This example demonstrates how to integrate AIOps with monitoring systems.
"""

import asyncio
import json
from datetime import datetime, timedelta
from aiops.agents.anomaly_detector import AnomalyDetectorAgent
from aiops.agents.intelligent_monitor import IntelligentMonitorAgent
from aiops.observability.metrics import MetricsCollector


async def detect_anomalies_in_metrics():
    """Detect anomalies in system metrics."""

    print("📊 Anomaly Detection in Metrics")
    print("="*60)

    # Mock time series data (normally from Prometheus)
    timestamps = [
        (datetime.now() - timedelta(minutes=60-i)).isoformat()
        for i in range(60)
    ]

    # Simulated metrics with anomaly at index 45
    cpu_values = [45.2, 47.1, 46.8, 48.3, 47.5] * 9  # Normal
    cpu_values[45] = 95.5  # Anomaly!

    metrics_data = {
        "timestamps": timestamps,
        "values": cpu_values,
        "metric_name": "cpu_usage_percent",
    }

    print(f"\n📈 Analyzing metric: {metrics_data['metric_name']}")
    print(f"Data points: {len(metrics_data['values'])}")

    # Detect anomalies
    detector = AnomalyDetectorAgent()
    result = await detector.execute(
        metrics=metrics_data,
        detection_method="statistical"
    )

    print(f"\n🔍 Detection Results:")
    print(f"  Anomalies Detected: {result.total_anomalies}")
    print(f"  Critical: {result.critical_anomalies}")
    print(f"  High Severity: {result.high_severity_anomalies}")
    print(f"  Detection Confidence: {result.detection_confidence:.2%}")

    # Show anomalies
    if result.anomalies:
        print(f"\n⚠️  Anomalies Found:")
        for anomaly in result.anomalies:
            print(f"\n  Type: {anomaly.type}")
            print(f"  Severity: {anomaly.severity}")
            print(f"  Timestamp: {anomaly.timestamp}")
            print(f"  Value: {anomaly.value} (baseline: {anomaly.baseline_value})")
            print(f"  Deviation: {anomaly.deviation_percent:.1f}%")
            print(f"  Confidence: {anomaly.confidence:.2%}")
            print(f"  Description: {anomaly.description}")

            if hasattr(anomaly, 'possible_causes') and anomaly.possible_causes:
                print(f"  Possible Causes:")
                for cause in anomaly.possible_causes:
                    print(f"    - {cause}")

    return result


async def intelligent_monitoring_example():
    """Example of intelligent monitoring with auto-response."""

    print("\n🤖 Intelligent Monitoring System")
    print("="*60)

    # Mock current metrics
    current_metrics = {
        "cpu_usage": 85.2,
        "memory_usage": 78.5,
        "disk_usage": 92.1,
        "network_latency_ms": 250,
        "error_rate": 0.05,
        "request_count": 1500,
    }

    # Mock baseline (healthy state)
    baseline_metrics = {
        "cpu_usage": 45.0,
        "memory_usage": 60.0,
        "disk_usage": 65.0,
        "network_latency_ms": 50,
        "error_rate": 0.01,
        "request_count": 1000,
    }

    print("\n📊 Current System State:")
    for metric, value in current_metrics.items():
        baseline = baseline_metrics.get(metric, 0)
        deviation = ((value - baseline) / baseline * 100) if baseline else 0
        status = "⚠️ " if abs(deviation) > 50 else "✅"
        print(f"  {status} {metric}: {value} (baseline: {baseline}, {deviation:+.1f}%)")

    # Analyze with intelligent monitor
    monitor = IntelligentMonitorAgent()
    result = await monitor.execute(
        current_metrics=current_metrics,
        baseline_metrics=baseline_metrics
    )

    print(f"\n🔔 Alert Status: {result.alert_level}")
    print(f"📊 Health Score: {result.health_score}/100")

    # Show alerts
    if hasattr(result, 'alerts') and result.alerts:
        print(f"\n🚨 Active Alerts:")
        for alert in result.alerts:
            print(f"\n  [{alert.severity}] {alert.metric}")
            print(f"  Description: {alert.description}")
            if hasattr(alert, 'recommended_action'):
                print(f"  Recommended Action: {alert.recommended_action}")

    # Show recommendations
    if hasattr(result, 'recommendations') and result.recommendations:
        print(f"\n💡 Recommendations:")
        for i, rec in enumerate(result.recommendations, 1):
            print(f"  {i}. {rec}")


async def create_custom_alert_rules():
    """Example of creating custom alert rules."""

    print("\n📋 Custom Alert Rules")
    print("="*60)

    alert_rules = {
        "high_cpu": {
            "metric": "cpu_usage",
            "threshold": 80,
            "duration": "5m",
            "severity": "warning",
            "action": "scale_up",
            "notification": ["slack", "email"],
        },
        "critical_memory": {
            "metric": "memory_usage",
            "threshold": 90,
            "duration": "2m",
            "severity": "critical",
            "action": "restart_pod",
            "notification": ["pagerduty", "slack"],
        },
        "high_error_rate": {
            "metric": "error_rate",
            "threshold": 0.05,  # 5%
            "duration": "1m",
            "severity": "critical",
            "action": "rollback_deployment",
            "notification": ["pagerduty", "slack", "email"],
        },
        "disk_space_low": {
            "metric": "disk_usage",
            "threshold": 85,
            "duration": "10m",
            "severity": "warning",
            "action": "cleanup_old_logs",
            "notification": ["slack"],
        },
    }

    print("\nConfigured Alert Rules:")
    for rule_name, rule in alert_rules.items():
        print(f"\n  📌 {rule_name}")
        print(f"     Metric: {rule['metric']}")
        print(f"     Threshold: {rule['threshold']}")
        print(f"     Duration: {rule['duration']}")
        print(f"     Severity: {rule['severity']}")
        print(f"     Action: {rule['action']}")
        print(f"     Notifications: {', '.join(rule['notification'])}")

    # Example: Prometheus alert rule format
    print("\n📝 Prometheus Alert Rule (YAML):")
    print("""
    groups:
      - name: aiops_alerts
        rules:
          - alert: HighCPUUsage
            expr: cpu_usage > 80
            for: 5m
            labels:
              severity: warning
            annotations:
              summary: "High CPU usage detected"
              description: "CPU usage is {{ $value }}%"

          - alert: CriticalMemoryUsage
            expr: memory_usage > 90
            for: 2m
            labels:
              severity: critical
            annotations:
              summary: "Critical memory usage"
              description: "Memory usage is {{ $value }}%"

          - alert: HighErrorRate
            expr: rate(errors_total[5m]) > 0.05
            for: 1m
            labels:
              severity: critical
            annotations:
              summary: "High error rate detected"
              description: "Error rate is {{ $value }}"
    """)


async def send_notifications(alert_data: dict):
    """Example of sending alert notifications."""

    print("\n📬 Sending Notifications")
    print("="*60)

    # Slack notification
    print("\n💬 Slack Notification:")
    slack_message = {
        "channel": "#alerts",
        "username": "AIOps Monitor",
        "icon_emoji": ":robot_face:",
        "attachments": [
            {
                "color": "danger" if alert_data["severity"] == "critical" else "warning",
                "title": f"🚨 {alert_data['title']}",
                "text": alert_data['description'],
                "fields": [
                    {
                        "title": "Severity",
                        "value": alert_data['severity'],
                        "short": True
                    },
                    {
                        "title": "Metric",
                        "value": alert_data['metric'],
                        "short": True
                    },
                    {
                        "title": "Value",
                        "value": alert_data['value'],
                        "short": True
                    },
                    {
                        "title": "Threshold",
                        "value": alert_data['threshold'],
                        "short": True
                    },
                ],
                "footer": "AIOps Monitoring",
                "ts": int(datetime.now().timestamp())
            }
        ]
    }

    print(json.dumps(slack_message, indent=2))

    # Email notification
    print("\n📧 Email Notification:")
    email_content = f"""
    Subject: 🚨 [{alert_data['severity'].upper()}] {alert_data['title']}

    Alert Details:
    --------------
    Severity: {alert_data['severity']}
    Metric: {alert_data['metric']}
    Current Value: {alert_data['value']}
    Threshold: {alert_data['threshold']}

    Description:
    {alert_data['description']}

    Recommended Actions:
    {alert_data.get('action', 'Review system metrics')}

    --
    Generated by AIOps Monitoring System
    Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
    """

    print(email_content)

    # Example: Actually send notifications
    print("\n🔄 To send real notifications:")
    print("""
    import requests

    # Slack Webhook
    slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
    requests.post(slack_webhook, json=slack_message)

    # Email (using SendGrid)
    import sendgrid
    sg = sendgrid.SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
    message = Mail(
        from_email='alerts@aiops.com',
        to_emails='team@company.com',
        subject=f"[{alert_data['severity']}] {alert_data['title']}",
        html_content=email_content
    )
    sg.send(message)

    # PagerDuty
    pagerduty_api_key = os.getenv("PAGERDUTY_API_KEY")
    pagerduty_service_id = os.getenv("PAGERDUTY_SERVICE_ID")
    # ... trigger incident
    """)


if __name__ == "__main__":
    print("🔔 Monitoring and Alerting Examples")
    print("="*60)

    # Run examples
    asyncio.run(detect_anomalies_in_metrics())

    print("\n" + "="*60)
    asyncio.run(intelligent_monitoring_example())

    print("\n" + "="*60)
    asyncio.run(create_custom_alert_rules())

    # Example alert
    sample_alert = {
        "title": "High CPU Usage Detected",
        "severity": "critical",
        "metric": "cpu_usage",
        "value": "95.5%",
        "threshold": "80%",
        "description": "CPU usage has exceeded threshold for 5 minutes",
        "action": "Consider scaling up resources or investigating processes",
    }

    print("\n" + "="*60)
    asyncio.run(send_notifications(sample_alert))

    print("\n✅ Monitoring examples complete!\n")
