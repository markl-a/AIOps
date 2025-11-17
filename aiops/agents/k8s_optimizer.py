"""
Kubernetes Resource Optimizer Agent

This agent analyzes Kubernetes deployments, pods, and services to optimize resource allocation,
identify over/under-provisioning, and suggest improvements for cluster efficiency.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
import yaml
import json
from datetime import datetime
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class ResourceRecommendation(BaseModel):
    """Resource optimization recommendation"""
    resource_type: str = Field(description="Type of resource (deployment, pod, service, etc.)")
    resource_name: str = Field(description="Name of the resource")
    namespace: str = Field(description="Kubernetes namespace")
    current_config: Dict[str, Any] = Field(description="Current resource configuration")
    recommended_config: Dict[str, Any] = Field(description="Recommended configuration")
    potential_savings: Dict[str, float] = Field(description="Potential cost/resource savings")
    reasoning: str = Field(description="Explanation for the recommendation")
    priority: str = Field(description="Priority level: critical, high, medium, low")


class K8sOptimizationResult(BaseModel):
    """Complete Kubernetes optimization analysis result"""
    cluster_name: str = Field(description="Kubernetes cluster name")
    analyzed_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    total_resources: int = Field(description="Total resources analyzed")
    recommendations: List[ResourceRecommendation] = Field(description="List of optimization recommendations")
    cluster_efficiency: float = Field(description="Overall cluster efficiency score (0-100)")
    potential_cost_savings: float = Field(description="Estimated monthly cost savings in USD")
    issues_found: List[str] = Field(description="List of issues identified")
    summary: str = Field(description="Executive summary")


class KubernetesOptimizerAgent:
    """
    AI-powered Kubernetes resource optimizer.

    Features:
    - Resource request/limit optimization
    - Pod autoscaling recommendations
    - Node utilization analysis
    - Cost optimization suggestions
    - Best practices validation
    """

    def __init__(self, llm_factory=None):
        """Initialize the Kubernetes Optimizer Agent"""
        self.llm_factory = llm_factory
        logger.info("Kubernetes Optimizer Agent initialized")

    async def analyze_deployment(
        self,
        deployment_yaml: str,
        metrics: Optional[Dict[str, Any]] = None
    ) -> K8sOptimizationResult:
        """
        Analyze a Kubernetes deployment and provide optimization recommendations.

        Args:
            deployment_yaml: YAML string of the deployment configuration
            metrics: Optional actual usage metrics from the cluster

        Returns:
            K8sOptimizationResult with recommendations
        """
        try:
            # Parse YAML
            deployment = yaml.safe_load(deployment_yaml)

            recommendations = []
            issues = []

            # Analyze resource requests and limits
            resource_rec = self._analyze_resources(deployment, metrics)
            if resource_rec:
                recommendations.extend(resource_rec)

            # Check for autoscaling
            hpa_rec = self._check_autoscaling(deployment)
            if hpa_rec:
                recommendations.append(hpa_rec)
                issues.append("Missing HorizontalPodAutoscaler configuration")

            # Analyze replica count
            replica_rec = self._analyze_replicas(deployment, metrics)
            if replica_rec:
                recommendations.append(replica_rec)

            # Check resource quotas and limits
            quota_issues = self._check_resource_quotas(deployment)
            issues.extend(quota_issues)

            # Check for best practices
            bp_issues = self._check_best_practices(deployment)
            issues.extend(bp_issues)

            # Calculate cluster efficiency
            efficiency = self._calculate_efficiency(deployment, metrics)

            # Calculate potential savings
            savings = self._calculate_savings(recommendations)

            # Generate summary
            summary = self._generate_summary(deployment, recommendations, efficiency)

            result = K8sOptimizationResult(
                cluster_name=deployment.get('metadata', {}).get('namespace', 'default'),
                total_resources=1,
                recommendations=recommendations,
                cluster_efficiency=efficiency,
                potential_cost_savings=savings,
                issues_found=issues,
                summary=summary
            )

            logger.info(f"K8s optimization complete: {len(recommendations)} recommendations found")
            return result

        except Exception as e:
            logger.error(f"Error analyzing Kubernetes deployment: {str(e)}")
            raise

    def _analyze_resources(
        self,
        deployment: Dict[str, Any],
        metrics: Optional[Dict[str, Any]]
    ) -> List[ResourceRecommendation]:
        """Analyze CPU and memory resource allocations"""
        recommendations = []

        try:
            spec = deployment.get('spec', {})
            template = spec.get('template', {})
            containers = template.get('spec', {}).get('containers', [])

            for container in containers:
                container_name = container.get('name', 'unknown')
                resources = container.get('resources', {})
                requests = resources.get('requests', {})
                limits = resources.get('limits', {})

                # Check if resources are defined
                if not requests or not limits:
                    recommendations.append(ResourceRecommendation(
                        resource_type="container",
                        resource_name=container_name,
                        namespace=deployment.get('metadata', {}).get('namespace', 'default'),
                        current_config={"resources": resources},
                        recommended_config={
                            "resources": {
                                "requests": {"cpu": "100m", "memory": "128Mi"},
                                "limits": {"cpu": "500m", "memory": "512Mi"}
                            }
                        },
                        potential_savings={"cpu_cores": 0.1, "memory_gb": 0.5},
                        reasoning="No resource requests/limits defined. Setting baseline recommendations to prevent resource contention.",
                        priority="high"
                    ))
                    continue

                # Analyze actual usage vs requests if metrics available
                if metrics and container_name in metrics:
                    actual_cpu = metrics[container_name].get('cpu', 0)
                    actual_memory = metrics[container_name].get('memory', 0)
                    requested_cpu = self._parse_cpu(requests.get('cpu', '0'))
                    requested_memory = self._parse_memory(requests.get('memory', '0'))

                    # Check for over-provisioning (using < 50% of requested)
                    if actual_cpu < requested_cpu * 0.5:
                        recommendations.append(ResourceRecommendation(
                            resource_type="container",
                            resource_name=container_name,
                            namespace=deployment.get('metadata', {}).get('namespace', 'default'),
                            current_config={"cpu_request": requests.get('cpu')},
                            recommended_config={"cpu_request": f"{int(actual_cpu * 1.3)}m"},
                            potential_savings={"cpu_cores": (requested_cpu - actual_cpu * 1.3) / 1000},
                            reasoning=f"CPU over-provisioned. Using {actual_cpu}m but requesting {requested_cpu}m. Recommend reducing to {int(actual_cpu * 1.3)}m (30% buffer).",
                            priority="medium"
                        ))

                    # Check for under-provisioning (using > 80% of requested)
                    if actual_cpu > requested_cpu * 0.8:
                        recommendations.append(ResourceRecommendation(
                            resource_type="container",
                            resource_name=container_name,
                            namespace=deployment.get('metadata', {}).get('namespace', 'default'),
                            current_config={"cpu_request": requests.get('cpu')},
                            recommended_config={"cpu_request": f"{int(actual_cpu * 1.5)}m"},
                            potential_savings={"cpu_cores": 0},
                            reasoning=f"CPU under-provisioned. Using {actual_cpu}m (>80% of {requested_cpu}m). Risk of throttling. Recommend increasing to {int(actual_cpu * 1.5)}m.",
                            priority="high"
                        ))

        except Exception as e:
            logger.error(f"Error analyzing resources: {str(e)}")

        return recommendations

    def _check_autoscaling(self, deployment: Dict[str, Any]) -> Optional[ResourceRecommendation]:
        """Check if HorizontalPodAutoscaler should be configured"""
        metadata = deployment.get('metadata', {})
        name = metadata.get('name', 'unknown')
        namespace = metadata.get('namespace', 'default')

        # Simple heuristic: recommend HPA for production workloads
        if not metadata.get('labels', {}).get('autoscaling', False):
            return ResourceRecommendation(
                resource_type="HorizontalPodAutoscaler",
                resource_name=f"{name}-hpa",
                namespace=namespace,
                current_config={"autoscaling": "not configured"},
                recommended_config={
                    "apiVersion": "autoscaling/v2",
                    "kind": "HorizontalPodAutoscaler",
                    "spec": {
                        "minReplicas": 2,
                        "maxReplicas": 10,
                        "metrics": [
                            {
                                "type": "Resource",
                                "resource": {
                                    "name": "cpu",
                                    "target": {"type": "Utilization", "averageUtilization": 70}
                                }
                            }
                        ]
                    }
                },
                potential_savings={"efficiency_gain": 25.0},
                reasoning="Configure HPA to automatically scale based on CPU utilization. This improves resource efficiency during low traffic periods.",
                priority="medium"
            )
        return None

    def _analyze_replicas(
        self,
        deployment: Dict[str, Any],
        metrics: Optional[Dict[str, Any]]
    ) -> Optional[ResourceRecommendation]:
        """Analyze replica count"""
        spec = deployment.get('spec', {})
        replicas = spec.get('replicas', 1)
        metadata = deployment.get('metadata', {})

        if replicas == 1:
            return ResourceRecommendation(
                resource_type="deployment",
                resource_name=metadata.get('name', 'unknown'),
                namespace=metadata.get('namespace', 'default'),
                current_config={"replicas": 1},
                recommended_config={"replicas": 3},
                potential_savings={"availability_improvement": 99.9},
                reasoning="Single replica deployment has no high availability. Recommend at least 3 replicas for production workloads.",
                priority="high"
            )

        return None

    def _check_resource_quotas(self, deployment: Dict[str, Any]) -> List[str]:
        """Check for resource quota issues"""
        issues = []
        spec = deployment.get('spec', {})
        template = spec.get('template', {})
        containers = template.get('spec', {}).get('containers', [])

        for container in containers:
            resources = container.get('resources', {})
            limits = resources.get('limits', {})
            requests = resources.get('requests', {})

            # Check if limits > requests
            if limits and requests:
                cpu_limit = self._parse_cpu(limits.get('cpu', '0'))
                cpu_request = self._parse_cpu(requests.get('cpu', '0'))

                if cpu_limit < cpu_request:
                    issues.append(f"Container '{container.get('name')}': CPU limit ({cpu_limit}m) < request ({cpu_request}m)")

        return issues

    def _check_best_practices(self, deployment: Dict[str, Any]) -> List[str]:
        """Check Kubernetes best practices"""
        issues = []
        spec = deployment.get('spec', {})
        template = spec.get('template', {})
        pod_spec = template.get('spec', {})

        # Check for liveness/readiness probes
        containers = pod_spec.get('containers', [])
        for container in containers:
            if 'livenessProbe' not in container:
                issues.append(f"Container '{container.get('name')}': Missing liveness probe")
            if 'readinessProbe' not in container:
                issues.append(f"Container '{container.get('name')}': Missing readiness probe")

        # Check for security context
        if 'securityContext' not in pod_spec:
            issues.append("Missing pod security context")

        # Check for resource limits
        for container in containers:
            if 'resources' not in container or 'limits' not in container.get('resources', {}):
                issues.append(f"Container '{container.get('name')}': Missing resource limits")

        return issues

    def _calculate_efficiency(
        self,
        deployment: Dict[str, Any],
        metrics: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate overall efficiency score"""
        score = 100.0

        # Deduct points for missing configurations
        spec = deployment.get('spec', {})
        template = spec.get('template', {})
        containers = template.get('spec', {}).get('containers', [])

        for container in containers:
            if 'resources' not in container:
                score -= 20
            if 'livenessProbe' not in container:
                score -= 10
            if 'readinessProbe' not in container:
                score -= 10

        if spec.get('replicas', 1) == 1:
            score -= 15

        return max(0.0, score)

    def _calculate_savings(self, recommendations: List[ResourceRecommendation]) -> float:
        """Calculate estimated monthly cost savings"""
        # Rough estimate: $30 per CPU core, $4 per GB RAM per month
        total_savings = 0.0

        for rec in recommendations:
            savings = rec.potential_savings
            cpu_savings = savings.get('cpu_cores', 0) * 30
            memory_savings = savings.get('memory_gb', 0) * 4
            total_savings += cpu_savings + memory_savings

        return round(total_savings, 2)

    def _generate_summary(
        self,
        deployment: Dict[str, Any],
        recommendations: List[ResourceRecommendation],
        efficiency: float
    ) -> str:
        """Generate executive summary"""
        name = deployment.get('metadata', {}).get('name', 'unknown')

        summary = f"Analysis of deployment '{name}':\n"
        summary += f"- Cluster efficiency score: {efficiency:.1f}/100\n"
        summary += f"- Found {len(recommendations)} optimization opportunities\n"

        high_priority = sum(1 for r in recommendations if r.priority == 'high')
        if high_priority > 0:
            summary += f"- {high_priority} high-priority items require immediate attention\n"

        return summary

    def _parse_cpu(self, cpu_str: str) -> int:
        """Parse CPU string to millicores"""
        if not cpu_str:
            return 0
        if cpu_str.endswith('m'):
            return int(cpu_str[:-1])
        return int(float(cpu_str) * 1000)

    def _parse_memory(self, mem_str: str) -> int:
        """Parse memory string to MB"""
        if not mem_str:
            return 0

        multipliers = {
            'Ki': 1 / 1024,
            'Mi': 1,
            'Gi': 1024,
            'K': 1 / 1000,
            'M': 1,
            'G': 1000
        }

        for suffix, multiplier in multipliers.items():
            if mem_str.endswith(suffix):
                return int(float(mem_str[:-len(suffix)]) * multiplier)

        return int(mem_str)
