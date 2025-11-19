"""Tests for Security Scanner Agent."""

import pytest
from unittest.mock import AsyncMock, patch
from aiops.agents.security_scanner import (
    SecurityScannerAgent,
    SecurityScanResult,
    SecurityVulnerability,
)


@pytest.fixture
def security_agent():
    """Create security scanner agent."""
    return SecurityScannerAgent()


@pytest.fixture
def sample_vulnerable_code():
    """Sample code with vulnerabilities."""
    return """
import subprocess
import mysql.connector

def get_user(user_id):
    # SQL Injection vulnerability
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    return cursor.fetchone()

def execute_command(cmd):
    # Command injection vulnerability
    subprocess.run(cmd, shell=True)

def login(username, password):
    # Hardcoded credentials
    if password == "admin123":
        return True
    return False
"""


@pytest.mark.asyncio
async def test_scan_code(security_agent, sample_vulnerable_code):
    """Test security code scanning."""
    mock_result = SecurityScanResult(
        vulnerabilities=[
            SecurityVulnerability(
                severity="critical",
                category="sql_injection",
                cwe_id="CWE-89",
                description="SQL Injection vulnerability in query construction",
                location="Line 6",
                code_snippet='query = f"SELECT * FROM users WHERE id = {user_id}"',
                remediation="Use parameterized queries with placeholders",
                owasp_category="A03:2021 – Injection",
            ),
            SecurityVulnerability(
                severity="high",
                category="command_injection",
                cwe_id="CWE-78",
                description="Command injection via shell=True",
                location="Line 11",
                code_snippet="subprocess.run(cmd, shell=True)",
                remediation="Avoid shell=True, use list arguments",
                owasp_category="A03:2021 – Injection",
            ),
            SecurityVulnerability(
                severity="medium",
                category="hardcoded_credentials",
                cwe_id="CWE-798",
                description="Hardcoded password in source code",
                location="Line 15",
                code_snippet='if password == "admin123"',
                remediation="Use environment variables or secrets management",
                owasp_category="A07:2021 – Identification and Authentication Failures",
            ),
        ],
        risk_score=85.0,
        total_issues=3,
        critical_count=1,
        high_count=1,
        medium_count=1,
        low_count=0,
    )

    with patch.object(
        security_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await security_agent.execute(code=sample_vulnerable_code, language="python")

        assert isinstance(result, SecurityScanResult)
        assert result.total_issues == 3
        assert result.critical_count == 1
        assert result.risk_score == 85.0
        assert len(result.vulnerabilities) == 3


@pytest.mark.asyncio
async def test_scan_dependencies(security_agent):
    """Test dependency vulnerability scanning."""
    dependencies = """
flask==0.12.0
requests==2.6.0
django==1.11.0
"""

    mock_result = SecurityScanResult(
        vulnerabilities=[
            SecurityVulnerability(
                severity="high",
                category="vulnerable_dependency",
                cwe_id="CWE-1035",
                description="Flask 0.12.0 has known security vulnerabilities",
                location="requirements.txt:1",
                remediation="Update to Flask >= 2.3.0",
            ),
            SecurityVulnerability(
                severity="critical",
                category="vulnerable_dependency",
                cwe_id="CWE-1035",
                description="Django 1.11.0 is end-of-life with security issues",
                location="requirements.txt:3",
                remediation="Update to Django >= 4.2",
            ),
        ],
        risk_score=90.0,
        total_issues=2,
        critical_count=1,
        high_count=1,
        medium_count=0,
        low_count=0,
    )

    with patch.object(
        security_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await security_agent.scan_dependencies(dependencies=dependencies)

        assert isinstance(result, SecurityScanResult)
        assert result.critical_count >= 1
        assert any("Django" in vuln.description for vuln in result.vulnerabilities)


@pytest.mark.asyncio
async def test_scan_configuration(security_agent):
    """Test configuration security scanning."""
    config = """
DEBUG = True
SECRET_KEY = 'my-secret-key-123'
ALLOWED_HOSTS = ['*']
CORS_ORIGIN_ALLOW_ALL = True
"""

    mock_result = SecurityScanResult(
        vulnerabilities=[
            SecurityVulnerability(
                severity="high",
                category="misconfiguration",
                description="DEBUG mode enabled in production",
                location="Line 1",
                remediation="Set DEBUG = False in production",
                owasp_category="A05:2021 – Security Misconfiguration",
            ),
            SecurityVulnerability(
                severity="critical",
                category="hardcoded_credentials",
                description="Hardcoded SECRET_KEY",
                location="Line 2",
                remediation="Use environment variables",
                owasp_category="A02:2021 – Cryptographic Failures",
            ),
        ],
        risk_score=88.0,
        total_issues=2,
        critical_count=1,
        high_count=1,
        medium_count=0,
        low_count=0,
    )

    with patch.object(
        security_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await security_agent.scan_config(config=config, config_type="django")

        assert isinstance(result, SecurityScanResult)
        assert result.total_issues >= 2


@pytest.mark.asyncio
async def test_error_handling(security_agent):
    """Test error handling."""
    with patch.object(
        security_agent,
        "_generate_structured_response",
        side_effect=Exception("Scan failed"),
    ):
        result = await security_agent.execute(code="invalid", language="python")

        assert isinstance(result, SecurityScanResult)
        assert result.risk_score == 0


@pytest.mark.asyncio
async def test_owasp_categorization(security_agent, sample_vulnerable_code):
    """Test OWASP category assignment."""
    mock_result = SecurityScanResult(
        vulnerabilities=[
            SecurityVulnerability(
                severity="critical",
                category="sql_injection",
                cwe_id="CWE-89",
                description="SQL Injection",
                owasp_category="A03:2021 – Injection",
            )
        ],
        risk_score=95.0,
        total_issues=1,
        critical_count=1,
        high_count=0,
        medium_count=0,
        low_count=0,
    )

    with patch.object(
        security_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await security_agent.execute(code=sample_vulnerable_code, language="python")

        assert all(vuln.owasp_category for vuln in result.vulnerabilities)


def test_create_system_prompt(security_agent):
    """Test system prompt creation."""
    prompt = security_agent._create_system_prompt("python")

    assert "security" in prompt.lower()
    assert "owasp" in prompt.lower()
    assert "python" in prompt.lower()
