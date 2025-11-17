"""
Secret Scanner Agent

Scans code repositories, configuration files, and docker images for
hardcoded secrets, API keys, passwords, and sensitive data.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from aiops.core.logger import get_logger
import re

logger = get_logger(__name__)


class SecretMatch(BaseModel):
    """Detected secret"""
    secret_type: str = Field(description="Type of secret (api_key, password, token, etc.)")
    file_path: str = Field(description="File where secret was found")
    line_number: int = Field(description="Line number")
    matched_string: str = Field(description="Matched content (partially masked)")
    pattern_matched: str = Field(description="Pattern that detected this")
    severity: str = Field(description="critical, high, medium, low")
    confidence: float = Field(description="Confidence level 0-100")
    recommendation: str = Field(description="How to remediate")


class SecretScanResult(BaseModel):
    """Secret scan result"""
    scanned_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    repository_path: str = Field(description="Path to repository")
    files_scanned: int = Field(description="Number of files scanned")
    secrets_found: int = Field(description="Number of secrets found")
    secrets: List[SecretMatch] = Field(description="Detected secrets")
    risk_score: float = Field(description="Overall risk score 0-100")
    summary: str = Field(description="Summary")
    recommendations: List[str] = Field(description="Security recommendations")


class SecretScanner:
    """Secret scanner agent"""

    # Secret patterns
    PATTERNS = {
        'aws_access_key': (r'AKIA[0-9A-Z]{16}', 'critical', 'AWS Access Key ID'),
        'aws_secret_key': (r'aws[_\-]?secret[_\-]?key[\s:=]+["\']?([a-zA-Z0-9/+=]{40})["\']?', 'critical', 'AWS Secret Key'),
        'github_token': (r'ghp_[a-zA-Z0-9]{36}', 'critical', 'GitHub Personal Access Token'),
        'github_oauth': (r'gho_[a-zA-Z0-9]{36}', 'critical', 'GitHub OAuth Token'),
        'slack_token': (r'xox[baprs]-[0-9]{10,12}-[0-9]{10,12}-[a-zA-Z0-9]{24,32}', 'critical', 'Slack Token'),
        'slack_webhook': (r'https://hooks\.slack\.com/services/T[a-zA-Z0-9_]+/B[a-zA-Z0-9_]+/[a-zA-Z0-9_]+', 'high', 'Slack Webhook'),
        'google_api_key': (r'AIza[0-9A-Za-z\\-_]{35}', 'critical', 'Google API Key'),
        'stripe_key': (r'sk_live_[0-9a-zA-Z]{24,}', 'critical', 'Stripe Secret Key'),
        'private_key': (r'-----BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY-----', 'critical', 'Private Key'),
        'generic_api_key': (r'api[_\-]?key[\s:=]+["\']?([a-zA-Z0-9\-_]{20,})["\']?', 'high', 'Generic API Key'),
        'password': (r'password[\s:=]+["\']([^"\']{8,})["\']', 'medium', 'Hardcoded Password'),
        'jwt_token': (r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*', 'high', 'JWT Token'),
        'database_url': (r'(postgres|mysql|mongodb):\/\/[^:]+:[^@]+@', 'high', 'Database URL with Credentials'),
    }

    def __init__(self, llm_factory=None):
        self.llm_factory = llm_factory
        logger.info("Secret Scanner initialized")

    async def scan_code(
        self,
        code_content: str,
        file_path: str = "unknown"
    ) -> SecretScanResult:
        """Scan code for hardcoded secrets"""
        secrets = []

        lines = code_content.split('\n')

        for line_num, line in enumerate(lines, 1):
            # Skip comments (simple heuristic)
            if line.strip().startswith('#') or line.strip().startswith('//'):
                continue

            # Check each pattern
            for secret_type, (pattern, severity, description) in self.PATTERNS.items():
                matches = re.finditer(pattern, line, re.IGNORECASE)

                for match in matches:
                    matched_text = match.group(0)

                    # Mask the secret
                    if len(matched_text) > 10:
                        masked = matched_text[:4] + '*' * (len(matched_text) - 8) + matched_text[-4:]
                    else:
                        masked = '*' * len(matched_text)

                    # Calculate confidence
                    confidence = self._calculate_confidence(secret_type, matched_text, line)

                    # Skip likely false positives
                    if confidence < 50:
                        continue

                    secrets.append(SecretMatch(
                        secret_type=description,
                        file_path=file_path,
                        line_number=line_num,
                        matched_string=masked,
                        pattern_matched=secret_type,
                        severity=severity,
                        confidence=confidence,
                        recommendation=self._get_recommendation(secret_type)
                    ))

        # Calculate risk score
        risk_score = self._calculate_risk_score(secrets)

        # Generate recommendations
        recommendations = self._generate_recommendations(secrets)

        # Generate summary
        summary = self._generate_summary(file_path, len(secrets), risk_score)

        return SecretScanResult(
            repository_path=file_path,
            files_scanned=1,
            secrets_found=len(secrets),
            secrets=secrets,
            risk_score=risk_score,
            summary=summary,
            recommendations=recommendations
        )

    def _calculate_confidence(self, secret_type: str, matched_text: str, line: str) -> float:
        """Calculate confidence that this is a real secret"""
        confidence = 80.0

        # Reduce confidence for common false positives
        false_positive_indicators = [
            'example', 'sample', 'test', 'demo', 'placeholder',
            'your_key_here', 'your_token', 'xxx', '123456', 'dummy'
        ]

        line_lower = line.lower()
        matched_lower = matched_text.lower()

        for indicator in false_positive_indicators:
            if indicator in line_lower or indicator in matched_lower:
                confidence -= 30

        # Increase confidence for specific patterns
        if secret_type == 'aws_access_key' and matched_text.startswith('AKIA'):
            confidence += 15

        if 'production' in line_lower or 'prod' in line_lower:
            confidence += 10

        return max(0, min(100, confidence))

    def _get_recommendation(self, secret_type: str) -> str:
        """Get remediation recommendation"""
        recommendations = {
            'aws_access_key': 'Use AWS IAM roles and instance profiles. Store keys in AWS Secrets Manager.',
            'github_token': 'Revoke this token immediately. Use GitHub Apps or OIDC for authentication.',
            'slack_token': 'Rotate this token. Use environment variables or secret management.',
            'google_api_key': 'Use service accounts and workload identity. Store in Secret Manager.',
            'stripe_key': 'URGENT: Rotate immediately. Use environment variables.',
            'private_key': 'Remove from code. Use secret management system and SSH agent.',
            'generic_api_key': 'Store in environment variables or secret management system.',
            'password': 'Never hardcode passwords. Use secret management or OAuth.',
            'jwt_token': 'Do not commit tokens. These should be generated at runtime.',
            'database_url': 'Use environment variables. Never commit credentials.',
        }

        for key, rec in recommendations.items():
            if key in secret_type.lower():
                return rec

        return 'Move to environment variables or secret management system (e.g., HashiCorp Vault, AWS Secrets Manager)'

    def _calculate_risk_score(self, secrets: List[SecretMatch]) -> float:
        """Calculate overall risk score"""
        if not secrets:
            return 0.0

        severity_weights = {
            'critical': 40,
            'high': 25,
            'medium': 15,
            'low': 5
        }

        total_risk = sum(severity_weights.get(s.severity, 10) for s in secrets)
        return min(100.0, total_risk)

    def _generate_recommendations(self, secrets: List[SecretMatch]) -> List[str]:
        """Generate security recommendations"""
        recommendations = []

        if secrets:
            critical_count = sum(1 for s in secrets if s.severity == 'critical')

            if critical_count > 0:
                recommendations.append(f"🚨 CRITICAL: Found {critical_count} critical secrets - rotate immediately!")

            recommendations.extend([
                "Implement pre-commit hooks to prevent secret commits (e.g., git-secrets, gitleaks)",
                "Use environment variables for all secrets and credentials",
                "Implement secret management system (HashiCorp Vault, AWS Secrets Manager)",
                "Add .env to .gitignore and use .env.example for templates",
                "Conduct security awareness training for developers",
                "Enable GitHub secret scanning for your repository"
            ])

            # Check if AWS keys found
            if any('aws' in s.secret_type.lower() for s in secrets):
                recommendations.append("Rotate AWS access keys and enable MFA")

            # Check if private keys found
            if any('private key' in s.secret_type.lower() for s in secrets):
                recommendations.append("Regenerate compromised private keys")

        return recommendations[:6]

    def _generate_summary(self, file_path: str, secrets_count: int, risk: float) -> str:
        """Generate summary"""
        summary = f"Secret Scan: {file_path}\n\n"

        if secrets_count == 0:
            summary += "✓ No secrets detected\n"
            summary += "Risk Score: 0/100"
        else:
            summary += f"⚠️  Found {secrets_count} potential secrets\n"
            summary += f"Risk Score: {risk:.0f}/100\n\n"

            if risk >= 80:
                summary += "🚨 CRITICAL RISK - Immediate action required"
            elif risk >= 50:
                summary += "⚠️  HIGH RISK - Address soon"
            else:
                summary += "⚠️  MEDIUM RISK - Review and remediate"

        return summary
