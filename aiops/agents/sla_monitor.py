"""
SLA Compliance Monitor Agent

Monitors service level agreements, tracks SLIs/SLOs, predicts violations,
and provides recommendations for maintaining SLA compliance.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class SLI(BaseModel):
    """Service Level Indicator"""
    name: str = Field(description="SLI name (availability, latency, error_rate, etc.)")
    current_value: float = Field(description="Current measured value")
    unit: str = Field(description="Unit of measurement")
    measurement_period: str = Field(description="Time period for measurement")


class SLO(BaseModel):
    """Service Level Objective"""
    name: str = Field(description="SLO name")
    sli_name: str = Field(description="Associated SLI")
    target_value: float = Field(description="Target value to maintain")
    operator: str = Field(description=">=, <=, ==")
    current_compliance: float = Field(description="Current compliance percentage")
    status: str = Field(description="compliant, at_risk, violated")
    error_budget_remaining: float = Field(description="Remaining error budget percentage")


class SLAViolationPrediction(BaseModel):
    """Prediction of potential SLA violation"""
    slo_name: str
    probability: float = Field(description="Probability of violation (0-100)")
    time_to_violation: Optional[str] = Field(description="Estimated time until violation")
    contributing_factors: List[str] = Field(description="Factors leading to potential violation")
    recommended_actions: List[str] = Field(description="Actions to prevent violation")
    severity: str = Field(description="critical, high, medium, low")


class SLAMonitoringResult(BaseModel):
    """SLA monitoring result"""
    analyzed_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    service_name: str = Field(description="Service being monitored")
    slis: List[SLI] = Field(description="Current SLIs")
    slos: List[SLO] = Field(description="SLO compliance status")
    violations: List[SLAViolationPrediction] = Field(description="Predicted violations")
    overall_health: str = Field(description="healthy, degraded, critical")
    compliance_score: float = Field(description="Overall compliance score 0-100")
    summary: str = Field(description="Summary")
    recommendations: List[str] = Field(description="Recommendations")


class SLAComplianceMonitor:
    """SLA compliance monitoring agent"""

    def __init__(self, llm_factory=None):
        self.llm_factory = llm_factory
        logger.info("SLA Compliance Monitor initialized")

    async def monitor_sla(
        self,
        service_name: str,
        metrics: Dict[str, Any],
        slo_definitions: Optional[List[Dict[str, Any]]] = None
    ) -> SLAMonitoringResult:
        """Monitor SLA compliance and predict violations"""

        # Define default SLIs
        slis = [
            SLI(
                name="availability",
                current_value=metrics.get('uptime_percentage', 99.5),
                unit="percentage",
                measurement_period="30d"
            ),
            SLI(
                name="latency_p99",
                current_value=metrics.get('latency_p99_ms', 250),
                unit="milliseconds",
                measurement_period="1h"
            ),
            SLI(
                name="error_rate",
                current_value=metrics.get('error_rate', 0.5),
                unit="percentage",
                measurement_period="1h"
            ),
            SLI(
                name="throughput",
                current_value=metrics.get('requests_per_second', 1000),
                unit="requests/second",
                measurement_period="5m"
            )
        ]

        # Define SLOs (can be customized)
        if not slo_definitions:
            slo_definitions = [
                {"name": "Availability SLO", "sli": "availability", "target": 99.9, "operator": ">="},
                {"name": "Latency SLO", "sli": "latency_p99", "target": 300, "operator": "<="},
                {"name": "Error Rate SLO", "sli": "error_rate", "target": 1.0, "operator": "<="},
            ]

        slos = []
        violations = []

        for slo_def in slo_definitions:
            sli_name = slo_def['sli']
            sli = next((s for s in slis if s.name == sli_name), None)

            if not sli:
                continue

            target = slo_def['target']
            operator = slo_def['operator']
            current = sli.current_value

            # Calculate compliance
            if operator == ">=":
                is_compliant = current >= target
                compliance_pct = min(100, (current / target) * 100)
                error_budget = max(0, ((current - target) / (100 - target)) * 100) if target < 100 else 0
            elif operator == "<=":
                is_compliant = current <= target
                compliance_pct = min(100, (target / current) * 100) if current > 0 else 100
                error_budget = max(0, ((target - current) / target) * 100) if target > 0 else 100
            else:
                is_compliant = current == target
                compliance_pct = 100 if is_compliant else 0
                error_budget = 0

            # Determine status
            if is_compliant:
                if error_budget < 20:
                    status = "at_risk"
                else:
                    status = "compliant"
            else:
                status = "violated"

            slo = SLO(
                name=slo_def['name'],
                sli_name=sli_name,
                target_value=target,
                operator=operator,
                current_compliance=compliance_pct,
                status=status,
                error_budget_remaining=error_budget
            )
            slos.append(slo)

            # Predict violations
            if status == "violated":
                violations.append(SLAViolationPrediction(
                    slo_name=slo.name,
                    probability=100.0,
                    time_to_violation="NOW",
                    contributing_factors=[
                        f"Current {sli_name}: {current}{sli.unit}",
                        f"Target: {operator} {target}{sli.unit}",
                        "SLO already violated"
                    ],
                    recommended_actions=[
                        "Immediate incident response required",
                        "Scale resources if capacity issue",
                        "Investigate root cause",
                        "Implement auto-remediation"
                    ],
                    severity="critical"
                ))
            elif status == "at_risk":
                violations.append(SLAViolationPrediction(
                    slo_name=slo.name,
                    probability=75.0,
                    time_to_violation="1-4 hours",
                    contributing_factors=[
                        f"Error budget low: {error_budget:.1f}% remaining",
                        f"Current trend approaching limit",
                        "Historical pattern indicates risk"
                    ],
                    recommended_actions=[
                        "Increase monitoring frequency",
                        "Prepare incident response team",
                        "Review recent changes/deployments",
                        "Consider scaling preemptively"
                    ],
                    severity="high"
                ))

        # Calculate overall health
        violated_count = sum(1 for slo in slos if slo.status == "violated")
        at_risk_count = sum(1 for slo in slos if slo.status == "at_risk")

        if violated_count > 0:
            health = "critical"
        elif at_risk_count > 0:
            health = "degraded"
        else:
            health = "healthy"

        # Calculate compliance score
        compliance_score = sum(slo.current_compliance for slo in slos) / len(slos) if slos else 100

        # Generate recommendations
        recommendations = self._generate_recommendations(slos, violations, metrics)

        # Generate summary
        summary = self._generate_summary(service_name, slos, violations, health, compliance_score)

        return SLAMonitoringResult(
            service_name=service_name,
            slis=slis,
            slos=slos,
            violations=violations,
            overall_health=health,
            compliance_score=compliance_score,
            summary=summary,
            recommendations=recommendations
        )

    def _generate_recommendations(
        self,
        slos: List[SLO],
        violations: List[SLAViolationPrediction],
        metrics: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # Check availability
        availability_slo = next((s for s in slos if 'availability' in s.sli_name.lower()), None)
        if availability_slo and availability_slo.status != "compliant":
            recommendations.extend([
                "Implement multi-region deployment for higher availability",
                "Add health checks and automatic failover",
                "Review and improve incident response time"
            ])

        # Check latency
        latency_slo = next((s for s in slos if 'latency' in s.sli_name.lower()), None)
        if latency_slo and latency_slo.status != "compliant":
            recommendations.extend([
                "Optimize database queries and add caching",
                "Implement CDN for static content",
                "Consider horizontal scaling or load balancing"
            ])

        # Check error rate
        error_slo = next((s for s in slos if 'error' in s.sli_name.lower()), None)
        if error_slo and error_slo.status != "compliant":
            recommendations.extend([
                "Implement circuit breakers and retry logic",
                "Improve error handling and logging",
                "Add automated testing for critical paths"
            ])

        # General recommendations
        if any(v.severity == "critical" for v in violations):
            recommendations.insert(0, "🚨 CRITICAL: Activate incident response team immediately")

        if len(violations) > 2:
            recommendations.append("Consider revising SLOs based on actual system capabilities")

        return recommendations[:5]  # Top 5 recommendations

    def _generate_summary(
        self,
        service_name: str,
        slos: List[SLO],
        violations: List[SLAViolationPrediction],
        health: str,
        score: float
    ) -> str:
        """Generate executive summary"""
        summary = f"SLA Monitoring: {service_name}\n\n"
        summary += f"Overall Health: {health.upper()}\n"
        summary += f"Compliance Score: {score:.1f}/100\n\n"

        compliant = sum(1 for s in slos if s.status == "compliant")
        summary += f"SLOs: {compliant}/{len(slos)} compliant\n"

        if violations:
            critical = sum(1 for v in violations if v.severity == "critical")
            if critical:
                summary += f"⚠️  {critical} critical violations detected\n"

        return summary
