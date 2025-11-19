"""Example 14: Advanced DevOps Agents

This example demonstrates the advanced DevOps agents:
- Incident Response Agent
- Compliance Checker Agent
- Migration Planner Agent
- Release Manager Agent
"""

import asyncio
from datetime import datetime, timedelta


async def incident_response_example():
    """Demonstrate Incident Response Agent"""
    from aiops.agents import IncidentResponseAgent

    print("\n" + "=" * 70)
    print("🚨 INCIDENT RESPONSE AGENT")
    print("=" * 70)

    agent = IncidentResponseAgent()

    # Simulate incident data
    incident_data = {
        "incident_id": "INC-20250119-001",
        "title": "Database Connection Pool Exhausted",
        "severity": "critical",
        "description": "Production database connection pool exhausted, causing 500 errors",
        "affected_services": ["api-service", "auth-service", "payment-service"],
        "started_at": (datetime.now() - timedelta(minutes=15)).isoformat(),
    }

    logs = [
        "[ERROR] Failed to acquire database connection from pool",
        "[ERROR] Connection timeout after 30s",
        "[WARN] Connection pool utilization: 100%",
        "[ERROR] Too many open connections: 500/500",
        "[INFO] New API requests queued: 1250",
    ]

    metrics = {
        "db_connections": {
            "max": 500,
            "active": 500,
            "idle": 0,
            "waiting": 250,
        },
        "api_latency_ms": {
            "p50": 5000,
            "p95": 30000,
            "p99": 60000,
        },
        "error_rate": 0.45,  # 45% error rate
    }

    alerts = [
        {"severity": "critical", "name": "DBConnectionPoolExhausted", "message": "All connections in use"},
        {"severity": "high", "name": "HighAPILatency", "message": "P95 latency > 10s"},
        {"severity": "high", "name": "HighErrorRate", "message": "Error rate > 10%"},
    ]

    print("\n📊 Analyzing Incident...")
    print(f"  ID: {incident_data['incident_id']}")
    print(f"  Title: {incident_data['title']}")
    print(f"  Severity: {incident_data['severity'].upper()}")
    print(f"  Affected Services: {', '.join(incident_data['affected_services'])}")

    # Analyze incident
    result = await agent.execute(
        incident_data=incident_data,
        logs=logs,
        metrics=metrics,
        alerts=alerts,
    )

    print(f"\n🔍 Root Cause Analysis:")
    print(f"  Cause: {result.root_cause.likely_cause}")
    print(f"  Confidence: {result.root_cause.confidence}%")
    print(f"\n  Contributing Factors:")
    for factor in result.root_cause.contributing_factors:
        print(f"    • {factor}")

    print(f"\n🔧 Remediation Steps ({len(result.remediation_steps)} steps):")
    for step in result.remediation_steps[:3]:  # Show first 3 steps
        print(f"  {step.step_number}. [{step.risk_level.upper()}] {step.action}")
        if step.command:
            print(f"     Command: {step.command}")
        print(f"     Expected: {step.expected_result}")

    print(f"\n🛡️  Prevention Measures:")
    for measure in result.prevention_measures[:3]:
        print(f"    • {measure}")

    print(f"\n📋 Executive Summary:")
    print(f"  {result.executive_summary}")

    # Generate postmortem
    print(f"\n📝 Generating Postmortem Report...")
    postmortem = await agent.generate_postmortem(
        incident_analysis=result,
        resolution_notes="Increased connection pool size from 500 to 2000. Implemented connection pooling improvements.",
    )
    print("  ✅ Postmortem report generated (saved to incident_postmortem.md)")


async def compliance_checker_example():
    """Demonstrate Compliance Checker Agent"""
    from aiops.agents import ComplianceCheckerAgent

    print("\n" + "=" * 70)
    print("🔒 COMPLIANCE CHECKER AGENT")
    print("=" * 70)

    agent = ComplianceCheckerAgent()

    # Infrastructure configuration
    infrastructure_config = {
        "cloud": "AWS",
        "regions": ["us-east-1", "us-west-2"],
        "kubernetes": {
            "version": "1.28",
            "encryption_at_rest": True,
            "rbac_enabled": True,
            "network_policies": True,
        },
        "databases": [
            {
                "type": "PostgreSQL",
                "version": "15",
                "encryption": True,
                "backup_retention_days": 30,
            }
        ],
    }

    # Access policies
    access_policies = {
        "mfa_required": True,
        "password_policy": {
            "min_length": 12,
            "complexity_required": True,
            "rotation_days": 90,
        },
        "rbac": True,
        "principle_of_least_privilege": True,
    }

    # Encryption configuration
    encryption_config = {
        "data_at_rest": {
            "databases": "AES-256",
            "storage": "AES-256",
        },
        "data_in_transit": {
            "tls_version": "1.3",
            "certificates": "Let's Encrypt",
        },
    }

    # Audit logging
    logging_config = {
        "enabled": True,
        "log_types": ["access", "admin", "data_access", "authentication"],
        "retention_days": 365,
        "immutable": True,
    }

    print("\n📋 Checking Compliance...")
    print("  Standards: SOC2, HIPAA, GDPR")
    print("  Environment: production")

    # Check compliance
    report = await agent.execute(
        environment="production",
        standards=["SOC2", "HIPAA", "GDPR"],
        infrastructure_config=infrastructure_config,
        access_policies=access_policies,
        encryption_config=encryption_config,
        logging_config=logging_config,
    )

    print(f"\n📊 Compliance Scores:")
    print(f"  Overall: {report.overall_score}%")
    for score in report.scores_by_standard:
        print(f"  {score.standard}: {score.score}% ({score.passing_controls}/{score.total_controls} controls passing)")

    print(f"\n⚠️  Violations Found: {len(report.violations)}")
    print(f"  Critical: {report.critical_violations}")

    if report.violations:
        print(f"\n  Top Violations:")
        for violation in report.violations[:3]:
            print(f"    • [{violation.severity.upper()}] {violation.rule_id}")
            print(f"      {violation.description}")
            print(f"      Remediation: {violation.remediation}")

    print(f"\n💡 Recommendations ({len(report.recommendations)}):")
    for rec in report.recommendations[:3]:
        print(f"    • {rec}")

    print(f"\n📅 Next Review: {report.next_review_date}")

    # Generate remediation plan
    print(f"\n📋 Generating Remediation Plan...")
    remediation_plan = await agent.generate_remediation_plan(
        compliance_report=report,
        timeline_weeks=12,
    )
    print("  ✅ 12-week remediation plan generated")


async def migration_planner_example():
    """Demonstrate Migration Planner Agent"""
    from aiops.agents import MigrationPlannerAgent

    print("\n" + "=" * 70)
    print("🚀 MIGRATION PLANNER AGENT")
    print("=" * 70)

    agent = MigrationPlannerAgent()

    # Source environment (on-premises)
    source_environment = {
        "platform": "On-Premises Data Center",
        "compute": "VMware vSphere",
        "databases": "Oracle 19c, PostgreSQL 13",
        "storage": "NetApp NAS 50TB",
        "applications": [
            "Web Application (Java Spring Boot)",
            "API Gateway (NGINX)",
            "Background Workers (Python Celery)",
        ],
        "users": 100000,
        "monthly_traffic": "10TB",
    }

    # Target environment (AWS)
    target_environment = {
        "platform": "AWS Cloud",
        "compute": "EKS (Kubernetes)",
        "databases": "RDS PostgreSQL 15, Aurora",
        "storage": "S3 + EFS",
        "applications": [
            "Web Application (containerized)",
            "API Gateway (AWS API Gateway + ALB)",
            "Background Workers (containerized)",
        ],
        "target_regions": ["us-east-1", "us-west-2"],
    }

    # Constraints
    constraints = {
        "max_downtime_hours": 4,
        "budget_usd": 200000,
        "timeline_weeks": 16,
        "must_maintain_compliance": ["SOC2", "HIPAA"],
    }

    # Business requirements
    business_requirements = {
        "sla_uptime": "99.95%",
        "sla_latency_ms": 200,
        "data_residency": "US only",
        "disaster_recovery_rto_hours": 4,
        "disaster_recovery_rpo_hours": 1,
    }

    print("\n📋 Planning Migration...")
    print(f"  Type: Cloud Migration (On-Prem → AWS)")
    print(f"  Timeline: {constraints['timeline_weeks']} weeks")
    print(f"  Budget: ${constraints['budget_usd']:,}")
    print(f"  Max Downtime: {constraints['max_downtime_hours']} hours")

    # Create migration plan
    plan = await agent.execute(
        migration_type="cloud-migration",
        source_environment=source_environment,
        target_environment=target_environment,
        constraints=constraints,
        business_requirements=business_requirements,
    )

    print(f"\n📊 Migration Plan Summary:")
    print(f"  Duration: {plan.estimated_duration_days} days")
    print(f"  Cost: ${plan.total_cost_estimate:,.2f}")
    print(f"  Phases: {len(plan.phases)}")
    print(f"  Risks: {len(plan.risks)}")

    print(f"\n🗓️  Migration Phases:")
    for phase in plan.phases:
        print(f"  Phase {phase.phase_number}: {phase.name}")
        print(f"    Duration: {phase.duration_days} days")
        print(f"    Risk: {phase.risk_level.upper()}")
        print(f"    Tasks: {len(phase.tasks)}")

    print(f"\n⚠️  Top Risks:")
    high_risks = [r for r in plan.risks if r.impact in ["high", "critical"]]
    for risk in high_risks[:3]:
        print(f"    • [{risk.probability}/{risk.impact}] {risk.description}")
        print(f"      Mitigation: {risk.mitigation}")

    print(f"\n🧪 Test Cases: {len(plan.test_cases)}")
    critical_tests = [t for t in plan.test_cases if t.priority == "critical"]
    print(f"    Critical: {len(critical_tests)}")

    print(f"\n🔄 Rollback Strategy:")
    print(f"  {plan.rollback_strategy[:200]}...")

    # Generate runbook for Phase 1
    print(f"\n📋 Generating Phase 1 Runbook...")
    runbook = await agent.generate_runbook(
        migration_plan=plan,
        phase_number=1,
    )
    print("  ✅ Phase 1 execution runbook generated")


async def release_manager_example():
    """Demonstrate Release Manager Agent"""
    from aiops.agents import ReleaseManagerAgent

    print("\n" + "=" * 70)
    print("📦 RELEASE MANAGER AGENT")
    print("=" * 70)

    agent = ReleaseManagerAgent()

    # Release details
    version = "v2.5.0"
    release_date = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d 14:00 UTC")

    # Changes in this release
    changes = [
        {
            "change_id": "PR-1234",
            "description": "Add new payment provider integration",
            "type": "feature",
        },
        {
            "change_id": "PR-1245",
            "description": "Fix critical memory leak in worker process",
            "type": "bugfix",
        },
        {
            "change_id": "PR-1256",
            "description": "Database schema migration for user preferences",
            "type": "feature",
        },
        {
            "change_id": "PR-1267",
            "description": "Update API authentication to OAuth 2.1",
            "type": "feature",
        },
        {
            "change_id": "PR-1278",
            "description": "Performance optimization for search queries",
            "type": "refactor",
        },
    ]

    # Previous release metrics
    previous_release_metrics = {
        "version": "v2.4.0",
        "release_duration_minutes": 45,
        "rollback_required": False,
        "issues_post_release": 2,
        "customer_impact": "minimal",
    }

    # Infrastructure
    infrastructure_details = {
        "platform": "Kubernetes on AWS EKS",
        "instances": 20,
        "regions": ["us-east-1", "us-west-2"],
        "load_balancer": "AWS ALB",
        "database": "RDS PostgreSQL with read replicas",
    }

    # Traffic pattern
    user_traffic_pattern = {
        "peak_hours": "9am-5pm EST",
        "requests_per_second": {
            "average": 5000,
            "peak": 12000,
        },
        "users": {
            "total": 150000,
            "concurrent": 8000,
        },
    }

    print(f"\n📦 Planning Release...")
    print(f"  Version: {version}")
    print(f"  Date: {release_date}")
    print(f"  Environment: production")
    print(f"  Changes: {len(changes)}")

    # Create release plan
    plan = await agent.execute(
        version=version,
        release_date=release_date,
        environment="production",
        changes=changes,
        previous_release_metrics=previous_release_metrics,
        infrastructure_details=infrastructure_details,
        user_traffic_pattern=user_traffic_pattern,
    )

    print(f"\n📊 Release Plan Summary:")
    print(f"  Risk Score: {plan.risk_score}/100")
    print(f"  Rollout Strategy: {plan.rollout_strategy.strategy_type}")
    print(f"  Estimated Duration: {plan.rollout_strategy.estimated_duration_minutes} minutes")
    print(f"  Validation Checks: {len(plan.validation_checks)}")

    print(f"\n📝 Changes Analysis:")
    for change in plan.changes:
        print(f"  • [{change.type}] {change.description}")
        print(f"    Risk: {change.risk_level}, Breaking: {change.breaking_change}")

    print(f"\n⚠️  Identified Risks ({len(plan.risks)}):")
    for risk in plan.risks[:3]:
        print(f"    • [{risk.probability}/{risk.impact}] {risk.description}")
        print(f"      Mitigation: {risk.mitigation}")

    print(f"\n🚀 Rollout Strategy: {plan.rollout_strategy.strategy_type.upper()}")
    for i, phase in enumerate(plan.rollout_strategy.phases, 1):
        print(f"  Phase {i}: {phase}")

    print(f"\n✅ Success Criteria:")
    for criterion in plan.rollout_strategy.success_criteria:
        print(f"    • {criterion}")

    print(f"\n🔴 Rollback Triggers:")
    for trigger in plan.rollout_strategy.rollback_triggers[:3]:
        print(f"    • {trigger}")

    print(f"\n🧪 Validation Checks ({len(plan.validation_checks)}):")
    critical_checks = [c for c in plan.validation_checks if c.priority == "critical"]
    for check in critical_checks[:3]:
        print(f"    • [{check.type}] {check.name}")
        print(f"      {check.description}")

    print(f"\n📋 Executive Summary:")
    print(f"  {plan.executive_summary}")

    # Assess Go/No-Go
    print(f"\n🎯 Assessing Go/No-Go Decision...")

    current_system_health = {
        "uptime": "99.98%",
        "error_rate": "0.02%",
        "latency_p95_ms": 150,
        "active_incidents": 0,
        "pending_alerts": 2,
    }

    pre_release_test_results = {
        "unit_tests": {"total": 1250, "passed": 1250, "failed": 0},
        "integration_tests": {"total": 320, "passed": 318, "failed": 2},
        "e2e_tests": {"total": 85, "passed": 85, "failed": 0},
        "performance_tests": "passed",
        "security_scan": "passed",
    }

    go_no_go = await agent.assess_go_no_go(
        release_plan=plan,
        current_system_health=current_system_health,
        pre_release_test_results=pre_release_test_results,
    )

    print(f"  ✅ Go/No-Go assessment completed")
    print(f"  Recommendation available in assessment report")


async def main():
    """Run all examples"""
    print("\n" + "=" * 70)
    print("🤖 ADVANCED DEVOPS AGENTS EXAMPLES")
    print("=" * 70)
    print("\nThis example demonstrates 4 advanced DevOps agents:")
    print("  1. Incident Response Agent - Automated incident analysis")
    print("  2. Compliance Checker Agent - Multi-standard compliance validation")
    print("  3. Migration Planner Agent - Complex migration planning")
    print("  4. Release Manager Agent - Release planning and coordination")

    try:
        # Run examples
        await incident_response_example()
        await compliance_checker_example()
        await migration_planner_example()
        await release_manager_example()

        print("\n" + "=" * 70)
        print("✅ ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("=" * 70)

        print("\n📚 Key Takeaways:")
        print("  • Incident Response: Fast root cause analysis and remediation")
        print("  • Compliance: Automated compliance checking across standards")
        print("  • Migration Planning: Risk-aware migration strategies")
        print("  • Release Management: Safe, validated release processes")

        print("\n💡 Next Steps:")
        print("  1. Customize agents for your specific use cases")
        print("  2. Integrate with your existing DevOps pipelines")
        print("  3. Add custom validation and monitoring")
        print("  4. Build automated workflows combining multiple agents")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
