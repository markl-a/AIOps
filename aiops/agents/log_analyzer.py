"""Log Analyzer Agent - Intelligent log analysis and troubleshooting."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from aiops.agents.base_agent import BaseAgent
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class LogInsight(BaseModel):
    """Represents an insight from log analysis."""

    severity: str = Field(description="Severity: critical, error, warning, info")
    category: str = Field(description="Category: error, performance, security, deployment")
    message: str = Field(description="Insight message")
    affected_component: Optional[str] = Field(default=None, description="Affected system component")
    occurrences: int = Field(default=1, description="Number of occurrences")
    first_seen: Optional[str] = Field(default=None, description="First occurrence timestamp")
    last_seen: Optional[str] = Field(default=None, description="Last occurrence timestamp")


class RootCauseAnalysis(BaseModel):
    """Root cause analysis result."""

    root_cause: str = Field(description="Identified root cause")
    confidence: float = Field(description="Confidence level (0-100)")
    evidence: List[str] = Field(description="Evidence supporting this root cause")
    related_logs: List[str] = Field(description="Related log entries")


class LogAnalysisResult(BaseModel):
    """Result of log analysis."""

    summary: str = Field(description="Executive summary of log analysis")
    insights: List[LogInsight] = Field(description="Key insights from logs")
    root_causes: List[RootCauseAnalysis] = Field(description="Root cause analyses")
    recommendations: List[str] = Field(description="Recommendations to fix issues")
    anomalies: List[str] = Field(description="Detected anomalies")
    trends: Dict[str, Any] = Field(description="Trends and patterns")


class LogAnalyzerAgent(BaseAgent):
    """Agent for intelligent log analysis."""

    def __init__(self, **kwargs):
        super().__init__(name="LogAnalyzerAgent", **kwargs)

    async def execute(
        self,
        logs: str,
        context: Optional[str] = None,
        focus_areas: Optional[List[str]] = None,
    ) -> LogAnalysisResult:
        """
        Analyze logs and provide insights.

        Args:
            logs: Log data to analyze
            context: Additional context about the system
            focus_areas: Specific areas to focus on (errors, performance, security, etc.)

        Returns:
            LogAnalysisResult with insights and recommendations
        """
        logger.info(f"Analyzing logs ({len(logs)} chars)")

        system_prompt = self._create_system_prompt(focus_areas)
        user_prompt = self._create_user_prompt(logs, context)

        try:
            result = await self._generate_structured_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                schema=LogAnalysisResult,
            )

            logger.info(
                f"Log analysis completed: {len(result.insights)} insights, "
                f"{len(result.root_causes)} root causes identified"
            )

            return result

        except Exception as e:
            logger.error(f"Log analysis failed: {e}")
            return LogAnalysisResult(
                summary=f"Analysis failed: {str(e)}",
                insights=[],
                root_causes=[],
                recommendations=["Please retry the analysis"],
                anomalies=[],
                trends={},
            )

    def _create_system_prompt(self, focus_areas: Optional[List[str]] = None) -> str:
        """Create system prompt for log analysis."""
        prompt = """You are an expert SRE and system analyst specializing in log analysis.

Your task is to analyze logs and provide actionable insights:

1. **Error Detection**: Identify errors, exceptions, and failures
2. **Root Cause Analysis**: Determine underlying causes of issues
3. **Performance Issues**: Spot performance degradation, latency spikes
4. **Security Concerns**: Identify suspicious activities, security events
5. **Anomaly Detection**: Find unusual patterns or behaviors
6. **Trend Analysis**: Identify patterns over time

Analysis Approach:
- Correlate related log entries
- Identify cascading failures
- Distinguish symptoms from root causes
- Provide evidence-based conclusions
- Suggest specific, actionable fixes

Severity Levels:
- critical: System down, data loss, security breach
- error: Significant failures, broken functionality
- warning: Potential issues, degraded performance
- info: Important operational information
"""

        if focus_areas:
            prompt += f"\nFocus Areas: {', '.join(focus_areas)}\n"

        prompt += "\nProvide clear, actionable insights with specific recommendations."

        return prompt

    def _create_user_prompt(self, logs: str, context: Optional[str] = None) -> str:
        """Create user prompt for log analysis."""
        prompt = "Analyze the following logs:\n\n"

        if context:
            prompt += f"**System Context**: {context}\n\n"

        prompt += f"**Logs**:\n```\n{logs}\n```\n\n"
        prompt += """Provide:
1. Summary of key findings
2. Specific insights with severity levels
3. Root cause analysis for major issues
4. Actionable recommendations
5. Detected anomalies and trends
"""

        return prompt

    async def analyze_error_logs(
        self,
        error_logs: str,
        stack_traces: Optional[List[str]] = None,
    ) -> LogAnalysisResult:
        """
        Specialized analysis for error logs.

        Args:
            error_logs: Error log entries
            stack_traces: Associated stack traces

        Returns:
            LogAnalysisResult focused on errors
        """
        logger.info(f"Analyzing error logs ({len(error_logs)} chars)")

        system_prompt = """You are an expert at debugging and error analysis.

Focus on:
1. Exception types and error messages
2. Stack trace analysis
3. Error propagation patterns
4. Common error causes
5. Quick fixes and workarounds

Provide specific debugging steps and fixes.
"""

        user_prompt = f"""Analyze these error logs:

**Error Logs**:
```
{error_logs}
```
"""

        if stack_traces:
            user_prompt += f"\n**Stack Traces**:\n"
            for i, trace in enumerate(stack_traces, 1):
                user_prompt += f"\nTrace {i}:\n```\n{trace}\n```\n"

        user_prompt += "\nProvide root cause analysis and specific fixes."

        try:
            result = await self._generate_structured_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                schema=LogAnalysisResult,
            )

            logger.info(f"Error analysis completed: {len(result.root_causes)} root causes")
            return result

        except Exception as e:
            logger.error(f"Error log analysis failed: {e}")
            return LogAnalysisResult(
                summary=f"Analysis failed: {str(e)}",
                insights=[],
                root_causes=[],
                recommendations=[],
                anomalies=[],
                trends={},
            )

    async def detect_anomalies(
        self,
        logs: str,
        baseline_logs: Optional[str] = None,
    ) -> List[str]:
        """
        Detect anomalies by comparing with baseline.

        Args:
            logs: Current logs
            baseline_logs: Normal/baseline logs for comparison

        Returns:
            List of detected anomalies
        """
        logger.info("Detecting anomalies in logs")

        system_prompt = """You are an expert in anomaly detection.

Compare current logs against baseline to identify:
1. Unusual error rates
2. New error types
3. Performance degradation
4. Unexpected patterns
5. Security anomalies

Focus on deviations from normal behavior.
"""

        user_prompt = f"""Detect anomalies in the following logs:

**Current Logs**:
```
{logs}
```
"""

        if baseline_logs:
            user_prompt += f"\n**Baseline (Normal) Logs**:\n```\n{baseline_logs}\n```\n"

        user_prompt += "\nList all detected anomalies with explanations."

        try:
            response = await self._generate_response(user_prompt, system_prompt)

            # Parse anomalies from response
            anomalies = [
                line.strip("- ").strip()
                for line in response.split("\n")
                if line.strip().startswith("-") or line.strip().startswith("*")
            ]

            logger.info(f"Detected {len(anomalies)} anomalies")
            return anomalies

        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return [f"Anomaly detection failed: {str(e)}"]
