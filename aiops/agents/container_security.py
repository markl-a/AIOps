"""
Container Security Scanner Agent

Scans Docker images and containers for vulnerabilities, misconfigurations,
and security best practices violations.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class Vulnerability(BaseModel):
    """Container vulnerability"""
    cve_id: Optional[str] = Field(description="CVE identifier")
    severity: str = Field(description="critical, high, medium, low")
    package_name: str = Field(description="Affected package")
    installed_version: str = Field(description="Currently installed version")
    fixed_version: Optional[str] = Field(description="Version that fixes the vulnerability")
    description: str = Field(description="Vulnerability description")
    cvss_score: Optional[float] = Field(description="CVSS score if available")


class ContainerSecurityResult(BaseModel):
    """Container security scan result"""
    analyzed_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    image_name: str = Field(description="Docker image name")
    image_tag: str = Field(description="Image tag")
    vulnerabilities: List[Vulnerability] = Field(description="List of vulnerabilities")
    misconfigurations: List[str] = Field(description="Configuration issues")
    security_score: float = Field(description="Overall security score 0-100")
    risk_level: str = Field(description="critical, high, medium, low")
    summary: str = Field(description="Summary")
    recommendations: List[str] = Field(description="Security recommendations")


class ContainerSecurityScanner:
    """Container security scanner"""

    def __init__(self, llm_factory=None):
        self.llm_factory = llm_factory
        logger.info("Container Security Scanner initialized")

    async def scan_dockerfile(self, dockerfile_content: str, image_name: str = "app") -> ContainerSecurityResult:
        """Scan Dockerfile for security issues"""
        vulnerabilities = []
        misconfigurations = []
        recommendations = []

        # Check for running as root
        if 'USER' not in dockerfile_content:
            misconfigurations.append("Container runs as root user")
            recommendations.append("Add 'USER' instruction to run as non-root user")

        # Check for latest tag
        if ':latest' in dockerfile_content or not ':' in dockerfile_content.split('\n')[0]:
            misconfigurations.append("Using 'latest' tag or no specific version")
            recommendations.append("Pin to specific image versions for reproducibility")

        # Check for hardcoded secrets
        if any(word in dockerfile_content.lower() for word in ['password', 'api_key', 'secret', 'token']):
            misconfigurations.append("Potential hardcoded secrets in Dockerfile")
            recommendations.append("Use build arguments or secrets management instead")
            vulnerabilities.append(Vulnerability(
                cve_id=None,
                severity="critical",
                package_name="dockerfile",
                installed_version="n/a",
                fixed_version=None,
                description="Hardcoded secrets detected",
                cvss_score=9.0
            ))

        # Check for unnecessary packages
        if 'apt-get install' in dockerfile_content and '--no-install-recommends' not in dockerfile_content:
            misconfigurations.append("Installing recommended packages unnecessarily")
            recommendations.append("Use --no-install-recommends to reduce attack surface")

        # Check for cache cleanup
        if 'apt-get install' in dockerfile_content and 'apt-get clean' not in dockerfile_content:
            misconfigurations.append("Not cleaning package manager cache")
            recommendations.append("Add 'apt-get clean' to reduce image size")

        # Check for HEALTHCHECK
        if 'HEALTHCHECK' not in dockerfile_content:
            misconfigurations.append("Missing HEALTHCHECK instruction")
            recommendations.append("Add HEALTHCHECK for better container monitoring")

        # Check for exposed ports
        if 'EXPOSE' not in dockerfile_content:
            misconfigurations.append("No ports explicitly exposed")
            recommendations.append("Use EXPOSE to document which ports the container listens on")

        # Simulate vulnerability scan (in real implementation, integrate with Trivy/Snyk)
        if 'FROM ubuntu' in dockerfile_content or 'FROM debian' in dockerfile_content:
            vulnerabilities.append(Vulnerability(
                cve_id="CVE-2024-XXXX",
                severity="high",
                package_name="openssl",
                installed_version="1.1.1",
                fixed_version="1.1.1w",
                description="OpenSSL vulnerability - Update recommended",
                cvss_score=7.5
            ))

        # Calculate security score
        security_score = self._calculate_security_score(vulnerabilities, misconfigurations)
        risk_level = self._determine_risk_level(vulnerabilities)

        summary = f"Scanned {image_name}: {len(vulnerabilities)} vulnerabilities, {len(misconfigurations)} misconfigurations. Score: {security_score:.0f}/100"

        return ContainerSecurityResult(
            image_name=image_name,
            image_tag="latest",
            vulnerabilities=vulnerabilities,
            misconfigurations=misconfigurations,
            security_score=security_score,
            risk_level=risk_level,
            summary=summary,
            recommendations=recommendations
        )

    def _calculate_security_score(self, vulns: List[Vulnerability], misconfigs: List[str]) -> float:
        score = 100.0
        for vuln in vulns:
            if vuln.severity == "critical":
                score -= 25
            elif vuln.severity == "high":
                score -= 15
            elif vuln.severity == "medium":
                score -= 8
        score -= len(misconfigs) * 5
        return max(0.0, score)

    def _determine_risk_level(self, vulns: List[Vulnerability]) -> str:
        critical = sum(1 for v in vulns if v.severity == "critical")
        high = sum(1 for v in vulns if v.severity == "high")

        if critical > 0:
            return "critical"
        elif high > 2:
            return "high"
        elif high > 0:
            return "medium"
        return "low"
