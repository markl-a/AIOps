"""Intelligent Monitor Agent - AI-powered monitoring and alerting."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from aiops.agents.base_agent import BaseAgent
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class Alert(BaseModel):
    """Represents a monitoring alert."""

    severity: str = Field(description="Severity: critical, high, medium, low, info")
    title: str = Field(description="Alert title")
    description: str = Field(description="Detailed description")
    affected_services: List[str] = Field(description="Affected services/components")
    metrics: Dict[str, Any] = Field(description="Related metrics")
    recommended_actions: List[str] = Field(description="Recommended actions")
    escalation_needed: bool = Field(description="Whether to escalate to on-call")
    noise_score: float = Field(description="Likelihood this is a false positive (0-100)")


class MonitoringInsight(BaseModel):
    """Monitoring insight from analysis."""

    insight_type: str = Field(description="Type: trend, correlation, prediction, recommendation")
    title: str = Field(description="Insight title")
    description: str = Field(description="Detailed description")
    confidence: float = Field(description="Confidence level (0-100)")
    actionable: bool = Field(description="Whether this requires action")
    priority: str = Field(description="Priority: high, medium, low")


class MonitoringAnalysisResult(BaseModel):
    """Result of monitoring analysis."""

    overall_health: str = Field(description="Overall system health: healthy, degraded, critical")
    health_score: float = Field(description="Health score (0-100)")
    alerts: List[Alert] = Field(description="Generated alerts")
    insights: List[MonitoringInsight] = Field(description="Monitoring insights")
    summary: str = Field(description="Executive summary")
    recommendations: List[str] = Field(description="Proactive recommendations")


class IntelligentMonitorAgent(BaseAgent):
    """Agent for intelligent monitoring and alerting."""

    def __init__(self, **kwargs):
        super().__init__(name="IntelligentMonitorAgent", **kwargs)

    async def execute(
        self,
        metrics: Dict[str, Any],
        logs: Optional[str] = None,
        historical_data: Optional[Dict[str, Any]] = None,
    ) -> MonitoringAnalysisResult:
        """
        Analyze system monitoring data.

        Args:
            metrics: Current system metrics
            logs: Recent logs
            historical_data: Historical metrics for comparison

        Returns:
            MonitoringAnalysisResult with alerts and insights
        """
        logger.info("Analyzing system monitoring data")

        system_prompt = self._create_system_prompt()
        user_prompt = self._create_user_prompt(metrics, logs, historical_data)

        try:
            result = await self._generate_structured_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                schema=MonitoringAnalysisResult,
            )

            logger.info(
                f"Monitoring analysis completed: health={result.overall_health}, "
                f"score={result.health_score}, alerts={len(result.alerts)}"
            )

            return result

        except Exception as e:
            logger.error(f"Monitoring analysis failed: {e}")
            return MonitoringAnalysisResult(
                overall_health="unknown",
                health_score=0,
                alerts=[],
                insights=[],
                summary=f"Analysis failed: {str(e)}",
                recommendations=[],
            )

    def _create_system_prompt(self) -> str:
        """Create system prompt for monitoring analysis."""
        return """You are an expert SRE specializing in intelligent monitoring and alerting.

Your expertise includes:

1. **Alert Generation**:
   - Generate actionable alerts, not noise
   - Reduce false positives
   - Correlate related issues
   - Prioritize by business impact

2. **Pattern Recognition**:
   - Identify trends and patterns
   - Detect early warning signs
   - Recognize cascading failures
   - Spot seasonal variations

3. **Intelligent Insights**:
   - Proactive recommendations
   - Capacity planning insights
   - Performance optimization opportunities
   - Security concerns

4. **Alert Fatigue Reduction**:
   - Group related alerts
   - Suppress low-value alerts
   - Provide context with each alert
   - Suggest alert tuning

Alert Severity Guidelines:
- **Critical**: System down, data loss, security breach
- **High**: Significant degradation, user impact
- **Medium**: Potential issues, degraded performance
- **Low**: Minor issues, informational
- **Info**: Proactive insights, recommendations

Provide:
- Overall system health assessment
- High-quality, actionable alerts
- Proactive insights and recommendations
- Clear remediation steps
- Escalation guidance
"""

    def _create_user_prompt(
        self,
        metrics: Dict[str, Any],
        logs: Optional[str] = None,
        historical_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create user prompt for monitoring analysis."""
        prompt = "Analyze the following monitoring data:\n\n"

        prompt += "**Current Metrics**:\n"
        prompt += self._format_metrics(metrics)
        prompt += "\n"

        if logs:
            prompt += f"**Recent Logs** (sample):\n```\n{logs[:1000]}\n```\n\n"

        if historical_data:
            prompt += "**Historical Data** (for comparison):\n"
            prompt += self._format_metrics(historical_data)
            prompt += "\n"

        prompt += """Provide:
1. Overall system health assessment
2. Actionable alerts (filter out noise)
3. Proactive insights and trends
4. Specific recommendations
5. Escalation guidance

Focus on signal over noise - only alert on important issues.
"""

        return prompt

    def _format_metrics(self, metrics: Dict[str, Any]) -> str:
        """Format metrics for prompt."""
        formatted = ""
        for key, value in metrics.items():
            if isinstance(value, dict):
                formatted += f"\n{key}:\n"
                for sub_key, sub_value in value.items():
                    formatted += f"  - {sub_key}: {sub_value}\n"
            else:
                formatted += f"- {key}: {value}\n"
        return formatted

    async def analyze_alert_quality(
        self,
        alert_history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Analyze alert quality and suggest improvements.

        Args:
            alert_history: Historical alert data with outcomes

        Returns:
            Alert quality analysis and recommendations
        """
        logger.info(f"Analyzing quality of {len(alert_history)} historical alerts")

        system_prompt = """You are an expert at alert optimization and reducing alert fatigue.

Analyze alert history to identify:
1. False positive patterns
2. Low-value alerts
3. Missing alerts (blind spots)
4. Alert tuning opportunities
5. Alert grouping opportunities

Suggest specific improvements to reduce noise and increase signal.
"""

        user_prompt = f"""Analyze these historical alerts:

**Alert History**:
"""
        for i, alert in enumerate(alert_history[:50]):  # Limit for token management
            user_prompt += f"\n{i+1}. {alert}\n"

        if len(alert_history) > 50:
            user_prompt += f"\n... and {len(alert_history) - 50} more alerts\n"

        user_prompt += """
Provide:
1. Alert quality metrics
2. False positive analysis
3. Alert tuning recommendations
4. Suggested alert rules improvements
"""

        try:
            response = await self._generate_response(user_prompt, system_prompt)

            return {
                "analysis": response,
                "quality_score": 75,  # Can be parsed from response
            }

        except Exception as e:
            logger.error(f"Alert quality analysis failed: {e}")
            return {"analysis": f"Analysis failed: {str(e)}", "quality_score": 0}

    async def generate_capacity_insights(
        self,
        resource_usage: Dict[str, Any],
        growth_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate capacity planning insights.

        Args:
            resource_usage: Current resource usage
            growth_data: Historical growth data

        Returns:
            Capacity planning insights and recommendations
        """
        logger.info("Generating capacity planning insights")

        system_prompt = """You are an expert in capacity planning and resource optimization.

Analyze resource usage to provide:
1. Current capacity utilization
2. Projected resource needs
3. Scaling recommendations
4. Cost optimization opportunities
5. Risk assessment (when will we run out of capacity)

Consider growth trends and seasonal patterns.
"""

        user_prompt = f"""Analyze capacity planning for these resources:

**Current Resource Usage**:
{self._format_metrics(resource_usage)}
"""

        if growth_data:
            user_prompt += f"\n**Growth Data**:\n{self._format_metrics(growth_data)}\n"

        user_prompt += """
Provide:
1. Current utilization analysis
2. Capacity forecast (30, 60, 90 days)
3. Scaling recommendations
4. Cost optimization opportunities
5. Risk timeline (when capacity will be exceeded)
"""

        try:
            response = await self._generate_response(user_prompt, system_prompt)

            return {
                "insights": response,
                "urgency": "medium",  # Can be parsed from response
            }

        except Exception as e:
            logger.error(f"Capacity insights generation failed: {e}")
            return {"insights": f"Generation failed: {str(e)}", "urgency": "unknown"}

    async def correlate_incidents(
        self,
        incidents: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Correlate related incidents to find common causes.

        Args:
            incidents: List of incidents to correlate

        Returns:
            Correlation analysis
        """
        logger.info(f"Correlating {len(incidents)} incidents")

        system_prompt = """You are an expert at incident correlation and root cause analysis.

Correlate incidents to identify:
1. Common root causes
2. Cascading failure patterns
3. Shared components/dependencies
4. Time-based correlations
5. Environment-specific patterns

Provide insights to prevent future incidents.
"""

        user_prompt = "Correlate these incidents:\n\n"

        for i, incident in enumerate(incidents[:20]):
            user_prompt += f"\n**Incident {i+1}**:\n{incident}\n"

        user_prompt += """
Identify:
1. Common patterns and root causes
2. Related incident groups
3. Prevention strategies
4. Systemic issues
"""

        try:
            response = await self._generate_response(user_prompt, system_prompt)

            return {
                "correlations": response,
                "common_patterns": [],  # Can be parsed from response
            }

        except Exception as e:
            logger.error(f"Incident correlation failed: {e}")
            return {"correlations": f"Correlation failed: {str(e)}", "common_patterns": []}
