"""
Compliance Checker Agent

This agent validates infrastructure, code, and configurations against
security and regulatory compliance standards (SOC2, HIPAA, PCI-DSS, GDPR, etc.)
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from aiops.agents.base_agent import BaseAgent
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class ComplianceViolation(BaseModel):
    """Single compliance violation"""
    rule_id: str = Field(description="Compliance rule identifier")
    standard: str = Field(description="Compliance standard (SOC2, HIPAA, etc.)")
    severity: str = Field(description="critical, high, medium, low")
    category: str = Field(description="Category (data, access, encryption, etc.)")
    resource: str = Field(description="Affected resource")
    description: str = Field(description="Violation description")
    current_state: str = Field(description="Current non-compliant state")
    required_state: str = Field(description="Required compliant state")
    remediation: str = Field(description="How to fix")
    automation_available: bool = Field(description="Can be auto-remediated")
    compliance_control: str = Field(description="Related compliance control")


class ComplianceScore(BaseModel):
    """Compliance score for a standard"""
    standard: str = Field(description="Compliance standard name")
    score: float = Field(description="Compliance score (0-100)")
    total_controls: int = Field(description="Total controls checked")
    passing_controls: int = Field(description="Passing controls")
    failing_controls: int = Field(description="Failing controls")
    exempted_controls: int = Field(description="Exempted controls")


class ComplianceReport(BaseModel):
    """Complete compliance check report"""
    report_id: str = Field(description="Unique report identifier")
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    environment: str = Field(description="Environment checked (prod, staging, etc.)")
    standards_checked: List[str] = Field(description="Compliance standards evaluated")
    overall_score: float = Field(description="Overall compliance score (0-100)")
    scores_by_standard: List[ComplianceScore] = Field(description="Scores per standard")
    violations: List[ComplianceViolation] = Field(description="All violations found")
    critical_violations: int = Field(description="Count of critical violations")
    recommendations: List[str] = Field(description="High-level recommendations")
    audit_trail: List[Dict[str, Any]] = Field(description="Audit trail of checks")
    next_review_date: str = Field(description="Recommended next review date")
    executive_summary: str = Field(description="Executive summary")


class ComplianceCheckerAgent(BaseAgent):
    """
    AI-powered compliance checker.

    Features:
    - Multi-standard compliance checking (SOC2, HIPAA, PCI-DSS, GDPR, ISO27001)
    - Infrastructure configuration validation
    - Data protection and encryption checks
    - Access control validation
    - Audit logging verification
    - Automated remediation suggestions
    """

    SUPPORTED_STANDARDS = [
        "SOC2",
        "HIPAA",
        "PCI-DSS",
        "GDPR",
        "ISO27001",
        "NIST",
        "CIS",
    ]

    def __init__(
        self,
        llm_provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = 0.2,
    ):
        super().__init__(
            name="ComplianceChecker",
            llm_provider=llm_provider,
            model=model,
            temperature=temperature,
        )

    async def execute(
        self,
        environment: str,
        standards: List[str],
        infrastructure_config: Optional[Dict[str, Any]] = None,
        code_repositories: Optional[List[str]] = None,
        access_policies: Optional[Dict[str, Any]] = None,
        encryption_config: Optional[Dict[str, Any]] = None,
        logging_config: Optional[Dict[str, Any]] = None,
        data_flows: Optional[List[Dict[str, Any]]] = None,
    ) -> ComplianceReport:
        """
        Check compliance against specified standards.

        Args:
            environment: Environment name (production, staging, etc.)
            standards: List of compliance standards to check against
            infrastructure_config: Infrastructure configuration (K8s, cloud, etc.)
            code_repositories: Code repository configurations
            access_policies: IAM and access control policies
            encryption_config: Encryption configuration
            logging_config: Audit logging configuration
            data_flows: Data flow diagrams/descriptions

        Returns:
            ComplianceReport with violations and recommendations
        """
        logger.info(f"Checking compliance for {environment} against {standards}")

        # Validate requested standards
        invalid_standards = [s for s in standards if s not in self.SUPPORTED_STANDARDS]
        if invalid_standards:
            logger.warning(f"Unsupported standards: {invalid_standards}")

        # Build compliance check prompt
        prompt = self._build_compliance_prompt(
            environment, standards, infrastructure_config, code_repositories,
            access_policies, encryption_config, logging_config, data_flows
        )

        # Define response schema
        schema = {
            "type": "object",
            "properties": {
                "overall_score": {"type": "number", "minimum": 0, "maximum": 100},
                "scores_by_standard": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "standard": {"type": "string"},
                            "score": {"type": "number"},
                            "total_controls": {"type": "integer"},
                            "passing_controls": {"type": "integer"},
                            "failing_controls": {"type": "integer"},
                            "exempted_controls": {"type": "integer"},
                        },
                    },
                },
                "violations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "rule_id": {"type": "string"},
                            "standard": {"type": "string"},
                            "severity": {"type": "string"},
                            "category": {"type": "string"},
                            "resource": {"type": "string"},
                            "description": {"type": "string"},
                            "current_state": {"type": "string"},
                            "required_state": {"type": "string"},
                            "remediation": {"type": "string"},
                            "automation_available": {"type": "boolean"},
                            "compliance_control": {"type": "string"},
                        },
                    },
                },
                "recommendations": {"type": "array", "items": {"type": "string"}},
                "audit_trail": {"type": "array"},
                "next_review_date": {"type": "string"},
                "executive_summary": {"type": "string"},
            },
            "required": ["overall_score", "violations", "executive_summary"],
        }

        # Generate compliance analysis
        system_prompt = """You are an expert compliance auditor with deep knowledge of SOC2, HIPAA,
        PCI-DSS, GDPR, ISO27001, and other security standards. Evaluate configurations against
        compliance requirements, identify violations, and provide clear remediation steps.
        Be thorough but practical in your recommendations."""

        response = await self._generate_structured_response(prompt, schema, system_prompt)

        # Create report
        violations = [ComplianceViolation(**v) for v in response.get("violations", [])]
        critical_violations = sum(1 for v in violations if v.severity == "critical")

        report = ComplianceReport(
            report_id=f"COMP-{environment}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            environment=environment,
            standards_checked=standards,
            overall_score=response.get("overall_score", 0),
            scores_by_standard=[ComplianceScore(**s) for s in response.get("scores_by_standard", [])],
            violations=violations,
            critical_violations=critical_violations,
            recommendations=response.get("recommendations", []),
            audit_trail=response.get("audit_trail", []),
            next_review_date=response.get("next_review_date", ""),
            executive_summary=response.get("executive_summary", ""),
        )

        logger.info(
            f"Compliance check complete: {report.overall_score}% compliant, "
            f"{len(violations)} violations ({critical_violations} critical)"
        )

        return report

    def _build_compliance_prompt(
        self,
        environment: str,
        standards: List[str],
        infrastructure_config: Optional[Dict[str, Any]],
        code_repositories: Optional[List[str]],
        access_policies: Optional[Dict[str, Any]],
        encryption_config: Optional[Dict[str, Any]],
        logging_config: Optional[Dict[str, Any]],
        data_flows: Optional[List[Dict[str, Any]]],
    ) -> str:
        """Build comprehensive compliance check prompt"""
        prompt_parts = [
            f"# Compliance Check Request\n",
            f"Environment: {environment}\n",
            f"Standards: {', '.join(standards)}\n\n",
        ]

        if infrastructure_config:
            prompt_parts.append(f"## Infrastructure Configuration\n```yaml\n{infrastructure_config}\n```\n\n")

        if access_policies:
            prompt_parts.append(f"## Access Control Policies\n```json\n{access_policies}\n```\n\n")

        if encryption_config:
            prompt_parts.append(f"## Encryption Configuration\n```yaml\n{encryption_config}\n```\n\n")

        if logging_config:
            prompt_parts.append(f"## Audit Logging Configuration\n```yaml\n{logging_config}\n```\n\n")

        if data_flows:
            prompt_parts.append("## Data Flows\n")
            for i, flow in enumerate(data_flows, 1):
                prompt_parts.append(f"{i}. {flow.get('name', 'Unknown')}: {flow.get('description', '')}\n")
            prompt_parts.append("\n")

        prompt_parts.append(f"""
## Compliance Requirements

For each standard ({', '.join(standards)}), check:

### SOC2 (if applicable)
- Security: Access controls, encryption, monitoring
- Availability: Uptime, redundancy, backup/recovery
- Processing Integrity: Quality controls, error handling
- Confidentiality: Data protection, access restrictions
- Privacy: Data handling, consent, deletion

### HIPAA (if applicable)
- Administrative Safeguards: Policies, training, access management
- Physical Safeguards: Facility access, workstation security
- Technical Safeguards: Encryption, audit controls, authentication
- PHI Protection: Data encryption at rest and in transit

### PCI-DSS (if applicable)
- Network Security: Firewalls, encryption, secure transmission
- Data Protection: Cardholder data storage and transmission
- Access Control: Authentication, authorization, monitoring
- Vulnerability Management: Patching, secure coding

### GDPR (if applicable)
- Data Protection: Encryption, pseudonymization
- Privacy by Design: Data minimization, purpose limitation
- Subject Rights: Access, deletion, portability
- Breach Notification: Detection and reporting procedures

### ISO27001 (if applicable)
- Information Security Controls: 114 controls across 14 domains
- Risk Management: Assessment, treatment, monitoring
- ISMS: Documentation, policies, procedures

Provide:
1. Overall compliance score (0-100)
2. Score per standard
3. List of all violations with severity, description, and remediation
4. High-level recommendations for improving compliance
5. Suggested next review date
6. Executive summary
""")

        return "".join(prompt_parts)

    async def generate_remediation_plan(
        self,
        compliance_report: ComplianceReport,
        timeline_weeks: int = 12,
    ) -> str:
        """
        Generate a remediation plan for compliance violations.

        Args:
            compliance_report: Compliance report with violations
            timeline_weeks: Timeline for remediation in weeks

        Returns:
            Detailed remediation plan
        """
        critical = [v for v in compliance_report.violations if v.severity == "critical"]
        high = [v for v in compliance_report.violations if v.severity == "high"]

        prompt = f"""Generate a {timeline_weeks}-week remediation plan for the following compliance violations:

# Compliance Report Summary
- Environment: {compliance_report.environment}
- Overall Score: {compliance_report.overall_score}%
- Total Violations: {len(compliance_report.violations)}
- Critical: {len(critical)}
- High: {len(high)}

# Critical Violations
{chr(10).join(f"- {v.rule_id}: {v.description}" for v in critical[:10])}

# High Severity Violations
{chr(10).join(f"- {v.rule_id}: {v.description}" for v in high[:10])}

Create a detailed remediation plan including:
1. Prioritized task list (critical first)
2. Week-by-week timeline
3. Resource requirements (people, tools, budget)
4. Risk mitigation strategies
5. Validation and testing approach
6. Rollback plans for each change
7. Success metrics

Format as a professional project plan suitable for engineering leadership.
"""

        system_prompt = """You are a compliance program manager creating a remediation plan.
        Be realistic about timelines, prioritize based on risk, and consider dependencies."""

        return await self._generate_response(prompt, system_prompt)
