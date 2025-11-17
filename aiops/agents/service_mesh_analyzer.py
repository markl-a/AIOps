"""
Service Mesh Analyzer Agent

Analyzes service mesh (Istio, Linkerd, Consul) configurations and traffic patterns,
optimizing performance, security, and reliability.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class ServiceMeshMetric(BaseModel):
    """Service mesh metric"""
    service_name: str
    metric_type: str = Field(description="latency, success_rate, throughput, etc.")
    value: float
    unit: str
    status: str = Field(description="healthy, warning, critical")


class MeshOptimization(BaseModel):
    """Service mesh optimization recommendation"""
    optimization_type: str = Field(description="traffic_split, retry_policy, circuit_breaker, etc.")
    service_name: str
    current_config: Dict[str, Any]
    recommended_config: Dict[str, Any]
    expected_benefit: str
    priority: str = Field(description="critical, high, medium, low")
    implementation: str = Field(description="How to implement")


class ServiceMeshAnalysisResult(BaseModel):
    """Service mesh analysis result"""
    analyzed_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    mesh_type: str = Field(description="istio, linkerd, consul, etc.")
    services_analyzed: int
    metrics: List[ServiceMeshMetric] = Field(description="Current metrics")
    optimizations: List[MeshOptimization] = Field(description="Optimization recommendations")
    health_score: float = Field(description="Overall mesh health 0-100")
    summary: str
    topology_insights: List[str] = Field(description="Insights about service topology")


class ServiceMeshAnalyzer:
    """Service mesh analyzer agent"""

    def __init__(self, llm_factory=None):
        self.llm_factory = llm_factory
        logger.info("Service Mesh Analyzer initialized")

    async def analyze_mesh(
        self,
        mesh_config: Dict[str, Any],
        traffic_metrics: Dict[str, Any],
        mesh_type: str = "istio"
    ) -> ServiceMeshAnalysisResult:
        """Analyze service mesh configuration and performance"""

        metrics = []
        optimizations = []
        topology_insights = []

        services = mesh_config.get('services', [])

        # Analyze each service
        for service in services:
            service_name = service.get('name', 'unknown')
            service_metrics = traffic_metrics.get(service_name, {})

            # Analyze latency
            latency = service_metrics.get('p99_latency_ms', 100)
            latency_status = "healthy" if latency < 200 else "warning" if latency < 500 else "critical"
            metrics.append(ServiceMeshMetric(
                service_name=service_name,
                metric_type="p99_latency",
                value=latency,
                unit="ms",
                status=latency_status
            ))

            if latency_status != "healthy":
                optimizations.append(MeshOptimization(
                    optimization_type="circuit_breaker",
                    service_name=service_name,
                    current_config=service.get('resilience', {}),
                    recommended_config={
                        "consecutive_errors": 5,
                        "interval": "10s",
                        "base_ejection_time": "30s",
                        "max_ejection_percent": 50
                    },
                    expected_benefit="Prevent cascading failures, improve overall latency by 20-40%",
                    priority="high",
                    implementation=f"Apply Istio DestinationRule with outlier detection for {service_name}"
                ))

            # Analyze success rate
            success_rate = service_metrics.get('success_rate', 99.5)
            success_status = "healthy" if success_rate >= 99.5 else "warning" if success_rate >= 99.0 else "critical"
            metrics.append(ServiceMeshMetric(
                service_name=service_name,
                metric_type="success_rate",
                value=success_rate,
                unit="percentage",
                status=success_status
            ))

            if success_status != "healthy":
                optimizations.append(MeshOptimization(
                    optimization_type="retry_policy",
                    service_name=service_name,
                    current_config=service.get('retry', {}),
                    recommended_config={
                        "attempts": 3,
                        "perTryTimeout": "2s",
                        "retryOn": "5xx,reset,connect-failure,refused-stream"
                    },
                    expected_benefit="Improve success rate by 0.5-2% through automatic retries",
                    priority="high",
                    implementation=f"Configure VirtualService retry policy for {service_name}"
                ))

            # Check for mTLS
            if not service.get('mtls_enabled', False):
                optimizations.append(MeshOptimization(
                    optimization_type="security",
                    service_name=service_name,
                    current_config={"mtls": "disabled"},
                    recommended_config={"mtls": {"mode": "STRICT"}},
                    expected_benefit="Enable encrypted service-to-service communication",
                    priority="critical",
                    implementation="Enable strict mTLS in PeerAuthentication policy"
                ))

        # Analyze traffic distribution
        if len(services) > 1:
            topology_insights.append(f"Service mesh contains {len(services)} services")

            # Check for single points of failure
            dependencies = mesh_config.get('dependencies', {})
            for service, deps in dependencies.items():
                if len(deps) == 1:
                    topology_insights.append(f"⚠️  {service} depends on single service: {deps[0]} (SPOF)")

            # Check for deep call chains
            max_depth = self._calculate_max_depth(dependencies)
            if max_depth > 5:
                topology_insights.append(f"⚠️  Max call chain depth: {max_depth} (consider reducing)")
                optimizations.append(MeshOptimization(
                    optimization_type="architecture",
                    service_name="overall",
                    current_config={"max_depth": max_depth},
                    recommended_config={"max_depth": 5},
                    expected_benefit="Reduce latency and improve reliability",
                    priority="medium",
                    implementation="Refactor deep call chains, consider API gateway pattern"
                ))

        # Analyze traffic splitting for canary deployments
        for service in services:
            versions = service.get('versions', [])
            if len(versions) > 1:
                optimizations.append(MeshOptimization(
                    optimization_type="traffic_split",
                    service_name=service['name'],
                    current_config={"traffic_split": "not configured"},
                    recommended_config={
                        "v1": 90,
                        "v2": 10
                    },
                    expected_benefit="Safe canary deployments with gradual rollout",
                    priority="medium",
                    implementation="Configure VirtualService with weighted traffic routing"
                ))
                topology_insights.append(f"✓ {service['name']} has {len(versions)} versions - good for canary")

        # Calculate health score
        healthy_metrics = sum(1 for m in metrics if m.status == "healthy")
        health_score = (healthy_metrics / len(metrics) * 100) if metrics else 100

        # Generate summary
        summary = self._generate_summary(mesh_type, len(services), health_score, len(optimizations))

        return ServiceMeshAnalysisResult(
            mesh_type=mesh_type,
            services_analyzed=len(services),
            metrics=metrics,
            optimizations=optimizations,
            health_score=health_score,
            summary=summary,
            topology_insights=topology_insights
        )

    def _calculate_max_depth(self, dependencies: Dict[str, List[str]]) -> int:
        """Calculate maximum call chain depth"""
        def dfs(service: str, visited: set) -> int:
            if service in visited:
                return 0
            visited.add(service)
            deps = dependencies.get(service, [])
            if not deps:
                return 1
            return 1 + max((dfs(dep, visited.copy()) for dep in deps), default=0)

        return max((dfs(service, set()) for service in dependencies.keys()), default=0)

    def _generate_summary(self, mesh_type: str, services: int, health: float, optimizations: int) -> str:
        """Generate summary"""
        summary = f"Service Mesh Analysis ({mesh_type})\n\n"
        summary += f"Services: {services}\n"
        summary += f"Health Score: {health:.1f}/100\n"
        summary += f"Optimizations: {optimizations}\n\n"

        if health >= 90:
            summary += "✓ Service mesh is healthy"
        elif health >= 70:
            summary += "⚠ Some issues detected"
        else:
            summary += "✗ Critical issues require attention"

        return summary
