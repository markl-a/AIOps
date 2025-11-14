"""Security Scanner Agent - Automated security vulnerability detection."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from aiops.agents.base_agent import BaseAgent
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class SecurityVulnerability(BaseModel):
    """Represents a security vulnerability."""

    severity: str = Field(description="Severity: critical, high, medium, low")
    category: str = Field(description="OWASP category or vulnerability type")
    cwe_id: Optional[str] = Field(default=None, description="CWE ID if applicable")
    title: str = Field(description="Vulnerability title")
    description: str = Field(description="Detailed description")
    affected_code: Optional[str] = Field(default=None, description="Affected code snippet")
    line_number: Optional[int] = Field(default=None, description="Line number")
    attack_scenario: str = Field(description="How this could be exploited")
    remediation: str = Field(description="How to fix this vulnerability")
    references: List[str] = Field(description="Reference links")


class DependencyVulnerability(BaseModel):
    """Represents a dependency vulnerability."""

    package_name: str = Field(description="Package name")
    current_version: str = Field(description="Current version")
    vulnerable_versions: str = Field(description="Vulnerable version range")
    fixed_version: str = Field(description="Version that fixes the issue")
    severity: str = Field(description="Severity level")
    cve_id: Optional[str] = Field(default=None, description="CVE ID")
    description: str = Field(description="Vulnerability description")


class SecurityScanResult(BaseModel):
    """Result of security scan."""

    security_score: float = Field(description="Overall security score (0-100)")
    summary: str = Field(description="Executive summary")
    code_vulnerabilities: List[SecurityVulnerability] = Field(description="Code vulnerabilities")
    dependency_vulnerabilities: List[DependencyVulnerability] = Field(description="Dependency vulnerabilities")
    security_best_practices: List[str] = Field(description="Security best practices to implement")
    compliance_notes: Dict[str, str] = Field(description="Compliance notes (OWASP, PCI-DSS, etc.)")


class SecurityScannerAgent(BaseAgent):
    """Agent for security vulnerability scanning."""

    def __init__(self, **kwargs):
        super().__init__(name="SecurityScannerAgent", **kwargs)

    async def execute(
        self,
        code: str,
        language: str = "python",
        dependencies: Optional[str] = None,
        context: Optional[str] = None,
    ) -> SecurityScanResult:
        """
        Scan code and dependencies for security vulnerabilities.

        Args:
            code: Code to scan
            language: Programming language
            dependencies: Dependency file content (requirements.txt, package.json, etc.)
            context: Additional context

        Returns:
            SecurityScanResult with vulnerabilities and recommendations
        """
        logger.info(f"Starting security scan for {language} code")

        system_prompt = self._create_system_prompt(language)
        user_prompt = self._create_user_prompt(code, dependencies, context)

        try:
            result = await self._generate_structured_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                schema=SecurityScanResult,
            )

            logger.info(
                f"Security scan completed: score {result.security_score}/100, "
                f"{len(result.code_vulnerabilities)} code vulns, "
                f"{len(result.dependency_vulnerabilities)} dependency vulns"
            )

            return result

        except Exception as e:
            logger.error(f"Security scan failed: {e}")
            return SecurityScanResult(
                security_score=0,
                summary=f"Scan failed: {str(e)}",
                code_vulnerabilities=[],
                dependency_vulnerabilities=[],
                security_best_practices=[],
                compliance_notes={},
            )

    def _create_system_prompt(self, language: str) -> str:
        """Create system prompt for security scanning."""
        return f"""You are an expert security researcher and penetration tester specializing in {language}.

Your task is to identify security vulnerabilities following OWASP Top 10 and industry best practices.

Focus Areas:

1. **Injection Attacks**:
   - SQL Injection
   - Command Injection
   - LDAP Injection
   - XPath Injection

2. **Broken Authentication**:
   - Weak password requirements
   - Session management issues
   - Missing MFA

3. **Sensitive Data Exposure**:
   - Hardcoded credentials
   - Secrets in code
   - Inadequate encryption

4. **XML External Entities (XXE)**:
   - XML parsing vulnerabilities
   - External entity attacks

5. **Broken Access Control**:
   - Missing authorization checks
   - Insecure direct object references

6. **Security Misconfiguration**:
   - Debug mode in production
   - Default credentials
   - Unnecessary features enabled

7. **Cross-Site Scripting (XSS)**:
   - Stored XSS
   - Reflected XSS
   - DOM-based XSS

8. **Insecure Deserialization**:
   - Unsafe object deserialization
   - Remote code execution risks

9. **Using Components with Known Vulnerabilities**:
   - Outdated dependencies
   - Known CVEs

10. **Insufficient Logging & Monitoring**:
    - Missing security logs
    - No anomaly detection

For each vulnerability:
- Provide severity (critical/high/medium/low)
- Map to OWASP category and CWE if applicable
- Explain attack scenario
- Provide specific remediation steps
- Include references

Be thorough but practical. Focus on real, exploitable vulnerabilities.
"""

    def _create_user_prompt(
        self,
        code: str,
        dependencies: Optional[str] = None,
        context: Optional[str] = None,
    ) -> str:
        """Create user prompt for security scanning."""
        prompt = "Perform comprehensive security analysis:\n\n"

        if context:
            prompt += f"**Context**: {context}\n\n"

        prompt += f"**Code to Scan**:\n```\n{code}\n```\n\n"

        if dependencies:
            prompt += f"**Dependencies**:\n```\n{dependencies}\n```\n\n"

        prompt += """Analyze for:
1. Code vulnerabilities (injection, XSS, auth issues, etc.)
2. Dependency vulnerabilities (if dependencies provided)
3. Security best practices violations
4. Compliance considerations

Provide specific, actionable findings with remediation steps.
"""

        return prompt

    async def scan_dependencies(
        self,
        dependencies: str,
        dependency_type: str = "python",
    ) -> List[DependencyVulnerability]:
        """
        Scan dependencies for known vulnerabilities.

        Args:
            dependencies: Dependency file content
            dependency_type: Type (python, node, java, etc.)

        Returns:
            List of dependency vulnerabilities
        """
        logger.info(f"Scanning {dependency_type} dependencies")

        system_prompt = f"""You are a security expert specializing in dependency vulnerabilities.

Analyze {dependency_type} dependencies for:
- Known CVEs
- Outdated packages
- Vulnerable version ranges
- Available security patches

Check against CVE databases and security advisories.
Provide specific version recommendations.
"""

        user_prompt = f"""Scan these dependencies for vulnerabilities:

```
{dependencies}
```

Identify:
1. Packages with known CVEs
2. Outdated packages with security fixes available
3. Recommended version upgrades
4. Security impact
"""

        try:
            # In a real implementation, this would integrate with vulnerability databases
            result = await self._generate_structured_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                schema={"type": "array", "items": DependencyVulnerability.model_json_schema()},
            )

            vulns = [DependencyVulnerability(**v) for v in result]
            logger.info(f"Found {len(vulns)} dependency vulnerabilities")
            return vulns

        except Exception as e:
            logger.error(f"Dependency scan failed: {e}")
            return []

    async def check_secrets(
        self,
        code: str,
        file_paths: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Scan for hardcoded secrets and credentials.

        Args:
            code: Code to scan
            file_paths: Optional file paths for context

        Returns:
            List of detected secrets
        """
        logger.info("Scanning for hardcoded secrets")

        system_prompt = """You are a security expert specializing in secret detection.

Identify hardcoded secrets:
- API keys
- Passwords
- Private keys
- Connection strings
- OAuth tokens
- AWS/Cloud credentials
- Database credentials

Look for patterns indicating secrets even if partially obfuscated.
"""

        user_prompt = f"""Scan for hardcoded secrets:

```
{code}
```

Identify any sensitive information that should not be in code.
Provide location and type of secret found.
"""

        try:
            response = await self._generate_response(user_prompt, system_prompt)

            # Parse response for secrets
            # In production, use regex patterns and entropy analysis
            secrets = []

            if "api" in response.lower() or "key" in response.lower():
                secrets.append({
                    "type": "potential_secret",
                    "description": "Potential secrets detected",
                    "recommendation": "Review code for hardcoded credentials",
                })

            logger.info(f"Secret scan completed: {len(secrets)} potential secrets")
            return secrets

        except Exception as e:
            logger.error(f"Secret scan failed: {e}")
            return []

    async def generate_security_report(
        self,
        scan_result: SecurityScanResult,
        format: str = "markdown",
    ) -> str:
        """
        Generate formatted security report.

        Args:
            scan_result: Scan results
            format: Report format (markdown, html, json)

        Returns:
            Formatted report
        """
        logger.info(f"Generating {format} security report")

        if format == "markdown":
            report = f"""# Security Scan Report

## Summary
{scan_result.summary}

**Security Score**: {scan_result.security_score}/100

## Code Vulnerabilities
Found {len(scan_result.code_vulnerabilities)} vulnerabilities:

"""
            for i, vuln in enumerate(scan_result.code_vulnerabilities, 1):
                report += f"""
### {i}. [{vuln.severity.upper()}] {vuln.title}

**Category**: {vuln.category}
{f"**CWE**: {vuln.cwe_id}" if vuln.cwe_id else ""}

**Description**: {vuln.description}

**Attack Scenario**: {vuln.attack_scenario}

**Remediation**: {vuln.remediation}

"""

            if scan_result.dependency_vulnerabilities:
                report += f"""
## Dependency Vulnerabilities
Found {len(scan_result.dependency_vulnerabilities)} vulnerable dependencies:

"""
                for dep in scan_result.dependency_vulnerabilities:
                    report += f"""
- **{dep.package_name}** {dep.current_version}
  - Severity: {dep.severity}
  - Fixed in: {dep.fixed_version}
  - {dep.description}

"""

            if scan_result.security_best_practices:
                report += "\n## Security Best Practices\n\n"
                for practice in scan_result.security_best_practices:
                    report += f"- {practice}\n"

            return report

        else:
            return f"Format {format} not yet implemented"
