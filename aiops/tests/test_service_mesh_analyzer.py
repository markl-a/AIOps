"""
Unit tests for Service Mesh Analyzer Agent
"""

import pytest
from datetime import datetime
from aiops.agents.service_mesh_analyzer import (
    ServiceMeshAnalyzer,
    ServiceMeshMetric,
    MeshOptimization,
    ServiceMeshAnalysisResult
)


class TestServiceMeshMetric:
    """Tests for ServiceMeshMetric model"""

    def test_create_metric(self):
        """Test creating a service mesh metric"""
        metric = ServiceMeshMetric(
            service_name="api-gateway",
            metric_type="p99_latency",
            value=150.5,
            unit="ms",
            status="healthy"
        )
        assert metric.service_name == "api-gateway"
        assert metric.metric_type == "p99_latency"
        assert metric.value == 150.5
        assert metric.unit == "ms"
        assert metric.status == "healthy"

    def test_metric_with_different_statuses(self):
        """Test metrics with different status values"""
        for status in ["healthy", "warning", "critical"]:
            metric = ServiceMeshMetric(
                service_name="test-service",
                metric_type="success_rate",
                value=99.9,
                unit="percentage",
                status=status
            )
            assert metric.status == status


class TestMeshOptimization:
    """Tests for MeshOptimization model"""

    def test_create_optimization(self):
        """Test creating a mesh optimization"""
        optimization = MeshOptimization(
            optimization_type="circuit_breaker",
            service_name="payment-service",
            current_config={"enabled": False},
            recommended_config={
                "consecutive_errors": 5,
                "interval": "10s",
                "base_ejection_time": "30s"
            },
            expected_benefit="Prevent cascading failures",
            priority="high",
            implementation="Apply Istio DestinationRule"
        )
        assert optimization.optimization_type == "circuit_breaker"
        assert optimization.service_name == "payment-service"
        assert optimization.priority == "high"

    def test_optimization_priorities(self):
        """Test different optimization priorities"""
        for priority in ["critical", "high", "medium", "low"]:
            optimization = MeshOptimization(
                optimization_type="retry_policy",
                service_name="test-service",
                current_config={},
                recommended_config={"attempts": 3},
                expected_benefit="Improve reliability",
                priority=priority,
                implementation="Configure retry policy"
            )
            assert optimization.priority == priority


class TestServiceMeshAnalysisResult:
    """Tests for ServiceMeshAnalysisResult model"""

    def test_create_result(self):
        """Test creating analysis result"""
        result = ServiceMeshAnalysisResult(
            mesh_type="istio",
            services_analyzed=5,
            metrics=[],
            optimizations=[],
            health_score=95.0,
            summary="All services healthy",
            topology_insights=["5 services in mesh"]
        )
        assert result.mesh_type == "istio"
        assert result.services_analyzed == 5
        assert result.health_score == 95.0

    def test_result_with_metrics_and_optimizations(self):
        """Test result with metrics and optimizations"""
        metric = ServiceMeshMetric(
            service_name="api",
            metric_type="latency",
            value=100,
            unit="ms",
            status="healthy"
        )
        optimization = MeshOptimization(
            optimization_type="security",
            service_name="api",
            current_config={},
            recommended_config={"mtls": "STRICT"},
            expected_benefit="Better security",
            priority="high",
            implementation="Enable mTLS"
        )
        result = ServiceMeshAnalysisResult(
            mesh_type="linkerd",
            services_analyzed=1,
            metrics=[metric],
            optimizations=[optimization],
            health_score=100.0,
            summary="Analysis complete",
            topology_insights=[]
        )
        assert len(result.metrics) == 1
        assert len(result.optimizations) == 1


class TestServiceMeshAnalyzer:
    """Tests for ServiceMeshAnalyzer"""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance"""
        return ServiceMeshAnalyzer()

    @pytest.fixture
    def healthy_mesh_config(self):
        """Healthy mesh configuration"""
        return {
            "services": [
                {
                    "name": "api-gateway",
                    "mtls_enabled": True,
                    "resilience": {"circuit_breaker": True}
                },
                {
                    "name": "user-service",
                    "mtls_enabled": True,
                    "resilience": {"circuit_breaker": True}
                }
            ],
            "dependencies": {
                "api-gateway": ["user-service"]
            }
        }

    @pytest.fixture
    def healthy_traffic_metrics(self):
        """Healthy traffic metrics"""
        return {
            "api-gateway": {
                "p99_latency_ms": 50,
                "success_rate": 99.9
            },
            "user-service": {
                "p99_latency_ms": 30,
                "success_rate": 99.95
            }
        }

    @pytest.fixture
    def unhealthy_mesh_config(self):
        """Unhealthy mesh configuration"""
        return {
            "services": [
                {
                    "name": "slow-service",
                    "mtls_enabled": False,
                    "versions": ["v1", "v2"]
                },
                {
                    "name": "failing-service",
                    "mtls_enabled": False
                }
            ],
            "dependencies": {
                "slow-service": ["failing-service"]
            }
        }

    @pytest.fixture
    def unhealthy_traffic_metrics(self):
        """Unhealthy traffic metrics"""
        return {
            "slow-service": {
                "p99_latency_ms": 600,
                "success_rate": 98.5
            },
            "failing-service": {
                "p99_latency_ms": 800,
                "success_rate": 95.0
            }
        }

    @pytest.mark.asyncio
    async def test_analyze_healthy_mesh(self, analyzer, healthy_mesh_config, healthy_traffic_metrics):
        """Test analyzing a healthy service mesh"""
        result = await analyzer.analyze_mesh(
            mesh_config=healthy_mesh_config,
            traffic_metrics=healthy_traffic_metrics,
            mesh_type="istio"
        )

        assert result.mesh_type == "istio"
        assert result.services_analyzed == 2
        assert result.health_score == 100.0
        assert len(result.metrics) == 4  # 2 services * 2 metrics each

        # All metrics should be healthy
        for metric in result.metrics:
            assert metric.status == "healthy"

    @pytest.mark.asyncio
    async def test_analyze_unhealthy_mesh(self, analyzer, unhealthy_mesh_config, unhealthy_traffic_metrics):
        """Test analyzing an unhealthy service mesh"""
        result = await analyzer.analyze_mesh(
            mesh_config=unhealthy_mesh_config,
            traffic_metrics=unhealthy_traffic_metrics,
            mesh_type="istio"
        )

        assert result.services_analyzed == 2
        assert result.health_score < 100.0

        # Should have optimizations for mTLS, circuit breaker, retry policy
        assert len(result.optimizations) > 0

        # Check for security optimization (mTLS)
        security_opts = [o for o in result.optimizations if o.optimization_type == "security"]
        assert len(security_opts) >= 2  # Both services missing mTLS

    @pytest.mark.asyncio
    async def test_analyze_mesh_with_high_latency(self, analyzer):
        """Test detection of high latency services"""
        config = {
            "services": [{"name": "high-latency-svc", "mtls_enabled": True}]
        }
        metrics = {
            "high-latency-svc": {"p99_latency_ms": 550, "success_rate": 99.9}
        }

        result = await analyzer.analyze_mesh(config, metrics)

        # Should detect critical latency
        latency_metrics = [m for m in result.metrics if m.metric_type == "p99_latency"]
        assert latency_metrics[0].status == "critical"

        # Should recommend circuit breaker
        circuit_opts = [o for o in result.optimizations if o.optimization_type == "circuit_breaker"]
        assert len(circuit_opts) == 1

    @pytest.mark.asyncio
    async def test_analyze_mesh_with_low_success_rate(self, analyzer):
        """Test detection of low success rate"""
        config = {
            "services": [{"name": "failing-svc", "mtls_enabled": True}]
        }
        metrics = {
            "failing-svc": {"p99_latency_ms": 100, "success_rate": 98.0}
        }

        result = await analyzer.analyze_mesh(config, metrics)

        # Should detect critical success rate
        success_metrics = [m for m in result.metrics if m.metric_type == "success_rate"]
        assert success_metrics[0].status == "critical"

        # Should recommend retry policy
        retry_opts = [o for o in result.optimizations if o.optimization_type == "retry_policy"]
        assert len(retry_opts) == 1

    @pytest.mark.asyncio
    async def test_analyze_mesh_with_multiple_versions(self, analyzer):
        """Test detection of canary deployment opportunity"""
        config = {
            "services": [
                {
                    "name": "canary-svc",
                    "mtls_enabled": True,
                    "versions": ["v1", "v2"]
                }
            ]
        }
        metrics = {"canary-svc": {"p99_latency_ms": 50, "success_rate": 99.9}}

        result = await analyzer.analyze_mesh(config, metrics)

        # Should recommend traffic split
        traffic_opts = [o for o in result.optimizations if o.optimization_type == "traffic_split"]
        assert len(traffic_opts) == 1

        # Should have topology insight about versions
        assert any("versions" in insight for insight in result.topology_insights)

    @pytest.mark.asyncio
    async def test_detect_single_point_of_failure(self, analyzer):
        """Test detection of single points of failure"""
        config = {
            "services": [
                {"name": "frontend", "mtls_enabled": True},
                {"name": "backend", "mtls_enabled": True}
            ],
            "dependencies": {
                "frontend": ["backend"]  # Single dependency = SPOF
            }
        }
        metrics = {
            "frontend": {"p99_latency_ms": 50, "success_rate": 99.9},
            "backend": {"p99_latency_ms": 50, "success_rate": 99.9}
        }

        result = await analyzer.analyze_mesh(config, metrics)

        # Should detect SPOF
        spof_insights = [i for i in result.topology_insights if "SPOF" in i]
        assert len(spof_insights) == 1

    @pytest.mark.asyncio
    async def test_detect_deep_call_chains(self, analyzer):
        """Test detection of deep call chains"""
        config = {
            "services": [
                {"name": f"service-{i}", "mtls_enabled": True}
                for i in range(7)
            ],
            "dependencies": {
                "service-0": ["service-1"],
                "service-1": ["service-2"],
                "service-2": ["service-3"],
                "service-3": ["service-4"],
                "service-4": ["service-5"],
                "service-5": ["service-6"]
            }
        }
        metrics = {
            f"service-{i}": {"p99_latency_ms": 50, "success_rate": 99.9}
            for i in range(7)
        }

        result = await analyzer.analyze_mesh(config, metrics)

        # Should detect deep call chain
        depth_insights = [i for i in result.topology_insights if "depth" in i.lower()]
        assert len(depth_insights) == 1

        # Should recommend architecture optimization
        arch_opts = [o for o in result.optimizations if o.optimization_type == "architecture"]
        assert len(arch_opts) == 1

    @pytest.mark.asyncio
    async def test_analyze_empty_mesh(self, analyzer):
        """Test analyzing empty mesh configuration"""
        result = await analyzer.analyze_mesh(
            mesh_config={"services": []},
            traffic_metrics={}
        )

        assert result.services_analyzed == 0
        assert result.health_score == 100.0
        assert len(result.metrics) == 0
        assert len(result.optimizations) == 0

    @pytest.mark.asyncio
    async def test_different_mesh_types(self, analyzer):
        """Test analysis with different mesh types"""
        config = {"services": [{"name": "test", "mtls_enabled": True}]}
        metrics = {"test": {"p99_latency_ms": 50, "success_rate": 99.9}}

        for mesh_type in ["istio", "linkerd", "consul"]:
            result = await analyzer.analyze_mesh(config, metrics, mesh_type=mesh_type)
            assert result.mesh_type == mesh_type
            assert mesh_type in result.summary.lower()

    @pytest.mark.asyncio
    async def test_missing_traffic_metrics(self, analyzer):
        """Test handling of missing traffic metrics"""
        config = {
            "services": [{"name": "unknown-svc", "mtls_enabled": True}]
        }
        metrics = {}  # No metrics available

        result = await analyzer.analyze_mesh(config, metrics)

        # Should use defaults and still analyze
        assert result.services_analyzed == 1
        assert len(result.metrics) == 2  # latency and success_rate

    def test_calculate_max_depth_simple(self, analyzer):
        """Test max depth calculation for simple chain"""
        dependencies = {
            "a": ["b"],
            "b": ["c"],
            "c": []
        }
        depth = analyzer._calculate_max_depth(dependencies)
        assert depth == 3

    def test_calculate_max_depth_branching(self, analyzer):
        """Test max depth calculation with branching"""
        dependencies = {
            "a": ["b", "c"],
            "b": ["d"],
            "c": ["d", "e"],
            "d": [],
            "e": []
        }
        depth = analyzer._calculate_max_depth(dependencies)
        assert depth == 3

    def test_calculate_max_depth_empty(self, analyzer):
        """Test max depth with empty dependencies"""
        depth = analyzer._calculate_max_depth({})
        assert depth == 0

    def test_calculate_max_depth_with_cycle(self, analyzer):
        """Test max depth handles cycles gracefully"""
        dependencies = {
            "a": ["b"],
            "b": ["c"],
            "c": ["a"]  # Cycle back to a
        }
        # Should not infinite loop
        depth = analyzer._calculate_max_depth(dependencies)
        assert depth >= 0

    def test_generate_summary_healthy(self, analyzer):
        """Test summary generation for healthy mesh"""
        summary = analyzer._generate_summary("istio", 5, 95.0, 2)

        assert "istio" in summary.lower()
        assert "5" in summary
        assert "95.0" in summary
        assert "✓" in summary

    def test_generate_summary_warning(self, analyzer):
        """Test summary generation for warning state"""
        summary = analyzer._generate_summary("linkerd", 3, 75.0, 5)

        assert "⚠" in summary

    def test_generate_summary_critical(self, analyzer):
        """Test summary generation for critical state"""
        summary = analyzer._generate_summary("consul", 10, 50.0, 15)

        assert "✗" in summary

    def test_analyzer_initialization(self):
        """Test analyzer initialization"""
        analyzer = ServiceMeshAnalyzer()
        assert analyzer.llm_factory is None

        mock_factory = object()
        analyzer_with_factory = ServiceMeshAnalyzer(llm_factory=mock_factory)
        assert analyzer_with_factory.llm_factory is mock_factory


class TestLatencyThresholds:
    """Tests for latency threshold detection"""

    @pytest.fixture
    def analyzer(self):
        return ServiceMeshAnalyzer()

    @pytest.mark.asyncio
    async def test_latency_healthy_threshold(self, analyzer):
        """Test healthy latency threshold (<200ms)"""
        config = {"services": [{"name": "fast", "mtls_enabled": True}]}
        metrics = {"fast": {"p99_latency_ms": 199, "success_rate": 99.9}}

        result = await analyzer.analyze_mesh(config, metrics)
        latency_metric = [m for m in result.metrics if m.metric_type == "p99_latency"][0]
        assert latency_metric.status == "healthy"

    @pytest.mark.asyncio
    async def test_latency_warning_threshold(self, analyzer):
        """Test warning latency threshold (200-500ms)"""
        config = {"services": [{"name": "slow", "mtls_enabled": True}]}
        metrics = {"slow": {"p99_latency_ms": 350, "success_rate": 99.9}}

        result = await analyzer.analyze_mesh(config, metrics)
        latency_metric = [m for m in result.metrics if m.metric_type == "p99_latency"][0]
        assert latency_metric.status == "warning"

    @pytest.mark.asyncio
    async def test_latency_critical_threshold(self, analyzer):
        """Test critical latency threshold (>500ms)"""
        config = {"services": [{"name": "very-slow", "mtls_enabled": True}]}
        metrics = {"very-slow": {"p99_latency_ms": 501, "success_rate": 99.9}}

        result = await analyzer.analyze_mesh(config, metrics)
        latency_metric = [m for m in result.metrics if m.metric_type == "p99_latency"][0]
        assert latency_metric.status == "critical"


class TestSuccessRateThresholds:
    """Tests for success rate threshold detection"""

    @pytest.fixture
    def analyzer(self):
        return ServiceMeshAnalyzer()

    @pytest.mark.asyncio
    async def test_success_rate_healthy(self, analyzer):
        """Test healthy success rate (>=99.5%)"""
        config = {"services": [{"name": "reliable", "mtls_enabled": True}]}
        metrics = {"reliable": {"p99_latency_ms": 50, "success_rate": 99.5}}

        result = await analyzer.analyze_mesh(config, metrics)
        success_metric = [m for m in result.metrics if m.metric_type == "success_rate"][0]
        assert success_metric.status == "healthy"

    @pytest.mark.asyncio
    async def test_success_rate_warning(self, analyzer):
        """Test warning success rate (99.0-99.5%)"""
        config = {"services": [{"name": "unstable", "mtls_enabled": True}]}
        metrics = {"unstable": {"p99_latency_ms": 50, "success_rate": 99.2}}

        result = await analyzer.analyze_mesh(config, metrics)
        success_metric = [m for m in result.metrics if m.metric_type == "success_rate"][0]
        assert success_metric.status == "warning"

    @pytest.mark.asyncio
    async def test_success_rate_critical(self, analyzer):
        """Test critical success rate (<99.0%)"""
        config = {"services": [{"name": "failing", "mtls_enabled": True}]}
        metrics = {"failing": {"p99_latency_ms": 50, "success_rate": 98.5}}

        result = await analyzer.analyze_mesh(config, metrics)
        success_metric = [m for m in result.metrics if m.metric_type == "success_rate"][0]
        assert success_metric.status == "critical"
