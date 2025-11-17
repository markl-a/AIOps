"""
Working Examples for All 12 New AIOps Features

This file demonstrates practical usage of each new feature with real-world scenarios.
Each example is designed to be run independently and shows the actual output.
"""

import asyncio
import json
from datetime import datetime


# Feature 1: Kubernetes Resource Optimizer
async def example_k8s_optimizer():
    """Example: Optimize Kubernetes deployment for resource efficiency"""
    print("\n" + "="*80)
    print("FEATURE 1: Kubernetes Resource Optimizer")
    print("="*80)

    from aiops.agents.k8s_optimizer import KubernetesOptimizerAgent

    # Sample Kubernetes deployment YAML
    deployment_yaml = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: production
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: web
        image: nginx:latest
        resources:
          requests:
            cpu: "2000m"
            memory: "2Gi"
          limits:
            cpu: "4000m"
            memory: "4Gi"
    """

    # Actual usage metrics (simulated)
    metrics = {
        "web": {
            "cpu": 300,  # Using only 300m out of 2000m requested
            "memory": 512  # Using only 512Mi out of 2Gi
        }
    }

    agent = KubernetesOptimizerAgent()
    result = await agent.analyze_deployment(deployment_yaml, metrics)

    print(f"\n📊 Analysis Results:")
    print(f"   Cluster Efficiency: {result.cluster_efficiency:.1f}/100")
    print(f"   Potential Monthly Savings: ${result.potential_cost_savings:.2f}")
    print(f"   Issues Found: {len(result.issues_found)}")
    print(f"\n💡 Recommendations ({len(result.recommendations)}):")
    for i, rec in enumerate(result.recommendations[:3], 1):
        print(f"   {i}. [{rec.priority.upper()}] {rec.resource_name}")
        print(f"      {rec.reasoning}")
        print(f"      Savings: ${sum(rec.potential_savings.values()):.2f}/month")

    print(f"\n📝 Summary:\n{result.summary}")
    return result


# Feature 2: Database Query Analyzer
async def example_db_query_analyzer():
    """Example: Analyze SQL query performance and get optimization suggestions"""
    print("\n" + "="*80)
    print("FEATURE 2: Database Query Analyzer")
    print("="*80)

    from aiops.agents.db_query_analyzer import DatabaseQueryAnalyzer

    # Problematic SQL query
    query = """
    SELECT * FROM users
    JOIN orders ON users.id = orders.user_id
    WHERE YEAR(created_at) = 2024
    AND users.email NOT IN (SELECT email FROM blacklist)
    """

    agent = DatabaseQueryAnalyzer()
    result = await agent.analyze_query(query, database_type="PostgreSQL")

    print(f"\n📊 Query Analysis:")
    print(f"   Quality Score: {result.overall_score:.1f}/100")
    print(f"   Issues Found: {len(result.optimizations)}")
    print(f"\n⚠️  Optimization Opportunities:")
    for opt in result.optimizations[:3]:
        print(f"\n   [{opt.severity.upper()}] {opt.issue_type}")
        print(f"   {opt.explanation}")
        print(f"   Expected Speedup: {opt.estimated_speedup}")

    if result.index_recommendations:
        print(f"\n🔍 Index Recommendations:")
        for idx in result.index_recommendations[:2]:
            print(f"   • {idx.table_name}.{', '.join(idx.columns)}")
            print(f"     DDL: {idx.ddl}")

    print(f"\n📝 Summary:\n{result.summary}")
    return result


# Feature 3: Cloud Cost Optimizer
async def example_cost_optimizer():
    """Example: Identify cloud cost savings opportunities"""
    print("\n" + "="*80)
    print("FEATURE 3: Cloud Cost Optimizer")
    print("="*80)

    from aiops.agents.cost_optimizer import CloudCostOptimizer

    # Sample cloud resources
    resources = [
        {
            "type": "EC2",
            "id": "i-1234567890abcdef0",
            "monthly_cost": 150.00,
            "pricing": "on-demand",
            "uptime_percentage": 95
        },
        {
            "type": "RDS",
            "id": "db-prod-main",
            "monthly_cost": 300.00,
            "pricing": "on-demand",
            "uptime_percentage": 100
        },
        {
            "type": "EBS",
            "id": "vol-unattached-1",
            "monthly_cost": 20.00,
            "attached": False
        },
        {
            "type": "Snapshot",
            "id": "snap-old-backup",
            "monthly_cost": 15.00,
            "age_days": 180
        }
    ]

    # Usage metrics
    usage_metrics = {
        "i-1234567890abcdef0": {
            "cpu_avg": 15.0,
            "memory_avg": 25.0,
            "network_avg": 10.0
        }
    }

    agent = CloudCostOptimizer()
    result = await agent.analyze_costs(resources, usage_metrics, cloud_provider="AWS")

    print(f"\n💰 Cost Analysis:")
    print(f"   Current Monthly Cost: ${result.current_monthly_cost:.2f}")
    print(f"   Potential Savings: ${result.potential_monthly_savings:.2f}")
    print(f"   Annual Savings: ${result.potential_monthly_savings * 12:.2f}")
    print(f"\n🎯 Top Savings Opportunities:")
    for saving in sorted(result.savings_opportunities, key=lambda x: x.potential_savings, reverse=True)[:3]:
        print(f"\n   [{saving.priority.upper()}] {saving.resource_type}: {saving.resource_id}")
        print(f"   Current: ${saving.current_cost:.2f}/mo → Save ${saving.potential_savings:.2f}/mo ({saving.savings_percentage:.0f}%)")
        print(f"   Action: {saving.recommendation}")
        print(f"   Effort: {saving.implementation_effort}")

    print(f"\n📝 Summary:\n{result.summary}")
    return result


# Feature 4: Infrastructure as Code Validator
async def example_iac_validator():
    """Example: Validate Terraform code for security and best practices"""
    print("\n" + "="*80)
    print("FEATURE 4: Infrastructure as Code Validator")
    print("="*80)

    from aiops.agents.iac_validator import IaCValidator

    # Sample Terraform code with issues
    terraform_code = """
resource "aws_s3_bucket" "data" {
  bucket = "my-data-bucket"
  acl    = "public-read"
}

resource "aws_db_instance" "main" {
  allocated_storage    = 100
  engine              = "postgres"
  instance_class      = "db.t3.medium"
  password            = "SuperSecret123!"  # Hardcoded!
}

resource "aws_security_group" "web" {
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
"""

    agent = IaCValidator()
    result = await agent.validate_terraform(terraform_code)

    print(f"\n🔒 Security Analysis:")
    print(f"   Security Score: {result.security_score:.1f}/100")
    print(f"   Cost Score: {result.cost_score:.1f}/100")
    print(f"   Compliance Score: {result.compliance_score:.1f}/100")
    print(f"\n⚠️  Issues Found ({len(result.issues)}):")
    for issue in sorted(result.issues, key=lambda x: {"critical": 0, "high": 1, "medium": 2}[x.severity])[:5]:
        print(f"\n   [{issue.severity.upper()}] {issue.category.upper()}")
        print(f"   Resource: {issue.resource_type}")
        print(f"   Issue: {issue.issue}")
        print(f"   Fix: {issue.recommendation}")

    print(f"\n📝 Summary:\n{result.summary}")
    return result


# Feature 5: Container Security Scanner
async def example_container_security():
    """Example: Scan Dockerfile for security vulnerabilities"""
    print("\n" + "="*80)
    print("FEATURE 5: Container Security Scanner")
    print("="*80)

    from aiops.agents.container_security import ContainerSecurityScanner

    # Sample Dockerfile with security issues
    dockerfile = """
FROM ubuntu:latest

# Hardcoded API key - BAD!
ENV API_KEY=sk_live_abc123xyz789secretkey

# Running as root - BAD!
RUN apt-get update && apt-get install -y nginx python3

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
"""

    agent = ContainerSecurityScanner()
    result = await agent.scan_dockerfile(dockerfile, image_name="my-app")

    print(f"\n🔒 Security Scan Results:")
    print(f"   Security Score: {result.security_score:.1f}/100")
    print(f"   Risk Level: {result.risk_level.upper()}")
    print(f"   Vulnerabilities: {len(result.vulnerabilities)}")
    print(f"   Misconfigurations: {len(result.misconfigurations)}")

    if result.vulnerabilities:
        print(f"\n🚨 Critical Vulnerabilities:")
        for vuln in result.vulnerabilities[:3]:
            print(f"   • [{vuln.severity.upper()}] {vuln.package_name}")
            print(f"     {vuln.description}")
            if vuln.fixed_version:
                print(f"     Fix: Upgrade to {vuln.fixed_version}")

    print(f"\n⚙️  Misconfigurations:")
    for config in result.misconfigurations[:3]:
        print(f"   • {config}")

    print(f"\n💡 Recommendations:")
    for rec in result.recommendations[:3]:
        print(f"   • {rec}")

    print(f"\n📝 Summary:\n{result.summary}")
    return result


# Feature 6: Chaos Engineering Agent
async def example_chaos_engineer():
    """Example: Create chaos engineering test plan"""
    print("\n" + "="*80)
    print("FEATURE 6: Chaos Engineering Agent")
    print("="*80)

    from aiops.agents.chaos_engineer import ChaosEngineer

    services = ["api-gateway", "user-service", "payment-service", "database"]

    agent = ChaosEngineer()
    plan = await agent.create_chaos_plan(services, environment="staging")

    print(f"\n🔥 Chaos Engineering Plan:")
    print(f"   Environment: {plan.environment}")
    print(f"   Experiments: {len(plan.experiments)}")
    print(f"   Total Duration: {plan.estimated_duration_hours:.1f} hours")
    print(f"   Risk Score: {plan.total_risk_score:.1f}/3.0")

    print(f"\n🧪 Planned Experiments:")
    for exp in plan.experiments[:3]:
        print(f"\n   {exp.name}")
        print(f"   Type: {exp.type} | Risk: {exp.risk_level.upper()} | Duration: {exp.duration_minutes}min")
        print(f"   Target: {exp.target}")
        print(f"   Hypothesis: {exp.hypothesis}")
        print(f"   Success Criteria:")
        for criteria in exp.success_criteria[:2]:
            print(f"      ✓ {criteria}")

    # Simulate running an experiment
    print(f"\n📊 Example: Analyzing Chaos Experiment Result")
    metrics_before = {"latency_p99": 100, "error_rate": 0.1, "cpu_usage": 45}
    metrics_after = {"latency_p99": 250, "error_rate": 2.5, "cpu_usage": 78}
    logs = ["2024-01-15 10:00:00 ERROR Connection timeout", "2024-01-15 10:00:05 WARN Retry attempt 1"]

    result = await agent.analyze_chaos_result(plan.experiments[0], metrics_before, metrics_after, logs)

    print(f"\n   Result: {result.status.upper()}")
    print(f"   Resilience: {result.system_resilience.upper()}")
    print(f"   Issues Found: {len(result.issues_found)}")
    if result.recommendations:
        print(f"   Top Recommendation: {result.recommendations[0]}")

    return plan


# Feature 7: SLA Compliance Monitor
async def example_sla_monitor():
    """Example: Monitor SLA compliance and predict violations"""
    print("\n" + "="*80)
    print("FEATURE 7: SLA Compliance Monitor")
    print("="*80)

    from aiops.agents.sla_monitor import SLAComplianceMonitor

    # Current service metrics
    metrics = {
        "uptime_percentage": 99.85,  # Slightly below 99.9% target
        "latency_p99_ms": 280,
        "error_rate": 0.8,
        "requests_per_second": 1200
    }

    agent = SLAComplianceMonitor()
    result = await agent.monitor_sla("payment-api", metrics)

    print(f"\n📊 SLA Monitoring:")
    print(f"   Service: {result.service_name}")
    print(f"   Health: {result.overall_health.upper()}")
    print(f"   Compliance Score: {result.compliance_score:.1f}/100")

    print(f"\n📈 Current SLIs:")
    for sli in result.slis:
        print(f"   • {sli.name}: {sli.current_value}{sli.unit}")

    print(f"\n🎯 SLO Status:")
    for slo in result.slos:
        status_icon = "✅" if slo.status == "compliant" else "⚠️" if slo.status == "at_risk" else "❌"
        print(f"   {status_icon} {slo.name}: {slo.current_compliance:.1f}% ({slo.status.upper()})")
        print(f"      Error Budget: {slo.error_budget_remaining:.1f}% remaining")

    if result.violations:
        print(f"\n🚨 Predicted Violations:")
        for violation in result.violations:
            print(f"   • {violation.slo_name}")
            print(f"     Probability: {violation.probability:.0f}%")
            print(f"     Time to Violation: {violation.time_to_violation}")
            print(f"     Action: {violation.recommended_actions[0]}")

    print(f"\n💡 Recommendations:")
    for rec in result.recommendations[:3]:
        print(f"   • {rec}")

    print(f"\n📝 Summary:\n{result.summary}")
    return result


# Feature 8: Configuration Drift Detector
async def example_config_drift():
    """Example: Detect configuration drift between environments"""
    print("\n" + "="*80)
    print("FEATURE 8: Configuration Drift Detector")
    print("="*80)

    from aiops.agents.config_drift_detector import ConfigurationDriftDetector

    # Production configuration (baseline)
    production_config = {
        "database_url": "postgres://prod-db:5432/app",
        "cache_ttl": 300,
        "max_connections": 100,
        "log_level": "INFO",
        "feature_flags": {
            "new_ui": True,
            "beta_features": False
        },
        "api_timeout": 30,
        "encryption_enabled": True
    }

    # Staging configuration (drifted)
    staging_config = {
        "database_url": "postgres://staging-db:5432/app",
        "cache_ttl": 60,  # Different!
        "max_connections": 50,  # Different!
        "log_level": "DEBUG",  # Different!
        "feature_flags": {
            "new_ui": True,
            "beta_features": True  # Different!
        },
        "api_timeout": 30
        # Missing: encryption_enabled
    }

    agent = ConfigurationDriftDetector()
    result = await agent.detect_drift(
        production_config,
        staging_config,
        baseline_env="production",
        target_env="staging"
    )

    print(f"\n🔍 Drift Detection Results:")
    print(f"   Configurations Checked: {result.total_configs}")
    print(f"   Drifts Detected: {result.drifts_detected}")
    print(f"   Drift Score: {result.drift_score:.1f}/100")
    print(f"   Status: {result.compliance_status.upper()}")

    print(f"\n⚠️  Configuration Drifts:")
    for drift in sorted(result.drifts, key=lambda x: {"critical": 0, "high": 1, "medium": 2}[x.severity])[:5]:
        print(f"\n   [{drift.severity.upper()}] {drift.config_key}")
        print(f"   Production: {drift.expected_value}")
        print(f"   Staging: {drift.actual_value}")
        print(f"   Impact: {drift.impact}")
        print(f"   Fix: {drift.recommendation}")

    print(f"\n💡 Recommendations:")
    for rec in result.recommendations[:3]:
        print(f"   • {rec}")

    print(f"\n📝 Summary:\n{result.summary}")
    return result


# Feature 9: Service Mesh Analyzer
async def example_service_mesh():
    """Example: Analyze service mesh performance and configuration"""
    print("\n" + "="*80)
    print("FEATURE 9: Service Mesh Analyzer")
    print("="*80)

    from aiops.agents.service_mesh_analyzer import ServiceMeshAnalyzer

    # Service mesh configuration
    mesh_config = {
        "services": [
            {"name": "frontend", "versions": ["v1", "v2"], "mtls_enabled": False},
            {"name": "backend", "versions": ["v1"]},
            {"name": "database", "versions": ["v1"]}
        ],
        "dependencies": {
            "frontend": ["backend"],
            "backend": ["database"]
        }
    }

    # Traffic metrics
    traffic_metrics = {
        "frontend": {
            "p99_latency_ms": 550,  # High!
            "success_rate": 98.5  # Below target!
        },
        "backend": {
            "p99_latency_ms": 150,
            "success_rate": 99.8
        }
    }

    agent = ServiceMeshAnalyzer()
    result = await agent.analyze_mesh(mesh_config, traffic_metrics, mesh_type="istio")

    print(f"\n🕸️  Service Mesh Analysis:")
    print(f"   Mesh Type: {result.mesh_type}")
    print(f"   Services: {result.services_analyzed}")
    print(f"   Health Score: {result.health_score:.1f}/100")

    print(f"\n📊 Service Metrics:")
    for metric in result.metrics:
        status_icon = "✅" if metric.status == "healthy" else "⚠️" if metric.status == "warning" else "❌"
        print(f"   {status_icon} {metric.service_name} - {metric.metric_type}: {metric.value}{metric.unit}")

    print(f"\n⚙️  Optimization Opportunities:")
    for opt in result.optimizations[:3]:
        print(f"\n   [{opt.priority.upper()}] {opt.optimization_type}")
        print(f"   Service: {opt.service_name}")
        print(f"   Benefit: {opt.expected_benefit}")
        print(f"   How: {opt.implementation}")

    if result.topology_insights:
        print(f"\n🔍 Topology Insights:")
        for insight in result.topology_insights[:3]:
            print(f"   • {insight}")

    print(f"\n📝 Summary:\n{result.summary}")
    return result


# Feature 10: Secret Scanner
async def example_secret_scanner():
    """Example: Scan code for hardcoded secrets"""
    print("\n" + "="*80)
    print("FEATURE 10: Secret Scanner")
    print("="*80)

    from aiops.agents.secret_scanner import SecretScanner

    # Sample code with secrets
    code = """
# Configuration file
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

# Database connection
DATABASE_URL = "postgres://admin:SuperSecret123@db.example.com:5432/production"

# API keys (example - for demonstration only)
STRIPE_SECRET_KEY = "sk_test_EXAMPLE_KEY_DO_NOT_USE"
GITHUB_TOKEN = "ghp_EXAMPLE_TOKEN_DO_NOT_USE"

# JWT token in code
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
"""

    agent = SecretScanner()
    result = await agent.scan_code(code, file_path="config.py")

    print(f"\n🔒 Secret Scan Results:")
    print(f"   Files Scanned: {result.files_scanned}")
    print(f"   Secrets Found: {result.secrets_found}")
    print(f"   Risk Score: {result.risk_score:.0f}/100")

    print(f"\n🚨 Detected Secrets:")
    for secret in result.secrets:
        print(f"\n   [{secret.severity.upper()}] {secret.secret_type}")
        print(f"   File: {secret.file_path}:{secret.line_number}")
        print(f"   Value: {secret.matched_string}")
        print(f"   Confidence: {secret.confidence:.0f}%")
        print(f"   Action: {secret.recommendation}")

    print(f"\n💡 Security Recommendations:")
    for rec in result.recommendations[:4]:
        print(f"   • {rec}")

    print(f"\n📝 Summary:\n{result.summary}")
    return result


# Feature 11: API Performance Analyzer
async def example_api_performance():
    """Example: Analyze API performance and get optimization suggestions"""
    print("\n" + "="*80)
    print("FEATURE 11: API Performance Analyzer")
    print("="*80)

    from aiops.agents.api_performance_analyzer import APIPerformanceAnalyzer

    # Sample API endpoints with performance data
    endpoints = [
        {
            "method": "GET",
            "path": "/api/users",
            "avg_latency_ms": 1200,  # High!
            "p95_latency_ms": 1800,
            "p99_latency_ms": 2500,
            "requests_per_minute": 250,
            "error_rate": 0.5,
            "avg_response_size_kb": 150
        },
        {
            "method": "POST",
            "path": "/api/orders",
            "avg_latency_ms": 650,
            "p95_latency_ms": 900,
            "p99_latency_ms": 1200,
            "requests_per_minute": 50,
            "error_rate": 2.5,  # High!
            "avg_response_size_kb": 25
        },
        {
            "method": "GET",
            "path": "/api/products",
            "avg_latency_ms": 150,
            "p95_latency_ms": 200,
            "p99_latency_ms": 250,
            "requests_per_minute": 500,
            "error_rate": 0.1,
            "avg_response_size_kb": 800  # Large!
        }
    ]

    agent = APIPerformanceAnalyzer()
    result = await agent.analyze_api(endpoints, api_type="REST")

    print(f"\n⚡ API Performance Analysis:")
    print(f"   API Type: {result.api_type}")
    print(f"   Endpoints: {result.endpoints_analyzed}")
    print(f"   Performance Score: {result.performance_score:.1f}/100")

    print(f"\n📊 Endpoint Performance:")
    for ep in result.endpoints:
        print(f"\n   {ep.method} {ep.path}")
        print(f"   P99 Latency: {ep.p99_latency_ms:.0f}ms | Errors: {ep.error_rate:.1f}% | Size: {ep.avg_response_size_kb:.0f}KB")

    print(f"\n🎯 Top Optimizations:")
    for opt in sorted(result.optimizations, key=lambda x: {"critical": 0, "high": 1, "medium": 2}[x.severity])[:4]:
        print(f"\n   [{opt.severity.upper()}] {opt.issue_type}")
        print(f"   Endpoint: {opt.endpoint}")
        print(f"   Expected: {opt.expected_improvement}")
        print(f"   Actions:")
        for action in opt.recommendations[:2]:
            print(f"      • {action}")

    if result.caching_opportunities:
        print(f"\n💾 Caching Opportunities:")
        for opp in result.caching_opportunities[:2]:
            print(f"   • {opp}")

    print(f"\n📝 Summary:\n{result.summary}")
    return result


# Feature 12: Disaster Recovery Planner
async def example_disaster_recovery():
    """Example: Create and validate disaster recovery plan"""
    print("\n" + "="*80)
    print("FEATURE 12: Disaster Recovery Planner")
    print("="*80)

    from aiops.agents.disaster_recovery import DisasterRecoveryPlanner

    # Systems to protect
    systems = [
        {
            "name": "production-database",
            "type": "database",
            "hours_since_backup": 6,
            "backup_frequency": "hourly",
            "backup_size_gb": 250,
            "retention_days": 30,
            "backup_tested": True
        },
        {
            "name": "application-server",
            "type": "application",
            "hours_since_backup": 24,
            "backup_frequency": "daily",
            "backup_size_gb": 50,
            "retention_days": 14,
            "backup_tested": False  # Problem!
        },
        {
            "name": "user-uploads",
            "type": "storage",
            "hours_since_backup": 72,  # Too old!
            "backup_frequency": "daily",
            "backup_size_gb": 500,
            "retention_days": 90,
            "backup_tested": False
        }
    ]

    agent = DisasterRecoveryPlanner()
    result = await agent.create_dr_plan(systems, organization="TechCorp")

    print(f"\n🚨 Disaster Recovery Plan:")
    print(f"   Organization: {result.organization}")
    print(f"   Readiness: {result.overall_readiness.upper()}")
    print(f"   Max RTO: {result.max_rto_minutes}min ({result.max_rto_minutes/60:.1f}h)")
    print(f"   Max RPO: {result.max_rpo_minutes}min ({result.max_rpo_minutes/60:.1f}h)")

    print(f"\n📋 Disaster Scenarios ({len(result.scenarios)}):")
    for scenario in result.scenarios[:2]:
        print(f"\n   {scenario.scenario_name}")
        print(f"   Probability: {scenario.probability.upper()} | Impact: {scenario.impact_severity.upper()}")
        print(f"   RTO: {scenario.rto_minutes}min | RPO: {scenario.rpo_minutes}min")
        print(f"   Recovery Steps: {len(scenario.recovery_procedures)}")
        print(f"   Example steps:")
        for proc in scenario.recovery_procedures[:2]:
            print(f"      {proc.step_number}. {proc.description} ({proc.estimated_time_minutes}min)")

    print(f"\n💾 Backup Validation:")
    for backup in result.backup_validations:
        status_icon = "✅" if backup.status == "healthy" else "⚠️" if backup.status == "warning" else "❌"
        print(f"\n   {status_icon} {backup.system_name}")
        print(f"   Frequency: {backup.backup_frequency} | Size: {backup.backup_size_gb}GB")
        print(f"   Tested: {'Yes' if backup.tested_recently else 'No'}")
        if backup.issues:
            print(f"   Issues: {', '.join(backup.issues)}")

    print(f"\n💡 Recommendations:")
    for rec in result.recommendations[:5]:
        print(f"   • {rec}")

    print(f"\n📝 Summary:\n{result.summary}")
    return result


async def run_all_examples():
    """Run all examples sequentially"""
    print("\n" + "="*80)
    print("🚀 AIOps Framework - 12 New Features Demonstration")
    print("="*80)
    print("Testing all features with working examples...")
    print("="*80)

    examples = [
        ("Kubernetes Resource Optimizer", example_k8s_optimizer),
        ("Database Query Analyzer", example_db_query_analyzer),
        ("Cloud Cost Optimizer", example_cost_optimizer),
        ("IaC Validator", example_iac_validator),
        ("Container Security Scanner", example_container_security),
        ("Chaos Engineering Agent", example_chaos_engineer),
        ("SLA Compliance Monitor", example_sla_monitor),
        ("Configuration Drift Detector", example_config_drift),
        ("Service Mesh Analyzer", example_service_mesh),
        ("Secret Scanner", example_secret_scanner),
        ("API Performance Analyzer", example_api_performance),
        ("Disaster Recovery Planner", example_disaster_recovery),
    ]

    results = {}
    for name, func in examples:
        try:
            result = await func()
            results[name] = "✅ SUCCESS"
        except Exception as e:
            results[name] = f"❌ FAILED: {str(e)}"
            print(f"\nError in {name}: {str(e)}")

    # Summary
    print("\n" + "="*80)
    print("📊 EXECUTION SUMMARY")
    print("="*80)
    for name, status in results.items():
        print(f"{status} - {name}")

    success_count = sum(1 for s in results.values() if "SUCCESS" in s)
    print(f"\n✅ Passed: {success_count}/{len(examples)}")
    print("="*80)


if __name__ == "__main__":
    # Run all examples
    asyncio.run(run_all_examples())

    # Or run individual examples:
    # asyncio.run(example_k8s_optimizer())
    # asyncio.run(example_db_query_analyzer())
    # asyncio.run(example_cost_optimizer())
    # ... etc
