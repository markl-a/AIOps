"""Anomaly Detector Agent - AI-powered anomaly detection for systems and metrics."""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from aiops.agents.base_agent import BaseAgent
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class Anomaly(BaseModel):
    """Represents a detected anomaly."""

    severity: str = Field(description="Severity: critical, high, medium, low")
    category: str = Field(description="Category: performance, error_rate, resource, security, behavior")
    metric_name: str = Field(description="Affected metric or component")
    description: str = Field(description="Anomaly description")
    detected_at: str = Field(description="Detection timestamp")
    confidence: float = Field(description="Detection confidence (0-100)")
    baseline: Optional[Any] = Field(default=None, description="Normal baseline value")
    current_value: Any = Field(description="Current anomalous value")
    deviation: Optional[str] = Field(default=None, description="Deviation from baseline")


class AnomalyDetectionResult(BaseModel):
    """Result of anomaly detection."""

    total_anomalies: int = Field(description="Total number of anomalies detected")
    critical_count: int = Field(description="Number of critical anomalies")
    anomalies: List[Anomaly] = Field(description="Detected anomalies")
    summary: str = Field(description="Summary of findings")
    recommendations: List[str] = Field(description="Recommended actions")
    potential_impacts: List[str] = Field(description="Potential business impacts")


class AnomalyDetectorAgent(BaseAgent):
    """Agent for anomaly detection in systems and metrics."""

    def __init__(self, **kwargs):
        super().__init__(name="AnomalyDetectorAgent", **kwargs)

    async def execute(
        self,
        metrics: Dict[str, Any],
        baseline: Optional[Dict[str, Any]] = None,
        context: Optional[str] = None,
    ) -> AnomalyDetectionResult:
        """
        Detect anomalies in system metrics.

        Args:
            metrics: Current metrics data
            baseline: Baseline/historical metrics for comparison
            context: Additional context about the system

        Returns:
            AnomalyDetectionResult with detected anomalies
        """
        logger.info("Detecting anomalies in system metrics")

        system_prompt = self._create_system_prompt()
        user_prompt = self._create_user_prompt(metrics, baseline, context)

        try:
            result = await self._generate_structured_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                schema=AnomalyDetectionResult,
            )

            logger.info(
                f"Anomaly detection completed: {result.total_anomalies} anomalies found, "
                f"{result.critical_count} critical"
            )

            return result

        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return AnomalyDetectionResult(
                total_anomalies=0,
                critical_count=0,
                anomalies=[],
                summary=f"Detection failed: {str(e)}",
                recommendations=[],
                potential_impacts=[],
            )

    def _create_system_prompt(self) -> str:
        """Create system prompt for anomaly detection."""
        return """You are an expert SRE and anomaly detection specialist.

Detect anomalies by analyzing:

1. **Performance Anomalies**:
   - Latency spikes
   - Throughput degradation
   - Response time increases

2. **Error Rate Anomalies**:
   - Sudden error increases
   - New error types
   - Error pattern changes

3. **Resource Anomalies**:
   - CPU/Memory spikes
   - Disk space issues
   - Network saturation

4. **Behavioral Anomalies**:
   - Traffic pattern changes
   - Unusual user behavior
   - Deployment impact

5. **Security Anomalies**:
   - Suspicious access patterns
   - Failed authentication spikes
   - Unusual API calls

Detection Criteria:
- Compare against baseline (if available)
- Identify statistical outliers
- Recognize known anomaly patterns
- Consider temporal context (time of day, day of week)
- Assess business impact

Provide:
- Confidence level for each detection
- Clear description of the anomaly
- Potential root causes
- Recommended actions
- Business impact assessment
"""

    def _create_user_prompt(
        self,
        metrics: Dict[str, Any],
        baseline: Optional[Dict[str, Any]] = None,
        context: Optional[str] = None,
    ) -> str:
        """Create user prompt for anomaly detection."""
        prompt = "Analyze the following metrics for anomalies:\n\n"

        if context:
            prompt += f"**System Context**: {context}\n\n"

        prompt += "**Current Metrics**:\n"
        prompt += self._format_metrics(metrics)
        prompt += "\n"

        if baseline:
            prompt += "**Baseline Metrics** (normal behavior):\n"
            prompt += self._format_metrics(baseline)
            prompt += "\n"

        prompt += """Detect and report:
1. All anomalies with confidence scores
2. Severity and category for each
3. Deviation from baseline
4. Potential impacts
5. Recommended actions
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

    async def detect_time_series_anomalies(
        self,
        time_series_data: List[Dict[str, Any]],
        metric_name: str,
    ) -> AnomalyDetectionResult:
        """
        Detect anomalies in time series data.

        Args:
            time_series_data: Time series data points
            metric_name: Name of the metric

        Returns:
            AnomalyDetectionResult for time series
        """
        logger.info(f"Detecting anomalies in time series: {metric_name}")

        system_prompt = """You are a time series analysis expert.

Detect anomalies in time series data:
- Sudden spikes or drops
- Trend changes
- Seasonality violations
- Level shifts
- Pattern breaks

Use statistical reasoning to identify outliers.
"""

        user_prompt = f"""Analyze this time series for anomalies:

**Metric**: {metric_name}

**Data Points**:
"""
        for i, point in enumerate(time_series_data[:100]):  # Limit to avoid token overflow
            user_prompt += f"  {i+1}. {point}\n"

        if len(time_series_data) > 100:
            user_prompt += f"\n... and {len(time_series_data) - 100} more data points\n"

        user_prompt += "\nIdentify anomalous points with timestamps and severity."

        try:
            result = await self._generate_structured_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                schema=AnomalyDetectionResult,
            )

            logger.info(f"Time series analysis completed: {result.total_anomalies} anomalies")
            return result

        except Exception as e:
            logger.error(f"Time series anomaly detection failed: {e}")
            return AnomalyDetectionResult(
                total_anomalies=0,
                critical_count=0,
                anomalies=[],
                summary=f"Detection failed: {str(e)}",
                recommendations=[],
                potential_impacts=[],
            )

    async def predict_failures(
        self,
        metrics: Dict[str, Any],
        historical_incidents: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Predict potential system failures based on current metrics.

        Args:
            metrics: Current system metrics
            historical_incidents: Past incidents and their indicators

        Returns:
            Failure predictions with probabilities
        """
        logger.info("Predicting potential system failures")

        system_prompt = """You are an expert at predicting system failures.

Analyze metrics to predict:
- Imminent failures
- Degradation trends
- Resource exhaustion
- Cascading failures

Use historical incident data to identify warning patterns.
Provide probability and timeframe for predictions.
"""

        user_prompt = f"""Predict potential failures based on these metrics:

**Current Metrics**:
{self._format_metrics(metrics)}
"""

        if historical_incidents:
            user_prompt += "\n**Historical Incidents**:\n"
            for incident in historical_incidents[:10]:
                user_prompt += f"- {incident}\n"

        user_prompt += """
Provide:
1. Predicted failure scenarios
2. Probability (0-100%)
3. Estimated time to failure
4. Early warning indicators
5. Preventive actions
"""

        try:
            response = await self._generate_response(user_prompt, system_prompt)

            return {
                "predictions": response,
                "confidence": "medium",  # Can be parsed from response
            }

        except Exception as e:
            logger.error(f"Failure prediction failed: {e}")
            return {"predictions": f"Prediction failed: {str(e)}", "confidence": "none"}
