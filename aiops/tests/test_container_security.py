"""
Unit tests for Container Security Scanner Agent
"""

import pytest
from aiops.agents.container_security import (
    ContainerSecurityScanner,
    Vulnerability,
    ContainerSecurityResult
)


class TestVulnerability:
    """Tests for Vulnerability model"""

    def test_create_vulnerability(self):
        """Test creating a vulnerability"""
        vuln = Vulnerability(
            cve_id="CVE-2024-1234",
            severity="high",
            package_name="openssl",
            installed_version="1.1.1k",
            fixed_version="1.1.1l",
            description="Buffer overflow vulnerability",
            cvss_score=8.5
        )
        assert vuln.cve_id == "CVE-2024-1234"
        assert vuln.severity == "high"
        assert vuln.cvss_score == 8.5

    def test_vulnerability_severities(self):
        """Test different severity levels"""
        for severity in ["critical", "high", "medium", "low"]:
            vuln = Vulnerability(
                cve_id="CVE-2024-0001",
                severity=severity,
                package_name="test",
                installed_version="1.0",
                fixed_version="1.1",
                description="Test",
                cvss_score=5.0
            )
            assert vuln.severity == severity

    def test_vulnerability_without_cve(self):
        """Test vulnerability without CVE ID"""
        vuln = Vulnerability(
            cve_id=None,
            severity="medium",
            package_name="custom-pkg",
            installed_version="1.0",
            fixed_version=None,
            description="Custom vulnerability",
            cvss_score=None
        )
        assert vuln.cve_id is None
        assert vuln.fixed_version is None
        assert vuln.cvss_score is None

    def test_vulnerability_without_fix(self):
        """Test vulnerability with no available fix"""
        vuln = Vulnerability(
            cve_id="CVE-2024-9999",
            severity="critical",
            package_name="legacy-lib",
            installed_version="0.5",
            fixed_version=None,
            description="No fix available",
            cvss_score=9.8
        )
        assert vuln.fixed_version is None


class TestContainerSecurityResult:
    """Tests for ContainerSecurityResult model"""

    def test_create_result(self):
        """Test creating security result"""
        result = ContainerSecurityResult(
            image_name="myapp",
            image_tag="v1.0.0",
            vulnerabilities=[],
            misconfigurations=[],
            security_score=100.0,
            risk_level="low",
            summary="No issues found",
            recommendations=[]
        )
        assert result.image_name == "myapp"
        assert result.security_score == 100.0
        assert result.risk_level == "low"

    def test_result_with_vulnerabilities(self):
        """Test result with vulnerabilities"""
        vulns = [
            Vulnerability(
                cve_id="CVE-2024-1",
                severity="critical",
                package_name="pkg1",
                installed_version="1.0",
                fixed_version="1.1",
                description="Critical vuln",
                cvss_score=9.5
            ),
            Vulnerability(
                cve_id="CVE-2024-2",
                severity="high",
                package_name="pkg2",
                installed_version="2.0",
                fixed_version="2.1",
                description="High vuln",
                cvss_score=7.5
            )
        ]
        result = ContainerSecurityResult(
            image_name="app",
            image_tag="latest",
            vulnerabilities=vulns,
            misconfigurations=["Running as root"],
            security_score=40.0,
            risk_level="critical",
            summary="Multiple vulnerabilities found",
            recommendations=["Update packages", "Don't run as root"]
        )
        assert len(result.vulnerabilities) == 2
        assert len(result.misconfigurations) == 1
        assert result.risk_level == "critical"

    def test_risk_levels(self):
        """Test different risk levels"""
        for risk_level in ["critical", "high", "medium", "low"]:
            result = ContainerSecurityResult(
                image_name="test",
                image_tag="test",
                vulnerabilities=[],
                misconfigurations=[],
                security_score=50.0,
                risk_level=risk_level,
                summary="Test",
                recommendations=[]
            )
            assert result.risk_level == risk_level


class TestContainerSecurityScanner:
    """Tests for ContainerSecurityScanner"""

    @pytest.fixture
    def scanner(self):
        """Create scanner instance"""
        return ContainerSecurityScanner()

    @pytest.mark.asyncio
    async def test_scan_clean_dockerfile(self, scanner):
        """Test scanning a well-configured Dockerfile"""
        dockerfile = """
FROM ubuntu:22.04

RUN apt-get update && \\
    apt-get install -y --no-install-recommends python3 && \\
    apt-get clean && \\
    rm -rf /var/lib/apt/lists/*

EXPOSE 8080

USER appuser

HEALTHCHECK --interval=30s CMD curl -f http://localhost:8080/health || exit 1

CMD ["python3", "app.py"]
"""
        result = await scanner.scan_dockerfile(dockerfile, "clean-app")

        assert result.image_name == "clean-app"
        # Should have fewer misconfigurations
        # May still have vulnerability from base image
        assert "runs as root" not in " ".join(result.misconfigurations).lower()

    @pytest.mark.asyncio
    async def test_detect_root_user(self, scanner):
        """Test detecting container running as root"""
        dockerfile = """
FROM ubuntu:22.04
RUN apt-get update
CMD ["./app"]
"""
        result = await scanner.scan_dockerfile(dockerfile)

        misconfigs = " ".join(result.misconfigurations).lower()
        assert "root" in misconfigs
        assert any("non-root" in r.lower() or "user" in r.lower() for r in result.recommendations)

    @pytest.mark.asyncio
    async def test_detect_latest_tag(self, scanner):
        """Test detecting use of latest tag"""
        dockerfile = """
FROM python:latest
CMD ["python", "app.py"]
"""
        result = await scanner.scan_dockerfile(dockerfile)

        misconfigs = " ".join(result.misconfigurations).lower()
        assert "latest" in misconfigs or "version" in misconfigs

    @pytest.mark.asyncio
    async def test_detect_hardcoded_secrets(self, scanner):
        """Test detecting hardcoded secrets"""
        dockerfile = """
FROM ubuntu:22.04
ENV API_KEY=my_secret_api_key
ENV PASSWORD=supersecret123
CMD ["./app"]
"""
        result = await scanner.scan_dockerfile(dockerfile)

        misconfigs = " ".join(result.misconfigurations).lower()
        assert "secret" in misconfigs or "password" in misconfigs.lower()
        assert len([v for v in result.vulnerabilities if v.severity == "critical"]) > 0

    @pytest.mark.asyncio
    async def test_detect_no_install_recommends(self, scanner):
        """Test detecting missing --no-install-recommends"""
        dockerfile = """
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y python3
CMD ["python3", "app.py"]
"""
        result = await scanner.scan_dockerfile(dockerfile)

        misconfigs = " ".join(result.misconfigurations).lower()
        assert "recommend" in misconfigs

    @pytest.mark.asyncio
    async def test_detect_missing_apt_clean(self, scanner):
        """Test detecting missing apt-get clean"""
        dockerfile = """
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y --no-install-recommends python3
CMD ["python3"]
"""
        result = await scanner.scan_dockerfile(dockerfile)

        misconfigs = " ".join(result.misconfigurations).lower()
        assert "clean" in misconfigs or "cache" in misconfigs

    @pytest.mark.asyncio
    async def test_detect_missing_healthcheck(self, scanner):
        """Test detecting missing HEALTHCHECK"""
        dockerfile = """
FROM ubuntu:22.04
USER appuser
EXPOSE 8080
CMD ["./app"]
"""
        result = await scanner.scan_dockerfile(dockerfile)

        misconfigs = " ".join(result.misconfigurations).lower()
        assert "healthcheck" in misconfigs

    @pytest.mark.asyncio
    async def test_detect_missing_expose(self, scanner):
        """Test detecting missing EXPOSE"""
        dockerfile = """
FROM ubuntu:22.04
USER appuser
HEALTHCHECK CMD curl localhost
CMD ["./app"]
"""
        result = await scanner.scan_dockerfile(dockerfile)

        misconfigs = " ".join(result.misconfigurations).lower()
        assert "expose" in misconfigs or "port" in misconfigs

    @pytest.mark.asyncio
    async def test_detect_base_image_vulnerabilities(self, scanner):
        """Test detecting vulnerabilities in base image"""
        dockerfile = """
FROM ubuntu:22.04
CMD ["./app"]
"""
        result = await scanner.scan_dockerfile(dockerfile)

        # Should detect simulated OpenSSL vulnerability
        openssl_vulns = [v for v in result.vulnerabilities if "openssl" in v.package_name.lower()]
        assert len(openssl_vulns) > 0

    @pytest.mark.asyncio
    async def test_debian_base_vulnerability(self, scanner):
        """Test vulnerability detection for Debian base"""
        dockerfile = """
FROM debian:bullseye
CMD ["./app"]
"""
        result = await scanner.scan_dockerfile(dockerfile)

        assert len(result.vulnerabilities) > 0

    def test_calculate_security_score_no_issues(self, scanner):
        """Test security score with no issues"""
        score = scanner._calculate_security_score([], [])
        assert score == 100.0

    def test_calculate_security_score_critical_vuln(self, scanner):
        """Test security score with critical vulnerability"""
        vulns = [
            Vulnerability(
                cve_id="CVE-1",
                severity="critical",
                package_name="pkg",
                installed_version="1.0",
                fixed_version="1.1",
                description="Critical",
                cvss_score=9.5
            )
        ]
        score = scanner._calculate_security_score(vulns, [])
        assert score == 75.0  # 100 - 25

    def test_calculate_security_score_high_vuln(self, scanner):
        """Test security score with high vulnerability"""
        vulns = [
            Vulnerability(
                cve_id="CVE-1",
                severity="high",
                package_name="pkg",
                installed_version="1.0",
                fixed_version="1.1",
                description="High",
                cvss_score=7.5
            )
        ]
        score = scanner._calculate_security_score(vulns, [])
        assert score == 85.0  # 100 - 15

    def test_calculate_security_score_medium_vuln(self, scanner):
        """Test security score with medium vulnerability"""
        vulns = [
            Vulnerability(
                cve_id="CVE-1",
                severity="medium",
                package_name="pkg",
                installed_version="1.0",
                fixed_version="1.1",
                description="Medium",
                cvss_score=5.0
            )
        ]
        score = scanner._calculate_security_score(vulns, [])
        assert score == 92.0  # 100 - 8

    def test_calculate_security_score_with_misconfigs(self, scanner):
        """Test security score with misconfigurations"""
        misconfigs = ["Running as root", "No healthcheck", "Using latest tag"]
        score = scanner._calculate_security_score([], misconfigs)
        assert score == 85.0  # 100 - (3 * 5)

    def test_calculate_security_score_combined(self, scanner):
        """Test security score with both vulns and misconfigs"""
        vulns = [
            Vulnerability(
                cve_id="CVE-1",
                severity="high",
                package_name="pkg",
                installed_version="1.0",
                fixed_version="1.1",
                description="High",
                cvss_score=7.5
            )
        ]
        misconfigs = ["Running as root"]
        score = scanner._calculate_security_score(vulns, misconfigs)
        assert score == 80.0  # 100 - 15 - 5

    def test_calculate_security_score_minimum_zero(self, scanner):
        """Test security score doesn't go below 0"""
        vulns = [
            Vulnerability(
                cve_id=f"CVE-{i}",
                severity="critical",
                package_name=f"pkg{i}",
                installed_version="1.0",
                fixed_version="1.1",
                description="Critical",
                cvss_score=9.8
            )
            for i in range(10)  # 10 critical = -250, would be -150
        ]
        score = scanner._calculate_security_score(vulns, [])
        assert score == 0.0

    def test_determine_risk_level_critical(self, scanner):
        """Test risk level with critical vulnerability"""
        vulns = [
            Vulnerability(
                cve_id="CVE-1",
                severity="critical",
                package_name="pkg",
                installed_version="1.0",
                fixed_version="1.1",
                description="Critical",
                cvss_score=9.5
            )
        ]
        risk = scanner._determine_risk_level(vulns)
        assert risk == "critical"

    def test_determine_risk_level_high_multiple(self, scanner):
        """Test risk level with multiple high vulnerabilities"""
        vulns = [
            Vulnerability(
                cve_id=f"CVE-{i}",
                severity="high",
                package_name=f"pkg{i}",
                installed_version="1.0",
                fixed_version="1.1",
                description="High",
                cvss_score=7.5
            )
            for i in range(3)
        ]
        risk = scanner._determine_risk_level(vulns)
        assert risk == "high"

    def test_determine_risk_level_high_single(self, scanner):
        """Test risk level with single high vulnerability"""
        vulns = [
            Vulnerability(
                cve_id="CVE-1",
                severity="high",
                package_name="pkg",
                installed_version="1.0",
                fixed_version="1.1",
                description="High",
                cvss_score=7.5
            )
        ]
        risk = scanner._determine_risk_level(vulns)
        assert risk == "medium"

    def test_determine_risk_level_low(self, scanner):
        """Test risk level with no high severity"""
        vulns = [
            Vulnerability(
                cve_id="CVE-1",
                severity="medium",
                package_name="pkg",
                installed_version="1.0",
                fixed_version="1.1",
                description="Medium",
                cvss_score=5.0
            )
        ]
        risk = scanner._determine_risk_level(vulns)
        assert risk == "low"

    def test_determine_risk_level_no_vulns(self, scanner):
        """Test risk level with no vulnerabilities"""
        risk = scanner._determine_risk_level([])
        assert risk == "low"

    def test_scanner_initialization(self):
        """Test scanner initialization"""
        scanner = ContainerSecurityScanner()
        assert scanner.llm_factory is None

    def test_scanner_with_llm_factory(self):
        """Test scanner initialization with LLM factory"""
        mock_factory = object()
        scanner = ContainerSecurityScanner(llm_factory=mock_factory)
        assert scanner.llm_factory is mock_factory


class TestContainerSecurityEdgeCases:
    """Edge case tests"""

    @pytest.fixture
    def scanner(self):
        return ContainerSecurityScanner()

    @pytest.mark.asyncio
    async def test_empty_dockerfile(self, scanner):
        """Test with empty Dockerfile"""
        result = await scanner.scan_dockerfile("")

        assert result is not None
        # Empty dockerfile should have misconfigurations
        assert len(result.misconfigurations) > 0

    @pytest.mark.asyncio
    async def test_minimal_dockerfile(self, scanner):
        """Test with minimal Dockerfile"""
        dockerfile = "FROM scratch"
        result = await scanner.scan_dockerfile(dockerfile)

        assert result is not None

    @pytest.mark.asyncio
    async def test_complex_dockerfile(self, scanner):
        """Test with complex multi-stage Dockerfile"""
        dockerfile = """
# Build stage
FROM golang:1.21 AS builder
WORKDIR /app
COPY . .
RUN go build -o app

# Production stage
FROM alpine:3.18
RUN apk add --no-cache ca-certificates
COPY --from=builder /app/app /app
USER nobody
EXPOSE 8080
HEALTHCHECK --interval=30s CMD wget -q --spider http://localhost:8080/health
CMD ["/app"]
"""
        result = await scanner.scan_dockerfile(dockerfile, "multi-stage-app")

        assert result.image_name == "multi-stage-app"
        # Should recognize USER instruction
        assert "root" not in " ".join(result.misconfigurations).lower()

    @pytest.mark.asyncio
    async def test_custom_image_name(self, scanner):
        """Test with custom image name"""
        dockerfile = "FROM ubuntu:22.04\nCMD ['./app']"
        result = await scanner.scan_dockerfile(dockerfile, "custom-name:v1.2.3")

        assert "custom-name" in result.image_name

    @pytest.mark.asyncio
    async def test_summary_format(self, scanner):
        """Test summary contains expected information"""
        dockerfile = """
FROM ubuntu:22.04
RUN apt-get update
CMD ["./app"]
"""
        result = await scanner.scan_dockerfile(dockerfile, "test-app")

        assert "test-app" in result.summary
        assert "vulnerabilities" in result.summary.lower() or str(len(result.vulnerabilities)) in result.summary
        assert "misconfig" in result.summary.lower() or str(len(result.misconfigurations)) in result.summary

    @pytest.mark.asyncio
    async def test_recommendations_provided(self, scanner):
        """Test that recommendations are provided for issues"""
        dockerfile = """
FROM ubuntu:latest
RUN apt-get install -y python3
ENV SECRET_KEY=mysecret
CMD ["python3", "app.py"]
"""
        result = await scanner.scan_dockerfile(dockerfile)

        # Should have recommendations for each issue
        assert len(result.recommendations) > 0
        # Each misconfiguration should have a recommendation
        recs_lower = " ".join(result.recommendations).lower()
        assert "user" in recs_lower or "version" in recs_lower or "secret" in recs_lower

    @pytest.mark.asyncio
    async def test_case_insensitive_detection(self, scanner):
        """Test that secret detection is case insensitive"""
        dockerfile = """
FROM ubuntu:22.04
ENV PASSWORD=test
ENV password=test
ENV Password=test
CMD ["./app"]
"""
        result = await scanner.scan_dockerfile(dockerfile)

        misconfigs = " ".join(result.misconfigurations).lower()
        assert "secret" in misconfigs

    @pytest.mark.asyncio
    async def test_token_detection(self, scanner):
        """Test detection of token in environment"""
        dockerfile = """
FROM ubuntu:22.04
ENV AUTH_TOKEN=abc123
CMD ["./app"]
"""
        result = await scanner.scan_dockerfile(dockerfile)

        misconfigs = " ".join(result.misconfigurations).lower()
        assert "secret" in misconfigs

    @pytest.mark.asyncio
    async def test_api_key_detection(self, scanner):
        """Test detection of api_key in environment"""
        dockerfile = """
FROM ubuntu:22.04
ENV API_KEY=xyz789
CMD ["./app"]
"""
        result = await scanner.scan_dockerfile(dockerfile)

        misconfigs = " ".join(result.misconfigurations).lower()
        assert "secret" in misconfigs
