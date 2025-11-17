#!/usr/bin/env python3
"""
Simple standalone test for the 12 new AIOps features.
This test doesn't require external dependencies like LangChain.
"""

import asyncio
import sys

# Test each feature independently

async def test_all_features():
    """Test all 12 new features"""
    print("="*80)
    print("🧪 Testing 12 New AIOps Features")
    print("="*80 + "\n")

    results = {}

    # Feature 1: K8s Optimizer
    try:
        print("1️⃣  Testing Kubernetes Resource Optimizer...")
        sys.path.insert(0, '/home/user/AIOps')
        from aiops.agents.k8s_optimizer import KubernetesOptimizerAgent, K8sOptimizationResult

        agent = KubernetesOptimizerAgent(llm_factory=None)
        deployment_yaml = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-app
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: app
        resources:
          requests:
            cpu: "1000m"
"""
        result = await agent.analyze_deployment(deployment_yaml, {"app": {"cpu": 100, "memory": 128}})
        assert isinstance(result, K8sOptimizationResult)
        assert result.total_resources >= 0
        print(f"   ✅ PASSED - Found {len(result.recommendations)} recommendations")
        results["K8s Optimizer"] = "PASSED"
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        results["K8s Optimizer"] = f"FAILED: {e}"

    # Feature 2: DB Query Analyzer
    try:
        print("\n2️⃣  Testing Database Query Analyzer...")
        from aiops.agents.db_query_analyzer import DatabaseQueryAnalyzer, QueryAnalysisResult

        agent = DatabaseQueryAnalyzer(llm_factory=None)
        query = "SELECT * FROM users WHERE id = 1"
        result = await agent.analyze_query(query)
        assert isinstance(result, QueryAnalysisResult)
        assert result.overall_score >= 0
        print(f"   ✅ PASSED - Score: {result.overall_score:.1f}/100")
        results["DB Query Analyzer"] = "PASSED"
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        results["DB Query Analyzer"] = f"FAILED: {e}"

    # Feature 3: Cost Optimizer
    try:
        print("\n3️⃣  Testing Cloud Cost Optimizer...")
        from aiops.agents.cost_optimizer import CloudCostOptimizer, CostOptimizationResult

        agent = CloudCostOptimizer(llm_factory=None)
        resources = [{"type": "EC2", "id": "i-123", "monthly_cost": 100, "pricing": "on-demand", "uptime_percentage": 100}]
        result = await agent.analyze_costs(resources, None, "AWS")
        assert isinstance(result, CostOptimizationResult)
        assert result.current_monthly_cost >= 0
        print(f"   ✅ PASSED - Potential savings: ${result.potential_monthly_savings:.2f}/mo")
        results["Cost Optimizer"] = "PASSED"
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        results["Cost Optimizer"] = f"FAILED: {e}"

    # Feature 4: IaC Validator
    try:
        print("\n4️⃣  Testing Infrastructure as Code Validator...")
        from aiops.agents.iac_validator import IaCValidator, IaCValidationResult

        agent = IaCValidator(llm_factory=None)
        terraform = 'resource "aws_s3_bucket" "test" { bucket = "test" }'
        result = await agent.validate_terraform(terraform)
        assert isinstance(result, IaCValidationResult)
        assert result.security_score >= 0
        print(f"   ✅ PASSED - Security score: {result.security_score:.1f}/100")
        results["IaC Validator"] = "PASSED"
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        results["IaC Validator"] = f"FAILED: {e}"

    # Feature 5: Container Security
    try:
        print("\n5️⃣  Testing Container Security Scanner...")
        from aiops.agents.container_security import ContainerSecurityScanner, ContainerSecurityResult

        agent = ContainerSecurityScanner(llm_factory=None)
        dockerfile = "FROM ubuntu:latest\nRUN apt-get update"
        result = await agent.scan_dockerfile(dockerfile)
        assert isinstance(result, ContainerSecurityResult)
        assert result.security_score >= 0
        print(f"   ✅ PASSED - Security score: {result.security_score:.1f}/100")
        results["Container Security"] = "PASSED"
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        results["Container Security"] = f"FAILED: {e}"

    # Feature 6: Chaos Engineer
    try:
        print("\n6️⃣  Testing Chaos Engineering Agent...")
        from aiops.agents.chaos_engineer import ChaosEngineer, ChaosEngineeringPlan

        agent = ChaosEngineer(llm_factory=None)
        result = await agent.create_chaos_plan(["api", "db"])
        assert isinstance(result, ChaosEngineeringPlan)
        assert len(result.experiments) > 0
        print(f"   ✅ PASSED - Created {len(result.experiments)} experiments")
        results["Chaos Engineer"] = "PASSED"
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        results["Chaos Engineer"] = f"FAILED: {e}"

    # Feature 7: SLA Monitor
    try:
        print("\n7️⃣  Testing SLA Compliance Monitor...")
        from aiops.agents.sla_monitor import SLAComplianceMonitor, SLAMonitoringResult

        agent = SLAComplianceMonitor(llm_factory=None)
        metrics = {"uptime_percentage": 99.9, "latency_p99_ms": 200, "error_rate": 0.1}
        result = await agent.monitor_sla("test-api", metrics)
        assert isinstance(result, SLAMonitoringResult)
        assert result.compliance_score >= 0
        print(f"   ✅ PASSED - Compliance: {result.compliance_score:.1f}/100, Health: {result.overall_health}")
        results["SLA Monitor"] = "PASSED"
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        results["SLA Monitor"] = f"FAILED: {e}"

    # Feature 8: Config Drift Detector
    try:
        print("\n8️⃣  Testing Configuration Drift Detector...")
        from aiops.agents.config_drift_detector import ConfigurationDriftDetector, DriftDetectionResult

        agent = ConfigurationDriftDetector(llm_factory=None)
        baseline = {"key1": "value1", "key2": 100}
        target = {"key1": "value2", "key2": 100}
        result = await agent.detect_drift(baseline, target)
        assert isinstance(result, DriftDetectionResult)
        assert result.drift_score >= 0
        print(f"   ✅ PASSED - Drift score: {result.drift_score:.1f}/100, Drifts: {result.drifts_detected}")
        results["Config Drift Detector"] = "PASSED"
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        results["Config Drift Detector"] = f"FAILED: {e}"

    # Feature 9: Service Mesh Analyzer
    try:
        print("\n9️⃣  Testing Service Mesh Analyzer...")
        from aiops.agents.service_mesh_analyzer import ServiceMeshAnalyzer, ServiceMeshAnalysisResult

        agent = ServiceMeshAnalyzer(llm_factory=None)
        config = {"services": [{"name": "api", "versions": ["v1"]}], "dependencies": {}}
        metrics = {"api": {"p99_latency_ms": 100, "success_rate": 99.9}}
        result = await agent.analyze_mesh(config, metrics)
        assert isinstance(result, ServiceMeshAnalysisResult)
        assert result.health_score >= 0
        print(f"   ✅ PASSED - Health: {result.health_score:.1f}/100")
        results["Service Mesh Analyzer"] = "PASSED"
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        results["Service Mesh Analyzer"] = f"FAILED: {e}"

    # Feature 10: Secret Scanner
    try:
        print("\n🔟 Testing Secret Scanner...")
        from aiops.agents.secret_scanner import SecretScanner, SecretScanResult

        agent = SecretScanner(llm_factory=None)
        code = """
API_KEY = "AKIAIOSFODNN7EXAMPLE"
PASSWORD = "mysecretpassword123"
"""
        result = await agent.scan_code(code)
        assert isinstance(result, SecretScanResult)
        assert result.secrets_found >= 0
        print(f"   ✅ PASSED - Found {result.secrets_found} secrets, Risk: {result.risk_score:.0f}/100")
        results["Secret Scanner"] = "PASSED"
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        results["Secret Scanner"] = f"FAILED: {e}"

    # Feature 11: API Performance Analyzer
    try:
        print("\n1️⃣1️⃣  Testing API Performance Analyzer...")
        from aiops.agents.api_performance_analyzer import APIPerformanceAnalyzer, APIPerformanceResult

        agent = APIPerformanceAnalyzer(llm_factory=None)
        endpoints = [{
            "method": "GET",
            "path": "/api/users",
            "avg_latency_ms": 100,
            "p95_latency_ms": 150,
            "p99_latency_ms": 200,
            "requests_per_minute": 100,
            "error_rate": 0.5,
            "avg_response_size_kb": 50
        }]
        result = await agent.analyze_api(endpoints)
        assert isinstance(result, APIPerformanceResult)
        assert result.performance_score >= 0
        print(f"   ✅ PASSED - Performance: {result.performance_score:.1f}/100")
        results["API Performance Analyzer"] = "PASSED"
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        results["API Performance Analyzer"] = f"FAILED: {e}"

    # Feature 12: Disaster Recovery Planner
    try:
        print("\n1️⃣2️⃣  Testing Disaster Recovery Planner...")
        from aiops.agents.disaster_recovery import DisasterRecoveryPlanner, DRPlanResult

        agent = DisasterRecoveryPlanner(llm_factory=None)
        systems = [{
            "name": "db",
            "type": "database",
            "hours_since_backup": 12,
            "backup_frequency": "daily",
            "backup_size_gb": 100,
            "retention_days": 30,
            "backup_tested": True
        }]
        result = await agent.create_dr_plan(systems)
        assert isinstance(result, DRPlanResult)
        assert len(result.scenarios) > 0
        print(f"   ✅ PASSED - Readiness: {result.overall_readiness}, Scenarios: {len(result.scenarios)}")
        results["Disaster Recovery Planner"] = "PASSED"
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        results["Disaster Recovery Planner"] = f"FAILED: {e}"

    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)

    passed = sum(1 for v in results.values() if v == "PASSED")
    total = len(results)

    for feature, status in results.items():
        icon = "✅" if status == "PASSED" else "❌"
        print(f"{icon} {feature}: {status}")

    print("="*80)
    print(f"RESULT: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    print("="*80)

    return passed == total

if __name__ == "__main__":
    success = asyncio.run(test_all_features())
    sys.exit(0 if success else 1)
