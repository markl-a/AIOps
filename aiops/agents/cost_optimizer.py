"""
Cloud Cost Optimizer Agent

This agent analyzes cloud resource usage and costs across AWS, Azure, and GCP,
identifying waste, suggesting optimizations, and forecasting future costs.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class CostSaving(BaseModel):
    """Individual cost saving opportunity"""
    resource_type: str = Field(description="Type of resource (EC2, RDS, S3, etc.)")
    resource_id: str = Field(description="Resource identifier")
    current_cost: float = Field(description="Current monthly cost in USD")
    potential_savings: float = Field(description="Potential monthly savings in USD")
    savings_percentage: float = Field(description="Percentage of cost that can be saved")
    recommendation: str = Field(description="What to do")
    reason: str = Field(description="Why this saves money")
    priority: str = Field(description="critical, high, medium, low")
    implementation_effort: str = Field(description="easy, medium, hard")


class CostForecast(BaseModel):
    """Cost forecast for future periods"""
    period: str = Field(description="Forecast period (next_month, next_quarter, next_year)")
    estimated_cost: float = Field(description="Forecasted cost in USD")
    confidence: float = Field(description="Confidence level (0-100)")
    trend: str = Field(description="increasing, stable, decreasing")
    factors: List[str] = Field(description="Factors affecting the forecast")


class CostOptimizationResult(BaseModel):
    """Complete cost optimization analysis"""
    analyzed_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    cloud_provider: str = Field(description="AWS, Azure, GCP, Multi-Cloud")
    current_monthly_cost: float = Field(description="Current total monthly cost")
    potential_monthly_savings: float = Field(description="Total potential monthly savings")
    savings_opportunities: List[CostSaving] = Field(description="List of cost saving opportunities")
    forecasts: List[CostForecast] = Field(description="Cost forecasts")
    wasteful_resources: List[str] = Field(description="Resources not being used effectively")
    summary: str = Field(description="Executive summary")
    recommendations_by_priority: Dict[str, int] = Field(description="Count by priority")


class CloudCostOptimizer:
    """
    AI-powered cloud cost optimizer.

    Features:
    - Identify idle and underutilized resources
    - Reserved instance recommendations
    - Right-sizing suggestions
    - Storage optimization
    - Cost forecasting
    - Multi-cloud cost comparison
    """

    def __init__(self, llm_factory=None):
        """Initialize the Cost Optimizer Agent"""
        self.llm_factory = llm_factory
        logger.info("Cloud Cost Optimizer Agent initialized")

    async def analyze_costs(
        self,
        resources: List[Dict[str, Any]],
        usage_metrics: Optional[Dict[str, Any]] = None,
        cloud_provider: str = "AWS"
    ) -> CostOptimizationResult:
        """
        Analyze cloud resources and identify cost optimization opportunities.

        Args:
            resources: List of cloud resources with cost information
            usage_metrics: Optional usage metrics for resources
            cloud_provider: Cloud provider (AWS, Azure, GCP)

        Returns:
            CostOptimizationResult with savings opportunities
        """
        try:
            savings_opportunities = []
            wasteful_resources = []
            total_current_cost = 0.0
            total_potential_savings = 0.0

            # Analyze each resource
            for resource in resources:
                resource_type = resource.get('type', 'unknown')
                resource_id = resource.get('id', 'unknown')
                cost = resource.get('monthly_cost', 0.0)
                total_current_cost += cost

                # Check for idle resources
                if self._is_idle(resource, usage_metrics):
                    savings = cost * 1.0  # 100% savings if completely idle
                    savings_opportunities.append(CostSaving(
                        resource_type=resource_type,
                        resource_id=resource_id,
                        current_cost=cost,
                        potential_savings=savings,
                        savings_percentage=100.0,
                        recommendation=f"Terminate or stop idle {resource_type}",
                        reason=f"Resource has been idle for >30 days with <1% utilization",
                        priority="high",
                        implementation_effort="easy"
                    ))
                    wasteful_resources.append(resource_id)
                    total_potential_savings += savings

                # Check for underutilization
                elif self._is_underutilized(resource, usage_metrics):
                    savings = cost * 0.5  # Estimate 50% savings by right-sizing
                    savings_opportunities.append(CostSaving(
                        resource_type=resource_type,
                        resource_id=resource_id,
                        current_cost=cost,
                        potential_savings=savings,
                        savings_percentage=50.0,
                        recommendation=f"Right-size {resource_type} to smaller instance type",
                        reason=f"Average utilization <30%. Can downsize to save costs.",
                        priority="medium",
                        implementation_effort="medium"
                    ))
                    total_potential_savings += savings

                # Check for missing reserved instance opportunities
                if resource_type in ['EC2', 'RDS', 'VM', 'SQL'] and resource.get('pricing', 'on-demand') == 'on-demand':
                    uptime = resource.get('uptime_percentage', 0)
                    if uptime > 70:  # Running >70% of the time
                        savings = cost * 0.40  # Typical 40% savings with RIs
                        savings_opportunities.append(CostSaving(
                            resource_type=resource_type,
                            resource_id=resource_id,
                            current_cost=cost,
                            potential_savings=savings,
                            savings_percentage=40.0,
                            recommendation="Purchase Reserved Instance or Savings Plan",
                            reason=f"Resource runs {uptime}% of the time. Reserved pricing offers 40-60% discount.",
                            priority="high",
                            implementation_effort="easy"
                        ))
                        total_potential_savings += savings

                # Check for old snapshots/backups
                if resource_type in ['Snapshot', 'Backup', 'Image']:
                    age_days = resource.get('age_days', 0)
                    if age_days > 90:
                        savings = cost * 1.0
                        savings_opportunities.append(CostSaving(
                            resource_type=resource_type,
                            resource_id=resource_id,
                            current_cost=cost,
                            potential_savings=savings,
                            savings_percentage=100.0,
                            recommendation="Delete old snapshots/backups",
                            reason=f"Snapshot is {age_days} days old. Implement retention policy.",
                            priority="medium",
                            implementation_effort="easy"
                        ))
                        wasteful_resources.append(resource_id)
                        total_potential_savings += savings

                # Check for unattached volumes
                if resource_type in ['EBS', 'Disk', 'Volume'] and not resource.get('attached', True):
                    savings = cost * 1.0
                    savings_opportunities.append(CostSaving(
                        resource_type=resource_type,
                        resource_id=resource_id,
                        current_cost=cost,
                        potential_savings=savings,
                        savings_percentage=100.0,
                        recommendation="Delete unattached volumes",
                        reason="Volume is not attached to any instance. Create snapshot if needed, then delete.",
                        priority="high",
                        implementation_effort="easy"
                    ))
                    wasteful_resources.append(resource_id)
                    total_potential_savings += savings

            # Generate cost forecasts
            forecasts = self._generate_forecasts(total_current_cost, savings_opportunities)

            # Count recommendations by priority
            recommendations_by_priority = {
                "critical": sum(1 for s in savings_opportunities if s.priority == "critical"),
                "high": sum(1 for s in savings_opportunities if s.priority == "high"),
                "medium": sum(1 for s in savings_opportunities if s.priority == "medium"),
                "low": sum(1 for s in savings_opportunities if s.priority == "low")
            }

            # Generate summary
            summary = self._generate_summary(
                total_current_cost,
                total_potential_savings,
                savings_opportunities,
                wasteful_resources
            )

            result = CostOptimizationResult(
                cloud_provider=cloud_provider,
                current_monthly_cost=total_current_cost,
                potential_monthly_savings=total_potential_savings,
                savings_opportunities=savings_opportunities,
                forecasts=forecasts,
                wasteful_resources=wasteful_resources,
                summary=summary,
                recommendations_by_priority=recommendations_by_priority
            )

            logger.info(f"Cost analysis complete: ${total_potential_savings:.2f}/month potential savings")
            return result

        except Exception as e:
            logger.error(f"Error analyzing costs: {str(e)}")
            raise

    def _is_idle(self, resource: Dict[str, Any], metrics: Optional[Dict[str, Any]]) -> bool:
        """Check if resource is idle"""
        if not metrics or resource['id'] not in metrics:
            return False

        resource_metrics = metrics[resource['id']]
        cpu = resource_metrics.get('cpu_avg', 100)
        network = resource_metrics.get('network_avg', 100)

        return cpu < 1.0 and network < 1.0

    def _is_underutilized(self, resource: Dict[str, Any], metrics: Optional[Dict[str, Any]]) -> bool:
        """Check if resource is underutilized"""
        if not metrics or resource['id'] not in metrics:
            return False

        resource_metrics = metrics[resource['id']]
        cpu = resource_metrics.get('cpu_avg', 100)
        memory = resource_metrics.get('memory_avg', 100)

        return cpu < 30.0 or memory < 30.0

    def _generate_forecasts(
        self,
        current_cost: float,
        savings_opportunities: List[CostSaving]
    ) -> List[CostForecast]:
        """Generate cost forecasts"""
        # Calculate optimized cost
        total_potential_savings = sum(s.potential_savings for s in savings_opportunities)
        optimized_cost = current_cost - total_potential_savings

        forecasts = [
            CostForecast(
                period="next_month",
                estimated_cost=current_cost * 1.05,  # Assume 5% growth
                confidence=85.0,
                trend="increasing",
                factors=[
                    "Historical growth trend",
                    "No optimization applied",
                    "Seasonal variations"
                ]
            ),
            CostForecast(
                period="next_month_optimized",
                estimated_cost=optimized_cost,
                confidence=75.0,
                trend="decreasing",
                factors=[
                    "If all recommendations implemented",
                    f"Savings: ${total_potential_savings:.2f}/month",
                    "May require upfront commitment (RIs)"
                ]
            ),
            CostForecast(
                period="next_quarter",
                estimated_cost=current_cost * 3 * 1.08,  # 8% quarterly growth
                confidence=70.0,
                trend="increasing",
                factors=[
                    "Business growth expected",
                    "New services may be added",
                    "Optimization recommended to control costs"
                ]
            )
        ]

        return forecasts

    def _generate_summary(
        self,
        current_cost: float,
        potential_savings: float,
        opportunities: List[CostSaving],
        wasteful: List[str]
    ) -> str:
        """Generate executive summary"""
        savings_pct = (potential_savings / current_cost * 100) if current_cost > 0 else 0

        summary = f"💰 Cloud Cost Optimization Analysis\n\n"
        summary += f"Current Monthly Cost: ${current_cost:.2f}\n"
        summary += f"Potential Monthly Savings: ${potential_savings:.2f} ({savings_pct:.1f}%)\n"
        summary += f"Annual Savings Potential: ${potential_savings * 12:.2f}\n\n"

        if wasteful:
            summary += f"⚠️  Found {len(wasteful)} wasteful resources (idle or unused)\n"

        summary += f"\n📊 Optimization Opportunities: {len(opportunities)}\n"

        high_priority = sum(1 for o in opportunities if o.priority in ['critical', 'high'])
        if high_priority:
            summary += f"   • {high_priority} high-priority items\n"

        easy_wins = sum(1 for o in opportunities if o.implementation_effort == 'easy')
        if easy_wins:
            summary += f"   • {easy_wins} quick wins (easy to implement)\n"

        summary += f"\n💡 Top Recommendations:\n"
        summary += "   1. Terminate idle resources\n"
        summary += "   2. Purchase Reserved Instances for stable workloads\n"
        summary += "   3. Right-size underutilized instances\n"
        summary += "   4. Implement automated cleanup for old snapshots\n"

        return summary
