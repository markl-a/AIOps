"""
Unit tests for Chaos Engineering Agent
"""

import pytest
from aiops.agents.chaos_engineer import (
    ChaosEngineer,
    ChaosExperiment,
    ChaosResult,
    ChaosEngineeringPlan
)


class TestChaosExperiment:
    """Tests for ChaosExperiment model"""

    def test_create_experiment(self):
        """Test creating a chaos experiment"""
        experiment = ChaosExperiment(
            name="Network Latency Test",
            type="network_latency",
            target="api-gateway",
            description="Inject 200ms latency",
            hypothesis="System should handle latency gracefully",
            blast_radius="limited",
            risk_level="low",
            duration_minutes=10,
            rollback_plan="Remove tc rules",
            success_criteria=["Response time < 5s"],
            commands=["tc qdisc add dev eth0 root netem delay 200ms"]
        )
        assert experiment.name == "Network Latency Test"
        assert experiment.type == "network_latency"
        assert experiment.risk_level == "low"

    def test_experiment_blast_radius(self):
        """Test different blast radius values"""
        for radius in ["limited", "moderate", "wide"]:
            experiment = ChaosExperiment(
                name="Test",
                type="test",
                target="test",
                description="Test",
                hypothesis="Test",
                blast_radius=radius,
                risk_level="low",
                duration_minutes=5,
                rollback_plan="Rollback",
                success_criteria=[],
                commands=[]
            )
            assert experiment.blast_radius == radius

    def test_experiment_risk_levels(self):
        """Test different risk levels"""
        for risk in ["low", "medium", "high"]:
            experiment = ChaosExperiment(
                name="Test",
                type="test",
                target="test",
                description="Test",
                hypothesis="Test",
                blast_radius="limited",
                risk_level=risk,
                duration_minutes=5,
                rollback_plan="Rollback",
                success_criteria=[],
                commands=[]
            )
            assert experiment.risk_level == risk


class TestChaosResult:
    """Tests for ChaosResult model"""

    def test_create_result(self):
        """Test creating a chaos result"""
        result = ChaosResult(
            experiment_name="Network Latency Test",
            status="success",
            duration_seconds=600,
            observations=["Latency increased by 200ms"],
            metrics_impact={"latency": {"before": 50, "after": 250}},
            system_resilience="good",
            issues_found=[],
            recommendations=[]
        )
        assert result.experiment_name == "Network Latency Test"
        assert result.status == "success"
        assert result.system_resilience == "good"

    def test_result_statuses(self):
        """Test different result statuses"""
        for status in ["success", "failed", "partial"]:
            result = ChaosResult(
                experiment_name="Test",
                status=status,
                duration_seconds=60,
                observations=[],
                metrics_impact={},
                system_resilience="good",
                issues_found=[],
                recommendations=[]
            )
            assert result.status == status

    def test_result_resilience_levels(self):
        """Test different resilience levels"""
        for resilience in ["excellent", "good", "fair", "poor"]:
            result = ChaosResult(
                experiment_name="Test",
                status="success",
                duration_seconds=60,
                observations=[],
                metrics_impact={},
                system_resilience=resilience,
                issues_found=[],
                recommendations=[]
            )
            assert result.system_resilience == resilience


class TestChaosEngineeringPlan:
    """Tests for ChaosEngineeringPlan model"""

    def test_create_plan(self):
        """Test creating a chaos engineering plan"""
        plan = ChaosEngineeringPlan(
            environment="staging",
            experiments=[],
            total_risk_score=1.5,
            estimated_duration_hours=2.0,
            summary="Test plan"
        )
        assert plan.environment == "staging"
        assert plan.total_risk_score == 1.5

    def test_plan_with_experiments(self):
        """Test plan with multiple experiments"""
        experiments = [
            ChaosExperiment(
                name=f"Test {i}",
                type="test",
                target="target",
                description="Test",
                hypothesis="Test",
                blast_radius="limited",
                risk_level="low",
                duration_minutes=10,
                rollback_plan="Rollback",
                success_criteria=[],
                commands=[]
            )
            for i in range(3)
        ]
        plan = ChaosEngineeringPlan(
            environment="production",
            experiments=experiments,
            total_risk_score=1.0,
            estimated_duration_hours=0.5,
            summary="3 experiments"
        )
        assert len(plan.experiments) == 3


class TestChaosEngineer:
    """Tests for ChaosEngineer"""

    @pytest.fixture
    def engineer(self):
        """Create engineer instance"""
        return ChaosEngineer()

    @pytest.mark.asyncio
    async def test_create_chaos_plan_single_service(self, engineer):
        """Test creating chaos plan for single service"""
        plan = await engineer.create_chaos_plan(
            services=["api-gateway"],
            environment="staging"
        )

        assert plan.environment == "staging"
        assert len(plan.experiments) >= 3  # Network, Pod, CPU
        assert plan.estimated_duration_hours > 0

    @pytest.mark.asyncio
    async def test_create_chaos_plan_multiple_services(self, engineer):
        """Test creating chaos plan for multiple services"""
        plan = await engineer.create_chaos_plan(
            services=["api-gateway", "user-service", "order-service"],
            environment="staging"
        )

        assert len(plan.experiments) >= 7  # 3 services * 2 + CPU + DB
        # Should include database experiment for multiple services
        db_experiments = [e for e in plan.experiments if "database" in e.target.lower()]
        assert len(db_experiments) >= 1

    @pytest.mark.asyncio
    async def test_create_chaos_plan_empty_services(self, engineer):
        """Test creating chaos plan with empty services"""
        plan = await engineer.create_chaos_plan(
            services=[],
            environment="staging"
        )

        # Should still create CPU stress test
        assert len(plan.experiments) >= 1

    @pytest.mark.asyncio
    async def test_create_chaos_plan_production(self, engineer):
        """Test creating chaos plan for production"""
        plan = await engineer.create_chaos_plan(
            services=["api"],
            environment="production"
        )

        assert plan.environment == "production"
        assert "production" in plan.summary.lower()

    @pytest.mark.asyncio
    async def test_network_latency_experiment(self, engineer):
        """Test network latency experiment creation"""
        plan = await engineer.create_chaos_plan(
            services=["my-service"],
            environment="staging"
        )

        network_exp = [e for e in plan.experiments if e.type == "network_latency"]
        assert len(network_exp) >= 1

        exp = network_exp[0]
        assert "latency" in exp.description.lower()
        assert exp.blast_radius == "limited"
        assert exp.risk_level == "low"
        assert len(exp.commands) > 0

    @pytest.mark.asyncio
    async def test_pod_failure_experiment(self, engineer):
        """Test pod failure experiment creation"""
        plan = await engineer.create_chaos_plan(
            services=["my-service"],
            environment="staging"
        )

        pod_exp = [e for e in plan.experiments if e.type == "pod_failure"]
        assert len(pod_exp) >= 1

        exp = pod_exp[0]
        assert "pod" in exp.description.lower() or "pod" in exp.name.lower()
        assert "kubectl" in " ".join(exp.commands)

    @pytest.mark.asyncio
    async def test_cpu_stress_experiment(self, engineer):
        """Test CPU stress experiment creation"""
        plan = await engineer.create_chaos_plan(
            services=["my-service"],
            environment="staging"
        )

        cpu_exp = [e for e in plan.experiments if e.type == "cpu_stress"]
        assert len(cpu_exp) >= 1

        exp = cpu_exp[0]
        assert exp.risk_level == "medium"
        assert "HPA" in exp.hypothesis or "scale" in exp.hypothesis.lower()

    @pytest.mark.asyncio
    async def test_dependency_failure_experiment(self, engineer):
        """Test dependency failure experiment creation"""
        plan = await engineer.create_chaos_plan(
            services=["service1", "service2"],
            environment="staging"
        )

        dep_exp = [e for e in plan.experiments if e.type == "dependency_failure"]
        assert len(dep_exp) >= 1

        exp = dep_exp[0]
        assert "database" in exp.target.lower()
        assert "circuit" in exp.hypothesis.lower() or "fallback" in exp.hypothesis.lower()

    @pytest.mark.asyncio
    async def test_risk_score_calculation(self, engineer):
        """Test risk score calculation"""
        plan = await engineer.create_chaos_plan(
            services=["service1"],
            environment="staging"
        )

        # Risk score should be average of experiment risks
        assert 0 < plan.total_risk_score <= 3

    @pytest.mark.asyncio
    async def test_duration_calculation(self, engineer):
        """Test duration calculation"""
        plan = await engineer.create_chaos_plan(
            services=["service1"],
            environment="staging"
        )

        # Should sum experiment durations
        expected_duration = sum(e.duration_minutes for e in plan.experiments) / 60
        assert plan.estimated_duration_hours == pytest.approx(expected_duration, rel=0.01)

    @pytest.mark.asyncio
    async def test_analyze_chaos_result_success(self, engineer):
        """Test analyzing successful chaos result"""
        experiment = ChaosExperiment(
            name="Test Experiment",
            type="network_latency",
            target="api",
            description="Test",
            hypothesis="Test",
            blast_radius="limited",
            risk_level="low",
            duration_minutes=10,
            rollback_plan="Rollback",
            success_criteria=["Latency < 1s"],
            commands=[]
        )

        metrics_before = {"latency_ms": 50, "error_rate": 0.1}
        metrics_after = {"latency_ms": 55, "error_rate": 0.15}
        logs = ["INFO: Request completed", "INFO: Health check passed"]

        result = await engineer.analyze_chaos_result(
            experiment=experiment,
            metrics_before=metrics_before,
            metrics_after=metrics_after,
            logs=logs
        )

        assert result.status == "success"
        assert result.system_resilience in ["excellent", "good"]
        assert len(result.issues_found) == 0

    @pytest.mark.asyncio
    async def test_analyze_chaos_result_with_errors(self, engineer):
        """Test analyzing chaos result with errors"""
        experiment = ChaosExperiment(
            name="Test Experiment",
            type="network_latency",
            target="api",
            description="Test",
            hypothesis="Test",
            blast_radius="limited",
            risk_level="low",
            duration_minutes=10,
            rollback_plan="Rollback",
            success_criteria=[],
            commands=[]
        )

        metrics_before = {"latency_ms": 50}
        metrics_after = {"latency_ms": 500}  # 10x increase
        logs = ["ERROR: Connection timeout"] * 15  # Many errors

        result = await engineer.analyze_chaos_result(
            experiment=experiment,
            metrics_before=metrics_before,
            metrics_after=metrics_after,
            logs=logs
        )

        assert result.status == "partial"
        assert len(result.issues_found) > 0
        assert len(result.recommendations) > 0

    @pytest.mark.asyncio
    async def test_analyze_chaos_result_metrics_impact(self, engineer):
        """Test metrics impact calculation"""
        experiment = ChaosExperiment(
            name="Test",
            type="test",
            target="target",
            description="Test",
            hypothesis="Test",
            blast_radius="limited",
            risk_level="low",
            duration_minutes=5,
            rollback_plan="Rollback",
            success_criteria=[],
            commands=[]
        )

        metrics_before = {"latency_ms": 100, "throughput": 1000}
        metrics_after = {"latency_ms": 200, "throughput": 800}

        result = await engineer.analyze_chaos_result(
            experiment=experiment,
            metrics_before=metrics_before,
            metrics_after=metrics_after,
            logs=[]
        )

        assert "latency_ms" in result.metrics_impact
        assert result.metrics_impact["latency_ms"]["before"] == 100
        assert result.metrics_impact["latency_ms"]["after"] == 200
        assert result.metrics_impact["latency_ms"]["change_pct"] == 100.0

    @pytest.mark.asyncio
    async def test_analyze_chaos_result_large_change(self, engineer):
        """Test detection of large metric changes"""
        experiment = ChaosExperiment(
            name="Test",
            type="test",
            target="target",
            description="Test",
            hypothesis="Test",
            blast_radius="limited",
            risk_level="low",
            duration_minutes=5,
            rollback_plan="Rollback",
            success_criteria=[],
            commands=[]
        )

        metrics_before = {"error_rate": 0.1}
        metrics_after = {"error_rate": 5.0}  # 50x increase

        result = await engineer.analyze_chaos_result(
            experiment=experiment,
            metrics_before=metrics_before,
            metrics_after=metrics_after,
            logs=[]
        )

        # Should observe the large change
        assert any("error_rate" in obs for obs in result.observations)

    @pytest.mark.asyncio
    async def test_analyze_chaos_result_resilience_levels(self, engineer):
        """Test resilience level determination"""
        experiment = ChaosExperiment(
            name="Test",
            type="test",
            target="target",
            description="Test",
            hypothesis="Test",
            blast_radius="limited",
            risk_level="low",
            duration_minutes=5,
            rollback_plan="Rollback",
            success_criteria=[],
            commands=[]
        )

        # Excellent - no errors
        result = await engineer.analyze_chaos_result(
            experiment=experiment,
            metrics_before={"latency": 50},
            metrics_after={"latency": 55},
            logs=[]
        )
        assert result.system_resilience == "excellent"

        # Fair/poor - many errors
        result = await engineer.analyze_chaos_result(
            experiment=experiment,
            metrics_before={"latency": 50},
            metrics_after={"latency": 500},
            logs=["ERROR: Failed"] * 20
        )
        assert result.system_resilience in ["fair", "poor"]

    @pytest.mark.asyncio
    async def test_analyze_chaos_result_duration(self, engineer):
        """Test duration calculation in result"""
        experiment = ChaosExperiment(
            name="Test",
            type="test",
            target="target",
            description="Test",
            hypothesis="Test",
            blast_radius="limited",
            risk_level="low",
            duration_minutes=15,
            rollback_plan="Rollback",
            success_criteria=[],
            commands=[]
        )

        result = await engineer.analyze_chaos_result(
            experiment=experiment,
            metrics_before={},
            metrics_after={},
            logs=[]
        )

        assert result.duration_seconds == 15 * 60

    @pytest.mark.asyncio
    async def test_analyze_chaos_result_zero_baseline(self, engineer):
        """Test handling of zero baseline metrics"""
        experiment = ChaosExperiment(
            name="Test",
            type="test",
            target="target",
            description="Test",
            hypothesis="Test",
            blast_radius="limited",
            risk_level="low",
            duration_minutes=5,
            rollback_plan="Rollback",
            success_criteria=[],
            commands=[]
        )

        # Zero baseline should not cause division by zero
        result = await engineer.analyze_chaos_result(
            experiment=experiment,
            metrics_before={"errors": 0},
            metrics_after={"errors": 5},
            logs=[]
        )

        assert result.metrics_impact["errors"]["change_pct"] == 0

    @pytest.mark.asyncio
    async def test_analyze_chaos_result_recommendations(self, engineer):
        """Test recommendations generation for poor resilience"""
        experiment = ChaosExperiment(
            name="Test",
            type="test",
            target="target",
            description="Test",
            hypothesis="Test",
            blast_radius="limited",
            risk_level="low",
            duration_minutes=5,
            rollback_plan="Rollback",
            success_criteria=[],
            commands=[]
        )

        # Many errors should generate recommendations
        result = await engineer.analyze_chaos_result(
            experiment=experiment,
            metrics_before={"latency": 50},
            metrics_after={"latency": 500},
            logs=["ERROR: Exception"] * 20
        )

        assert len(result.recommendations) > 0
        # Should recommend retry logic, health checks, etc.
        all_recs = " ".join(result.recommendations).lower()
        assert any(keyword in all_recs for keyword in ["retry", "health", "circuit", "autoscaling"])

    def test_engineer_initialization(self):
        """Test engineer initialization"""
        engineer = ChaosEngineer()
        assert engineer.llm_factory is None

        mock_factory = object()
        engineer_with_factory = ChaosEngineer(llm_factory=mock_factory)
        assert engineer_with_factory.llm_factory is mock_factory


class TestChaosEngineerEdgeCases:
    """Edge case tests for ChaosEngineer"""

    @pytest.fixture
    def engineer(self):
        return ChaosEngineer()

    @pytest.mark.asyncio
    async def test_very_long_service_names(self, engineer):
        """Test with very long service names"""
        long_name = "a" * 100
        plan = await engineer.create_chaos_plan(
            services=[long_name],
            environment="staging"
        )

        assert plan is not None
        assert any(long_name in e.target for e in plan.experiments)

    @pytest.mark.asyncio
    async def test_special_characters_in_service_names(self, engineer):
        """Test with special characters in service names"""
        plan = await engineer.create_chaos_plan(
            services=["my-service_v2.0"],
            environment="staging"
        )

        assert plan is not None

    @pytest.mark.asyncio
    async def test_many_services(self, engineer):
        """Test with many services"""
        services = [f"service-{i}" for i in range(20)]
        plan = await engineer.create_chaos_plan(
            services=services,
            environment="staging"
        )

        # Should have experiments for all services
        assert len(plan.experiments) >= len(services) * 2  # At least network + pod per service

    @pytest.mark.asyncio
    async def test_missing_metrics_in_after(self, engineer):
        """Test handling of missing metrics in after measurement"""
        experiment = ChaosExperiment(
            name="Test",
            type="test",
            target="target",
            description="Test",
            hypothesis="Test",
            blast_radius="limited",
            risk_level="low",
            duration_minutes=5,
            rollback_plan="Rollback",
            success_criteria=[],
            commands=[]
        )

        # Metric exists in before but not in after
        result = await engineer.analyze_chaos_result(
            experiment=experiment,
            metrics_before={"latency": 50, "throughput": 1000},
            metrics_after={"latency": 60},  # throughput missing
            logs=[]
        )

        # Should use before value as fallback
        assert result.metrics_impact["throughput"]["after"] == 1000

    @pytest.mark.asyncio
    async def test_empty_logs(self, engineer):
        """Test with empty logs"""
        experiment = ChaosExperiment(
            name="Test",
            type="test",
            target="target",
            description="Test",
            hypothesis="Test",
            blast_radius="limited",
            risk_level="low",
            duration_minutes=5,
            rollback_plan="Rollback",
            success_criteria=[],
            commands=[]
        )

        result = await engineer.analyze_chaos_result(
            experiment=experiment,
            metrics_before={},
            metrics_after={},
            logs=[]
        )

        assert result.system_resilience == "excellent"

    @pytest.mark.asyncio
    async def test_case_insensitive_error_detection(self, engineer):
        """Test case insensitive error detection in logs"""
        experiment = ChaosExperiment(
            name="Test",
            type="test",
            target="target",
            description="Test",
            hypothesis="Test",
            blast_radius="limited",
            risk_level="low",
            duration_minutes=5,
            rollback_plan="Rollback",
            success_criteria=[],
            commands=[]
        )

        # Mixed case errors
        logs = ["ERROR: fail", "Error: timeout", "EXCEPTION raised", "exception caught"] * 5

        result = await engineer.analyze_chaos_result(
            experiment=experiment,
            metrics_before={},
            metrics_after={},
            logs=logs
        )

        # Should detect all error variants
        assert len(result.issues_found) > 0
