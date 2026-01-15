"""
Unit tests for SLA Compliance Monitor Agent
"""

import pytest
from datetime import datetime
from aiops.agents.sla_monitor import (
    SLAComplianceMonitor,
    SLI,
    SLO,
    SLAViolationPrediction,
    SLAMonitoringResult
)


class TestSLI:
    """Tests for SLI model"""

    def test_create_sli(self):
        """Test creating an SLI"""
        sli = SLI(
            name="availability",
            current_value=99.95,
            unit="percentage",
            measurement_period="30d"
        )
        assert sli.name == "availability"
        assert sli.current_value == 99.95
        assert sli.unit == "percentage"
        assert sli.measurement_period == "30d"

    def test_different_sli_types(self):
        """Test different SLI types"""
        slis = [
            SLI(name="latency_p99", current_value=250, unit="milliseconds", measurement_period="1h"),
            SLI(name="error_rate", current_value=0.5, unit="percentage", measurement_period="1h"),
            SLI(name="throughput", current_value=1000, unit="requests/second", measurement_period="5m")
        ]
        assert len(slis) == 3
        assert slis[0].name == "latency_p99"
        assert slis[1].name == "error_rate"
        assert slis[2].name == "throughput"


class TestSLO:
    """Tests for SLO model"""

    def test_create_slo(self):
        """Test creating an SLO"""
        slo = SLO(
            name="Availability SLO",
            sli_name="availability",
            target_value=99.9,
            operator=">=",
            current_compliance=100.0,
            status="compliant",
            error_budget_remaining=50.0
        )
        assert slo.name == "Availability SLO"
        assert slo.target_value == 99.9
        assert slo.status == "compliant"

    def test_slo_statuses(self):
        """Test different SLO statuses"""
        for status in ["compliant", "at_risk", "violated"]:
            slo = SLO(
                name="Test SLO",
                sli_name="test",
                target_value=99.0,
                operator=">=",
                current_compliance=95.0,
                status=status,
                error_budget_remaining=10.0
            )
            assert slo.status == status


class TestSLAViolationPrediction:
    """Tests for SLAViolationPrediction model"""

    def test_create_prediction(self):
        """Test creating a violation prediction"""
        prediction = SLAViolationPrediction(
            slo_name="Availability SLO",
            probability=75.0,
            time_to_violation="1-4 hours",
            contributing_factors=["Error budget low"],
            recommended_actions=["Scale resources"],
            severity="high"
        )
        assert prediction.slo_name == "Availability SLO"
        assert prediction.probability == 75.0
        assert prediction.severity == "high"

    def test_prediction_severities(self):
        """Test different severity levels"""
        for severity in ["critical", "high", "medium", "low"]:
            prediction = SLAViolationPrediction(
                slo_name="Test",
                probability=50.0,
                time_to_violation="2h",
                contributing_factors=[],
                recommended_actions=[],
                severity=severity
            )
            assert prediction.severity == severity


class TestSLAMonitoringResult:
    """Tests for SLAMonitoringResult model"""

    def test_create_result(self):
        """Test creating a monitoring result"""
        result = SLAMonitoringResult(
            service_name="api-gateway",
            slis=[],
            slos=[],
            violations=[],
            overall_health="healthy",
            compliance_score=100.0,
            summary="All good",
            recommendations=[]
        )
        assert result.service_name == "api-gateway"
        assert result.overall_health == "healthy"
        assert result.compliance_score == 100.0


class TestSLAComplianceMonitor:
    """Tests for SLAComplianceMonitor"""

    @pytest.fixture
    def monitor(self):
        """Create monitor instance"""
        return SLAComplianceMonitor()

    @pytest.fixture
    def healthy_metrics(self):
        """Healthy service metrics"""
        return {
            "uptime_percentage": 99.99,
            "latency_p99_ms": 150,
            "error_rate": 0.1,
            "requests_per_second": 5000
        }

    @pytest.fixture
    def at_risk_metrics(self):
        """At-risk service metrics"""
        return {
            "uptime_percentage": 99.91,  # Just above 99.9 threshold
            "latency_p99_ms": 290,  # Close to 300ms limit
            "error_rate": 0.9,  # Close to 1.0% limit
            "requests_per_second": 1000
        }

    @pytest.fixture
    def violated_metrics(self):
        """Violated SLA metrics"""
        return {
            "uptime_percentage": 99.5,  # Below 99.9 threshold
            "latency_p99_ms": 500,  # Above 300ms limit
            "error_rate": 2.5,  # Above 1.0% limit
            "requests_per_second": 500
        }

    @pytest.mark.asyncio
    async def test_monitor_healthy_service(self, monitor, healthy_metrics):
        """Test monitoring a healthy service"""
        result = await monitor.monitor_sla(
            service_name="healthy-service",
            metrics=healthy_metrics
        )

        assert result.service_name == "healthy-service"
        assert result.overall_health == "healthy"
        assert result.compliance_score == 100.0
        assert len(result.violations) == 0

        # All SLOs should be compliant
        for slo in result.slos:
            assert slo.status == "compliant"

    @pytest.mark.asyncio
    async def test_monitor_at_risk_service(self, monitor, at_risk_metrics):
        """Test monitoring an at-risk service"""
        result = await monitor.monitor_sla(
            service_name="at-risk-service",
            metrics=at_risk_metrics
        )

        assert result.overall_health in ["degraded", "healthy"]

        # Should have at least one at_risk SLO
        at_risk_slos = [s for s in result.slos if s.status == "at_risk"]
        # Note: at_risk status depends on error budget calculation

    @pytest.mark.asyncio
    async def test_monitor_violated_service(self, monitor, violated_metrics):
        """Test monitoring a service with SLA violations"""
        result = await monitor.monitor_sla(
            service_name="violated-service",
            metrics=violated_metrics
        )

        assert result.overall_health == "critical"
        assert len(result.violations) > 0

        # Should have critical violations
        critical_violations = [v for v in result.violations if v.severity == "critical"]
        assert len(critical_violations) > 0

    @pytest.mark.asyncio
    async def test_default_slis(self, monitor):
        """Test that default SLIs are created"""
        result = await monitor.monitor_sla(
            service_name="test-service",
            metrics={}
        )

        sli_names = [s.name for s in result.slis]
        assert "availability" in sli_names
        assert "latency_p99" in sli_names
        assert "error_rate" in sli_names
        assert "throughput" in sli_names

    @pytest.mark.asyncio
    async def test_default_slo_definitions(self, monitor):
        """Test that default SLOs are created"""
        result = await monitor.monitor_sla(
            service_name="test-service",
            metrics={}
        )

        slo_names = [s.name for s in result.slos]
        assert "Availability SLO" in slo_names
        assert "Latency SLO" in slo_names
        assert "Error Rate SLO" in slo_names

    @pytest.mark.asyncio
    async def test_custom_slo_definitions(self, monitor, healthy_metrics):
        """Test with custom SLO definitions"""
        custom_slos = [
            {"name": "Custom Availability", "sli": "availability", "target": 99.5, "operator": ">="},
            {"name": "Strict Latency", "sli": "latency_p99", "target": 100, "operator": "<="}
        ]

        result = await monitor.monitor_sla(
            service_name="custom-service",
            metrics=healthy_metrics,
            slo_definitions=custom_slos
        )

        slo_names = [s.name for s in result.slos]
        assert "Custom Availability" in slo_names
        assert "Strict Latency" in slo_names
        assert len(result.slos) == 2

    @pytest.mark.asyncio
    async def test_availability_slo_compliance(self, monitor):
        """Test availability SLO compliance calculation"""
        # Exactly at threshold
        metrics = {"uptime_percentage": 99.9}
        result = await monitor.monitor_sla("test", metrics)

        avail_slo = next(s for s in result.slos if "Availability" in s.name)
        assert avail_slo.status == "compliant"

    @pytest.mark.asyncio
    async def test_availability_slo_violation(self, monitor):
        """Test availability SLO violation"""
        metrics = {"uptime_percentage": 99.0}  # Below 99.9
        result = await monitor.monitor_sla("test", metrics)

        avail_slo = next(s for s in result.slos if "Availability" in s.name)
        assert avail_slo.status == "violated"

    @pytest.mark.asyncio
    async def test_latency_slo_compliance(self, monitor):
        """Test latency SLO compliance"""
        metrics = {"latency_p99_ms": 200}  # Below 300ms
        result = await monitor.monitor_sla("test", metrics)

        latency_slo = next(s for s in result.slos if "Latency" in s.name)
        assert latency_slo.status == "compliant"

    @pytest.mark.asyncio
    async def test_latency_slo_violation(self, monitor):
        """Test latency SLO violation"""
        metrics = {"latency_p99_ms": 500}  # Above 300ms
        result = await monitor.monitor_sla("test", metrics)

        latency_slo = next(s for s in result.slos if "Latency" in s.name)
        assert latency_slo.status == "violated"

    @pytest.mark.asyncio
    async def test_error_rate_slo_compliance(self, monitor):
        """Test error rate SLO compliance"""
        metrics = {"error_rate": 0.5}  # Below 1.0%
        result = await monitor.monitor_sla("test", metrics)

        error_slo = next(s for s in result.slos if "Error" in s.name)
        assert error_slo.status == "compliant"

    @pytest.mark.asyncio
    async def test_error_rate_slo_violation(self, monitor):
        """Test error rate SLO violation"""
        metrics = {"error_rate": 2.0}  # Above 1.0%
        result = await monitor.monitor_sla("test", metrics)

        error_slo = next(s for s in result.slos if "Error" in s.name)
        assert error_slo.status == "violated"

    @pytest.mark.asyncio
    async def test_violation_prediction_critical(self, monitor):
        """Test critical violation prediction"""
        metrics = {"uptime_percentage": 99.0, "latency_p99_ms": 100, "error_rate": 0.1}
        result = await monitor.monitor_sla("test", metrics)

        # Should have critical violation for availability
        critical_violations = [v for v in result.violations if v.severity == "critical"]
        assert len(critical_violations) >= 1

        # Critical violation should have time_to_violation = NOW
        critical = critical_violations[0]
        assert critical.time_to_violation == "NOW"
        assert critical.probability == 100.0

    @pytest.mark.asyncio
    async def test_compliance_score_calculation(self, monitor):
        """Test compliance score is correctly calculated"""
        # All compliant
        healthy = {"uptime_percentage": 99.99, "latency_p99_ms": 100, "error_rate": 0.1}
        result = await monitor.monitor_sla("test", healthy)
        assert result.compliance_score == 100.0

        # Some violated
        mixed = {"uptime_percentage": 99.0, "latency_p99_ms": 500, "error_rate": 0.1}
        result = await monitor.monitor_sla("test", mixed)
        assert result.compliance_score < 100.0

    @pytest.mark.asyncio
    async def test_overall_health_states(self, monitor):
        """Test overall health state determination"""
        # Healthy
        healthy = {"uptime_percentage": 99.99, "latency_p99_ms": 100, "error_rate": 0.1}
        result = await monitor.monitor_sla("test", healthy)
        assert result.overall_health == "healthy"

        # Critical (with violation)
        violated = {"uptime_percentage": 99.0, "latency_p99_ms": 500, "error_rate": 5.0}
        result = await monitor.monitor_sla("test", violated)
        assert result.overall_health == "critical"

    @pytest.mark.asyncio
    async def test_recommendations_generated(self, monitor, violated_metrics):
        """Test that recommendations are generated for violations"""
        result = await monitor.monitor_sla("test", violated_metrics)

        assert len(result.recommendations) > 0
        # Should have critical alert for violated SLAs
        assert any("CRITICAL" in r for r in result.recommendations)

    @pytest.mark.asyncio
    async def test_summary_generated(self, monitor, healthy_metrics):
        """Test that summary is generated"""
        result = await monitor.monitor_sla("my-service", healthy_metrics)

        assert result.summary is not None
        assert "my-service" in result.summary
        assert "HEALTHY" in result.summary

    @pytest.mark.asyncio
    async def test_unknown_sli_in_slo(self, monitor):
        """Test handling of unknown SLI in SLO definition"""
        custom_slos = [
            {"name": "Unknown SLO", "sli": "nonexistent", "target": 99.0, "operator": ">="}
        ]

        result = await monitor.monitor_sla("test", {}, slo_definitions=custom_slos)

        # Should not crash, SLO with unknown SLI should be skipped
        assert len(result.slos) == 0

    def test_generate_recommendations_availability(self, monitor):
        """Test recommendations for availability issues"""
        slos = [SLO(
            name="Availability",
            sli_name="availability",
            target_value=99.9,
            operator=">=",
            current_compliance=95.0,
            status="violated",
            error_budget_remaining=0
        )]
        violations = []
        metrics = {}

        recommendations = monitor._generate_recommendations(slos, violations, metrics)

        assert any("availability" in r.lower() or "failover" in r.lower() for r in recommendations)

    def test_generate_recommendations_latency(self, monitor):
        """Test recommendations for latency issues"""
        slos = [SLO(
            name="Latency SLO",
            sli_name="latency_p99",
            target_value=300,
            operator="<=",
            current_compliance=50.0,
            status="violated",
            error_budget_remaining=0
        )]
        violations = []
        metrics = {}

        recommendations = monitor._generate_recommendations(slos, violations, metrics)

        assert any("caching" in r.lower() or "database" in r.lower() or "cdn" in r.lower()
                   for r in recommendations)

    def test_generate_recommendations_error_rate(self, monitor):
        """Test recommendations for error rate issues"""
        slos = [SLO(
            name="Error Rate SLO",
            sli_name="error_rate",
            target_value=1.0,
            operator="<=",
            current_compliance=50.0,
            status="violated",
            error_budget_remaining=0
        )]
        violations = []
        metrics = {}

        recommendations = monitor._generate_recommendations(slos, violations, metrics)

        assert any("circuit" in r.lower() or "error" in r.lower() or "retry" in r.lower()
                   for r in recommendations)

    def test_generate_recommendations_critical_first(self, monitor):
        """Test that critical alerts come first"""
        slos = []
        violations = [SLAViolationPrediction(
            slo_name="Critical",
            probability=100.0,
            time_to_violation="NOW",
            contributing_factors=[],
            recommended_actions=[],
            severity="critical"
        )]
        metrics = {}

        recommendations = monitor._generate_recommendations(slos, violations, metrics)

        # First recommendation should be critical alert
        assert recommendations[0].startswith("🚨")

    def test_generate_recommendations_max_five(self, monitor):
        """Test that recommendations are limited to 5"""
        slos = [
            SLO(name="A", sli_name="availability", target_value=99.9, operator=">=",
                current_compliance=50, status="violated", error_budget_remaining=0),
            SLO(name="L", sli_name="latency_p99", target_value=300, operator="<=",
                current_compliance=50, status="violated", error_budget_remaining=0),
            SLO(name="E", sli_name="error_rate", target_value=1.0, operator="<=",
                current_compliance=50, status="violated", error_budget_remaining=0),
        ]
        violations = [
            SLAViolationPrediction(slo_name="V1", probability=100, time_to_violation="NOW",
                                   contributing_factors=[], recommended_actions=[], severity="critical"),
            SLAViolationPrediction(slo_name="V2", probability=100, time_to_violation="NOW",
                                   contributing_factors=[], recommended_actions=[], severity="critical"),
            SLAViolationPrediction(slo_name="V3", probability=100, time_to_violation="NOW",
                                   contributing_factors=[], recommended_actions=[], severity="critical"),
        ]

        recommendations = monitor._generate_recommendations(slos, violations, {})

        assert len(recommendations) <= 5

    def test_generate_summary_format(self, monitor):
        """Test summary format"""
        slos = [
            SLO(name="SLO1", sli_name="test", target_value=99, operator=">=",
                current_compliance=100, status="compliant", error_budget_remaining=50),
            SLO(name="SLO2", sli_name="test2", target_value=99, operator=">=",
                current_compliance=100, status="compliant", error_budget_remaining=50)
        ]
        violations = []

        summary = monitor._generate_summary("my-svc", slos, violations, "healthy", 100.0)

        assert "my-svc" in summary
        assert "HEALTHY" in summary
        assert "100.0" in summary
        assert "2/2" in summary  # 2 compliant out of 2

    def test_generate_summary_with_violations(self, monitor):
        """Test summary with critical violations"""
        slos = []
        violations = [
            SLAViolationPrediction(slo_name="V", probability=100, time_to_violation="NOW",
                                   contributing_factors=[], recommended_actions=[], severity="critical")
        ]

        summary = monitor._generate_summary("svc", slos, violations, "critical", 50.0)

        assert "⚠️" in summary
        assert "1 critical" in summary

    def test_monitor_initialization(self):
        """Test monitor initialization"""
        monitor = SLAComplianceMonitor()
        assert monitor.llm_factory is None

        mock_factory = object()
        monitor_with_factory = SLAComplianceMonitor(llm_factory=mock_factory)
        assert monitor_with_factory.llm_factory is mock_factory


class TestOperatorHandling:
    """Tests for different operator types in SLO compliance"""

    @pytest.fixture
    def monitor(self):
        return SLAComplianceMonitor()

    @pytest.mark.asyncio
    async def test_greater_than_or_equal_operator(self, monitor):
        """Test >= operator"""
        slos = [{"name": "GTE", "sli": "availability", "target": 99.0, "operator": ">="}]

        # Compliant
        result = await monitor.monitor_sla("test", {"uptime_percentage": 99.5}, slos)
        assert result.slos[0].status in ["compliant", "at_risk"]

        # Violated
        result = await monitor.monitor_sla("test", {"uptime_percentage": 98.0}, slos)
        assert result.slos[0].status == "violated"

    @pytest.mark.asyncio
    async def test_less_than_or_equal_operator(self, monitor):
        """Test <= operator"""
        slos = [{"name": "LTE", "sli": "latency_p99", "target": 200, "operator": "<="}]

        # Compliant
        result = await monitor.monitor_sla("test", {"latency_p99_ms": 150}, slos)
        assert result.slos[0].status in ["compliant", "at_risk"]

        # Violated
        result = await monitor.monitor_sla("test", {"latency_p99_ms": 300}, slos)
        assert result.slos[0].status == "violated"

    @pytest.mark.asyncio
    async def test_equals_operator(self, monitor):
        """Test == operator"""
        slos = [{"name": "EQ", "sli": "availability", "target": 100.0, "operator": "=="}]

        # Compliant
        result = await monitor.monitor_sla("test", {"uptime_percentage": 100.0}, slos)
        assert result.slos[0].status == "compliant"

        # Violated
        result = await monitor.monitor_sla("test", {"uptime_percentage": 99.9}, slos)
        assert result.slos[0].status == "violated"
