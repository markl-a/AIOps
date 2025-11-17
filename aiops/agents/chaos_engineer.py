"""
Chaos Engineering Agent

Plans and executes controlled chaos experiments to test system resilience,
identify weaknesses, and improve reliability.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class ChaosExperiment(BaseModel):
    """Chaos experiment definition"""
    name: str = Field(description="Experiment name")
    type: str = Field(description="network, cpu, memory, disk, pod_failure, etc.")
    target: str = Field(description="Target resource/service")
    description: str = Field(description="What this experiment tests")
    hypothesis: str = Field(description="Expected system behavior")
    blast_radius: str = Field(description="limited, moderate, wide")
    risk_level: str = Field(description="low, medium, high")
    duration_minutes: int = Field(description="How long to run the experiment")
    rollback_plan: str = Field(description="How to stop/rollback")
    success_criteria: List[str] = Field(description="Metrics to validate success")
    commands: List[str] = Field(description="Commands to execute")


class ChaosResult(BaseModel):
    """Chaos experiment result"""
    experiment_name: str
    executed_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    status: str = Field(description="success, failed, partial")
    duration_seconds: int
    observations: List[str] = Field(description="What was observed")
    metrics_impact: Dict[str, Any] = Field(description="Impact on metrics")
    system_resilience: str = Field(description="excellent, good, fair, poor")
    issues_found: List[str] = Field(description="Issues discovered")
    recommendations: List[str] = Field(description="Improvements to make")


class ChaosEngineeringPlan(BaseModel):
    """Complete chaos engineering plan"""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    environment: str = Field(description="staging, production, etc.")
    experiments: List[ChaosExperiment] = Field(description="Planned experiments")
    total_risk_score: float = Field(description="Overall risk score")
    estimated_duration_hours: float = Field(description="Total time needed")
    summary: str = Field(description="Summary")


class ChaosEngineer:
    """Chaos engineering agent"""

    def __init__(self, llm_factory=None):
        self.llm_factory = llm_factory
        logger.info("Chaos Engineering Agent initialized")

    async def create_chaos_plan(
        self,
        services: List[str],
        environment: str = "staging"
    ) -> ChaosEngineeringPlan:
        """Create a chaos engineering test plan"""
        experiments = []

        # Network chaos experiments
        for service in services:
            experiments.append(ChaosExperiment(
                name=f"Network Latency - {service}",
                type="network_latency",
                target=service,
                description=f"Inject 200ms latency to {service} to test timeout handling",
                hypothesis="System should gracefully handle increased latency with proper timeouts and retries",
                blast_radius="limited",
                risk_level="low",
                duration_minutes=10,
                rollback_plan="Remove network policy/tc rules",
                success_criteria=[
                    "Request timeout < 5 seconds",
                    "Error rate < 1%",
                    "Circuit breaker triggers appropriately",
                    "No cascading failures"
                ],
                commands=[
                    f"tc qdisc add dev eth0 root netem delay 200ms",
                    "# Monitor for 10 minutes",
                    "tc qdisc del dev eth0 root"
                ]
            ))

            # Pod failure
            experiments.append(ChaosExperiment(
                name=f"Pod Failure - {service}",
                type="pod_failure",
                target=service,
                description=f"Kill random pod of {service} to test auto-recovery",
                hypothesis="Kubernetes should automatically restart pod and service should remain available",
                blast_radius="limited",
                risk_level="low",
                duration_minutes=5,
                rollback_plan="Manual pod restart if needed",
                success_criteria=[
                    "Pod restarts within 30 seconds",
                    "No service downtime",
                    "Load balancer removes unhealthy pod",
                    "Requests routed to healthy pods"
                ],
                commands=[
                    f"kubectl delete pod -l app={service} --grace-period=0",
                    "kubectl wait --for=condition=Ready pod -l app={service} --timeout=60s"
                ]
            ))

        # Resource exhaustion
        experiments.append(ChaosExperiment(
            name="CPU Stress Test",
            type="cpu_stress",
            target=services[0] if services else "app",
            description="Stress CPU to 90% to test throttling and scaling",
            hypothesis="HPA should trigger and scale up pods, performance degrades gracefully",
            blast_radius="moderate",
            risk_level="medium",
            duration_minutes=15,
            rollback_plan="Kill stress process",
            success_criteria=[
                "HPA triggers within 2 minutes",
                "New pods start successfully",
                "Response time increases but < 3x baseline",
                "No crashes or OOM kills"
            ],
            commands=[
                "stress-ng --cpu 4 --timeout 15m",
                "# Monitor HPA: kubectl get hpa -w"
            ]
        ))

        # Dependency failure
        if len(services) > 1:
            experiments.append(ChaosExperiment(
                name="Database Connection Failure",
                type="dependency_failure",
                target="database",
                description="Simulate database unavailability",
                hypothesis="Application should use circuit breaker and fallback to cached data",
                blast_radius="moderate",
                risk_level="medium",
                duration_minutes=5,
                rollback_plan="Restore network connectivity",
                success_criteria=[
                    "Circuit breaker opens within 10 seconds",
                    "Fallback logic executes",
                    "User-facing errors are graceful",
                    "System recovers when DB restored"
                ],
                commands=[
                    "# Block DB traffic",
                    "iptables -A OUTPUT -d <db-ip> -j DROP",
                    "# Wait 5 minutes",
                    "iptables -D OUTPUT -d <db-ip> -j DROP"
                ]
            ))

        total_duration = sum(e.duration_minutes for e in experiments) / 60
        risk_scores = {"low": 1, "medium": 2, "high": 3}
        avg_risk = sum(risk_scores[e.risk_level] for e in experiments) / len(experiments) if experiments else 0

        summary = f"Chaos plan for {environment}: {len(experiments)} experiments, est. {total_duration:.1f}h"

        return ChaosEngineeringPlan(
            environment=environment,
            experiments=experiments,
            total_risk_score=avg_risk,
            estimated_duration_hours=total_duration,
            summary=summary
        )

    async def analyze_chaos_result(
        self,
        experiment: ChaosExperiment,
        metrics_before: Dict[str, float],
        metrics_after: Dict[str, float],
        logs: List[str]
    ) -> ChaosResult:
        """Analyze chaos experiment results"""
        observations = []
        issues_found = []
        recommendations = []

        # Analyze metrics changes
        metrics_impact = {}
        for metric, before_value in metrics_before.items():
            after_value = metrics_after.get(metric, before_value)
            change_pct = ((after_value - before_value) / before_value * 100) if before_value != 0 else 0
            metrics_impact[metric] = {
                "before": before_value,
                "after": after_value,
                "change_pct": round(change_pct, 2)
            }

            if abs(change_pct) > 50:
                observations.append(f"{metric} changed by {change_pct:.1f}%")

        # Check for errors in logs
        error_count = sum(1 for log in logs if 'error' in log.lower() or 'exception' in log.lower())
        if error_count > 10:
            issues_found.append(f"High error rate: {error_count} errors in logs")
            recommendations.append("Improve error handling and circuit breaker implementation")

        # Determine resilience
        critical_issues = len([i for i in issues_found if 'critical' in i.lower()])
        if critical_issues > 0:
            resilience = "poor"
        elif len(issues_found) > 3:
            resilience = "fair"
        elif len(issues_found) > 0:
            resilience = "good"
        else:
            resilience = "excellent"

        if resilience in ["fair", "poor"]:
            recommendations.append("Add retry logic with exponential backoff")
            recommendations.append("Implement health checks and readiness probes")
            recommendations.append("Configure resource limits and autoscaling")

        status = "success" if resilience in ["excellent", "good"] else "partial"

        return ChaosResult(
            experiment_name=experiment.name,
            status=status,
            duration_seconds=experiment.duration_minutes * 60,
            observations=observations,
            metrics_impact=metrics_impact,
            system_resilience=resilience,
            issues_found=issues_found,
            recommendations=recommendations
        )
