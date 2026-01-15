"""Tests for Compliance Checker Agent."""

import pytest
from unittest.mock import AsyncMock, patch
from aiops.agents.compliance_checker import (
    ComplianceCheckerAgent,
    ComplianceReport,
    ComplianceViolation,
    ComplianceScore,
)


@pytest.fixture
def compliance_agent():
    """Create compliance checker agent."""
    return ComplianceCheckerAgent()


@pytest.fixture
def sample_infrastructure_config():
    """Sample infrastructure configuration with issues."""
    return {
        "kubernetes": {
            "pod_security_policy": "disabled",
            "network_policy": "allow_all",
            "secrets_encryption": False,
        },
        "database": {
            "encryption_at_rest": False,
            "ssl_mode": "disable",
            "backup_enabled": True,
        },
        "storage": {
            "encryption": "none",
            "public_access": True,
        }
    }


@pytest.fixture
def sample_access_policies():
    """Sample access control policies."""
    return {
        "iam": {
            "mfa_required": False,
            "password_policy": {
                "min_length": 6,
                "require_special": False,
            },
            "root_access": True,
        },
        "roles": [
            {"name": "admin", "permissions": "*"},
        ]
    }


@pytest.mark.asyncio
async def test_compliance_check_soc2(compliance_agent, sample_infrastructure_config, sample_access_policies):
    """Test SOC2 compliance checking."""
    mock_response = {
        "overall_score": 65.0,
        "scores_by_standard": [
            {
                "standard": "SOC2",
                "score": 65.0,
                "total_controls": 50,
                "passing_controls": 32,
                "failing_controls": 18,
                "exempted_controls": 0,
            }
        ],
        "violations": [
            {
                "rule_id": "SOC2-CC6.1",
                "standard": "SOC2",
                "severity": "critical",
                "category": "encryption",
                "resource": "database",
                "description": "Database encryption at rest not enabled",
                "current_state": "encryption_at_rest: false",
                "required_state": "encryption_at_rest: true",
                "remediation": "Enable encryption at rest for database",
                "automation_available": True,
                "compliance_control": "CC6.1 - Logical Access Security",
            },
            {
                "rule_id": "SOC2-CC6.6",
                "standard": "SOC2",
                "severity": "high",
                "category": "access",
                "resource": "iam",
                "description": "MFA not required for all users",
                "current_state": "mfa_required: false",
                "required_state": "mfa_required: true",
                "remediation": "Enable MFA requirement for all users",
                "automation_available": True,
                "compliance_control": "CC6.6 - Authentication",
            },
        ],
        "recommendations": [
            "Enable encryption at rest for all data stores",
            "Implement MFA for all user accounts",
            "Review and restrict network policies",
        ],
        "audit_trail": [],
        "next_review_date": "2025-06-15",
        "executive_summary": "Infrastructure has significant compliance gaps requiring immediate attention.",
    }

    with patch.object(
        compliance_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_response)
    ):
        result = await compliance_agent.execute(
            environment="production",
            standards=["SOC2"],
            infrastructure_config=sample_infrastructure_config,
            access_policies=sample_access_policies,
        )

        assert isinstance(result, ComplianceReport)
        assert result.overall_score == 65.0
        assert result.environment == "production"
        assert "SOC2" in result.standards_checked
        assert len(result.violations) == 2
        assert result.critical_violations == 1


@pytest.mark.asyncio
async def test_compliance_check_hipaa(compliance_agent):
    """Test HIPAA compliance checking."""
    mock_response = {
        "overall_score": 78.0,
        "scores_by_standard": [
            {
                "standard": "HIPAA",
                "score": 78.0,
                "total_controls": 30,
                "passing_controls": 23,
                "failing_controls": 7,
                "exempted_controls": 0,
            }
        ],
        "violations": [
            {
                "rule_id": "HIPAA-164.312(a)",
                "standard": "HIPAA",
                "severity": "critical",
                "category": "access_control",
                "resource": "ehr_system",
                "description": "PHI access not properly restricted",
                "current_state": "unrestricted access",
                "required_state": "role-based access control",
                "remediation": "Implement RBAC for PHI access",
                "automation_available": False,
                "compliance_control": "164.312(a) - Access Control",
            },
        ],
        "recommendations": [
            "Implement audit logging for all PHI access",
            "Enable encryption for PHI at rest and in transit",
        ],
        "audit_trail": [],
        "next_review_date": "2025-04-01",
        "executive_summary": "HIPAA compliance needs improvement in access control areas.",
    }

    encryption_config = {
        "phi_encryption": "aes-256",
        "key_management": "aws_kms",
        "in_transit": "tls_1_3",
    }

    with patch.object(
        compliance_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_response)
    ):
        result = await compliance_agent.execute(
            environment="healthcare-prod",
            standards=["HIPAA"],
            encryption_config=encryption_config,
        )

        assert isinstance(result, ComplianceReport)
        assert "HIPAA" in result.standards_checked
        assert any(v.standard == "HIPAA" for v in result.violations)
        assert result.overall_score == 78.0


@pytest.mark.asyncio
async def test_compliance_check_multiple_standards(compliance_agent):
    """Test checking compliance against multiple standards."""
    mock_response = {
        "overall_score": 72.0,
        "scores_by_standard": [
            {
                "standard": "SOC2",
                "score": 75.0,
                "total_controls": 50,
                "passing_controls": 38,
                "failing_controls": 12,
                "exempted_controls": 0,
            },
            {
                "standard": "GDPR",
                "score": 68.0,
                "total_controls": 40,
                "passing_controls": 27,
                "failing_controls": 13,
                "exempted_controls": 0,
            },
            {
                "standard": "PCI-DSS",
                "score": 72.0,
                "total_controls": 60,
                "passing_controls": 43,
                "failing_controls": 17,
                "exempted_controls": 0,
            },
        ],
        "violations": [
            {
                "rule_id": "GDPR-Art17",
                "standard": "GDPR",
                "severity": "high",
                "category": "data_rights",
                "resource": "user_data_store",
                "description": "Right to erasure not fully implemented",
                "current_state": "manual deletion only",
                "required_state": "automated deletion capability",
                "remediation": "Implement automated data deletion workflow",
                "automation_available": True,
                "compliance_control": "Article 17 - Right to Erasure",
            },
            {
                "rule_id": "PCI-DSS-3.4",
                "standard": "PCI-DSS",
                "severity": "critical",
                "category": "data_protection",
                "resource": "cardholder_data",
                "description": "PAN not properly masked in logs",
                "current_state": "full PAN visible",
                "required_state": "masked PAN (last 4 digits only)",
                "remediation": "Implement PAN masking in all log outputs",
                "automation_available": True,
                "compliance_control": "3.4 - Render PAN Unreadable",
            },
        ],
        "recommendations": [
            "Implement data subject access request automation",
            "Deploy PAN tokenization solution",
        ],
        "audit_trail": [],
        "next_review_date": "2025-03-01",
        "executive_summary": "Multiple compliance frameworks evaluated with varying results.",
    }

    with patch.object(
        compliance_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_response)
    ):
        result = await compliance_agent.execute(
            environment="production",
            standards=["SOC2", "GDPR", "PCI-DSS"],
        )

        assert isinstance(result, ComplianceReport)
        assert len(result.standards_checked) == 3
        assert len(result.scores_by_standard) == 3
        assert any(s.standard == "GDPR" for s in result.scores_by_standard)


@pytest.mark.asyncio
async def test_generate_remediation_plan(compliance_agent):
    """Test remediation plan generation."""
    # Create a mock compliance report
    report = ComplianceReport(
        report_id="COMP-test-001",
        environment="production",
        standards_checked=["SOC2"],
        overall_score=60.0,
        scores_by_standard=[],
        violations=[
            ComplianceViolation(
                rule_id="SOC2-CC6.1",
                standard="SOC2",
                severity="critical",
                category="encryption",
                resource="database",
                description="Database encryption not enabled",
                current_state="unencrypted",
                required_state="encrypted",
                remediation="Enable encryption",
                automation_available=True,
                compliance_control="CC6.1",
            ),
            ComplianceViolation(
                rule_id="SOC2-CC6.6",
                standard="SOC2",
                severity="high",
                category="access",
                resource="iam",
                description="MFA not enabled",
                current_state="disabled",
                required_state="enabled",
                remediation="Enable MFA",
                automation_available=True,
                compliance_control="CC6.6",
            ),
        ],
        critical_violations=1,
        recommendations=["Enable encryption", "Enable MFA"],
        audit_trail=[],
        next_review_date="2025-06-15",
        executive_summary="Compliance gaps found",
    )

    mock_plan = """
# Remediation Plan - 12 Weeks

## Week 1-2: Critical Issues
- Enable database encryption
- Begin MFA rollout

## Week 3-4: High Priority
- Complete MFA deployment
- Update IAM policies

## Week 5-8: Medium Priority
- Network policy updates
- Logging improvements

## Week 9-12: Validation
- Security testing
- Compliance audit preparation
"""

    with patch.object(
        compliance_agent, "_generate_response", new=AsyncMock(return_value=mock_plan)
    ):
        plan = await compliance_agent.generate_remediation_plan(report, timeline_weeks=12)

        assert "Remediation Plan" in plan
        assert "Week" in plan


@pytest.mark.asyncio
async def test_error_handling(compliance_agent):
    """Test error handling during compliance check."""
    with patch.object(
        compliance_agent,
        "_generate_structured_response",
        side_effect=Exception("LLM service unavailable"),
    ):
        # The agent should handle errors gracefully
        try:
            result = await compliance_agent.execute(
                environment="test",
                standards=["SOC2"],
            )
            # If no exception, result should be a valid report
            assert result is not None
        except Exception as e:
            # Error should propagate but be meaningful
            assert "LLM service unavailable" in str(e) or "service" in str(e).lower()


def test_build_compliance_prompt(compliance_agent):
    """Test compliance prompt building."""
    prompt = compliance_agent._build_compliance_prompt(
        environment="production",
        standards=["SOC2", "HIPAA"],
        infrastructure_config={"encryption": True},
        code_repositories=None,
        access_policies={"mfa": True},
        encryption_config=None,
        logging_config=None,
        data_flows=None,
    )

    assert "production" in prompt
    assert "SOC2" in prompt
    assert "HIPAA" in prompt
    assert "Infrastructure Configuration" in prompt
    assert "Access Control Policies" in prompt


def test_supported_standards(compliance_agent):
    """Test that supported standards list is populated."""
    assert len(compliance_agent.SUPPORTED_STANDARDS) > 0
    assert "SOC2" in compliance_agent.SUPPORTED_STANDARDS
    assert "HIPAA" in compliance_agent.SUPPORTED_STANDARDS
    assert "PCI-DSS" in compliance_agent.SUPPORTED_STANDARDS
    assert "GDPR" in compliance_agent.SUPPORTED_STANDARDS
