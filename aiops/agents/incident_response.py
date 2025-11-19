"""
Incident Response Agent

This agent provides automated incident analysis, root cause detection,
and recommended remediation steps for production incidents.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from aiops.agents.base_agent import BaseAgent
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class IncidentTimeline(BaseModel):
    """Timeline event in an incident"""
    timestamp: str = Field(description="Event timestamp")
    event_type: str = Field(description="Type of event (alert, action, change)")
    description: str = Field(description="Event description")
    severity: str = Field(description="Event severity")
    source: str = Field(description="Source system/component")


class RootCauseAnalysis(BaseModel):
    """Root cause analysis result"""
    likely_cause: str = Field(description="Most likely root cause")
    confidence: float = Field(description="Confidence level (0-100)")
    contributing_factors: List[str] = Field(description="Contributing factors")
    evidence: List[str] = Field(description="Supporting evidence")
    similar_incidents: List[str] = Field(description="Similar past incidents")


class RemediationStep(BaseModel):
    """Recommended remediation step"""
    step_number: int = Field(description="Step sequence number")
    action: str = Field(description="Action to take")
    command: Optional[str] = Field(description="Command to execute if applicable")
    expected_outcome: str = Field(description="Expected result")
    rollback_plan: Optional[str] = Field(description="How to rollback if needed")
    risk_level: str = Field(description="Risk level: low, medium, high")


class IncidentAnalysisResult(BaseModel):
    """Complete incident analysis result"""
    incident_id: str = Field(description="Unique incident identifier")
    analyzed_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    severity: str = Field(description="critical, high, medium, low")
    title: str = Field(description="Incident title")
    description: str = Field(description="Detailed description")
    affected_services: List[str] = Field(description="List of affected services")
    timeline: List[IncidentTimeline] = Field(description="Incident timeline")
    root_cause: RootCauseAnalysis = Field(description="Root cause analysis")
    remediation_steps: List[RemediationStep] = Field(description="Recommended remediation steps")
    prevention_measures: List[str] = Field(description="Measures to prevent recurrence")
    estimated_impact: Dict[str, Any] = Field(description="Estimated business impact")
    communication_plan: List[str] = Field(description="Stakeholder communication plan")
    executive_summary: str = Field(description="Executive summary for stakeholders")


class IncidentResponseAgent(BaseAgent):
    """
    AI-powered incident response agent.

    Features:
    - Automated incident analysis
    - Root cause detection
    - Remediation recommendations
    - Impact assessment
    - Communication planning
    - Prevention strategies
    """

    def __init__(
        self,
        llm_provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = 0.3,
    ):
        super().__init__(
            name="IncidentResponse",
            llm_provider=llm_provider,
            model=model,
            temperature=temperature,
        )

    async def execute(
        self,
        incident_data: Dict[str, Any],
        logs: Optional[List[str]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        alerts: Optional[List[Dict[str, Any]]] = None,
    ) -> IncidentAnalysisResult:
        """
        Analyze an incident and provide response recommendations.

        Args:
            incident_data: Incident information (description, severity, services)
            logs: Recent log entries related to the incident
            metrics: Relevant metrics data
            alerts: Alert history

        Returns:
            IncidentAnalysisResult with analysis and recommendations
        """
        logger.info(f"Analyzing incident: {incident_data.get('title', 'Unknown')}")

        # Build comprehensive analysis prompt
        prompt = self._build_analysis_prompt(incident_data, logs, metrics, alerts)

        # Define response schema
        schema = {
            "type": "object",
            "properties": {
                "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "affected_services": {"type": "array", "items": {"type": "string"}},
                "timeline": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "timestamp": {"type": "string"},
                            "event_type": {"type": "string"},
                            "description": {"type": "string"},
                            "severity": {"type": "string"},
                            "source": {"type": "string"},
                        },
                    },
                },
                "root_cause": {
                    "type": "object",
                    "properties": {
                        "likely_cause": {"type": "string"},
                        "confidence": {"type": "number"},
                        "contributing_factors": {"type": "array", "items": {"type": "string"}},
                        "evidence": {"type": "array", "items": {"type": "string"}},
                        "similar_incidents": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "remediation_steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "step_number": {"type": "integer"},
                            "action": {"type": "string"},
                            "command": {"type": "string"},
                            "expected_outcome": {"type": "string"},
                            "rollback_plan": {"type": "string"},
                            "risk_level": {"type": "string"},
                        },
                    },
                },
                "prevention_measures": {"type": "array", "items": {"type": "string"}},
                "estimated_impact": {"type": "object"},
                "communication_plan": {"type": "array", "items": {"type": "string"}},
                "executive_summary": {"type": "string"},
            },
            "required": [
                "severity", "title", "description", "affected_services",
                "root_cause", "remediation_steps", "executive_summary"
            ],
        }

        # Generate structured analysis
        system_prompt = """You are an expert SRE and incident responder. Analyze incidents thoroughly,
        identify root causes, and provide actionable remediation steps. Consider system dependencies,
        failure modes, and business impact. Prioritize safety and rollback plans."""

        response = await self._generate_structured_response(prompt, schema, system_prompt)

        # Create result
        result = IncidentAnalysisResult(
            incident_id=incident_data.get("incident_id", f"INC-{datetime.now().strftime('%Y%m%d-%H%M%S')}"),
            severity=response.get("severity", "medium"),
            title=response.get("title", ""),
            description=response.get("description", ""),
            affected_services=response.get("affected_services", []),
            timeline=[IncidentTimeline(**t) for t in response.get("timeline", [])],
            root_cause=RootCauseAnalysis(**response.get("root_cause", {})),
            remediation_steps=[RemediationStep(**s) for s in response.get("remediation_steps", [])],
            prevention_measures=response.get("prevention_measures", []),
            estimated_impact=response.get("estimated_impact", {}),
            communication_plan=response.get("communication_plan", []),
            executive_summary=response.get("executive_summary", ""),
        )

        logger.info(
            f"Incident analysis complete: {len(result.remediation_steps)} remediation steps, "
            f"root cause confidence: {result.root_cause.confidence}%"
        )

        return result

    def _build_analysis_prompt(
        self,
        incident_data: Dict[str, Any],
        logs: Optional[List[str]],
        metrics: Optional[Dict[str, Any]],
        alerts: Optional[List[Dict[str, Any]]],
    ) -> str:
        """Build comprehensive incident analysis prompt"""
        prompt_parts = [
            "# Incident Analysis Request\n",
            f"## Incident Information\n{self._format_incident_data(incident_data)}\n",
        ]

        if logs:
            prompt_parts.append(f"\n## Recent Logs\n```\n{chr(10).join(logs[:50])}\n```\n")

        if metrics:
            prompt_parts.append(f"\n## Metrics Data\n```json\n{metrics}\n```\n")

        if alerts:
            prompt_parts.append(f"\n## Alert History\n{self._format_alerts(alerts)}\n")

        prompt_parts.append("""
## Analysis Requirements

Please provide:
1. **Timeline**: Reconstruct the incident timeline from available data
2. **Root Cause**: Identify the most likely root cause with confidence level
3. **Remediation Steps**: Detailed, actionable steps to resolve the incident
4. **Prevention**: Measures to prevent similar incidents
5. **Impact Assessment**: Estimate business impact (users, revenue, reputation)
6. **Communication Plan**: How to communicate with stakeholders

Prioritize:
- Safety and risk mitigation
- Quick recovery with rollback plans
- Evidence-based analysis
- Clear, actionable recommendations
""")

        return "".join(prompt_parts)

    def _format_incident_data(self, incident_data: Dict[str, Any]) -> str:
        """Format incident data for prompt"""
        lines = []
        for key, value in incident_data.items():
            lines.append(f"- **{key}**: {value}")
        return "\n".join(lines)

    def _format_alerts(self, alerts: List[Dict[str, Any]]) -> str:
        """Format alerts for prompt"""
        lines = []
        for i, alert in enumerate(alerts[:20], 1):
            lines.append(
                f"{i}. [{alert.get('severity', 'unknown')}] "
                f"{alert.get('name', 'Unknown')} - {alert.get('message', '')}"
            )
        return "\n".join(lines)

    async def generate_postmortem(
        self,
        incident_analysis: IncidentAnalysisResult,
        resolution_notes: Optional[str] = None,
    ) -> str:
        """
        Generate a postmortem report from incident analysis.

        Args:
            incident_analysis: Completed incident analysis
            resolution_notes: Notes on how the incident was resolved

        Returns:
            Formatted postmortem report
        """
        prompt = f"""Generate a comprehensive postmortem report for the following incident:

# Incident Details
- ID: {incident_analysis.incident_id}
- Title: {incident_analysis.title}
- Severity: {incident_analysis.severity}
- Affected Services: {', '.join(incident_analysis.affected_services)}

# Root Cause
{incident_analysis.root_cause.likely_cause}
Confidence: {incident_analysis.root_cause.confidence}%

# Resolution Notes
{resolution_notes or 'No additional notes provided'}

# Prevention Measures
{chr(10).join(f'- {m}' for m in incident_analysis.prevention_measures)}

Please create a detailed postmortem report including:
1. Executive Summary
2. Timeline of Events
3. Root Cause Analysis
4. Impact Assessment
5. What Went Well
6. What Could Be Improved
7. Action Items
8. Lessons Learned

Format as professional markdown document suitable for sharing with engineering leadership.
"""

        system_prompt = """You are a senior SRE writing a postmortem report. Be honest about failures,
        focus on learning, avoid blame, and provide actionable improvements."""

        return await self._generate_response(prompt, system_prompt)
