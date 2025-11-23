"""Security configuration validator.

This module provides validation for security-critical configuration
to ensure the application starts with proper security settings.
"""
import os
import re
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass

from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class SecurityIssue:
    """Represents a security configuration issue."""

    severity: str  # "critical", "high", "medium", "low"
    message: str
    recommendation: str


class SecurityValidator:
    """Validates security configuration."""

    # Common weak passwords to check against
    WEAK_PASSWORDS = {
        "admin",
        "password",
        "changeme",
        "123456",
        "qwerty",
        "letmein",
        "welcome",
        "monkey",
        "dragon",
        "master",
        "password123",
        "admin123",
    }

    # Minimum password requirements
    MIN_PASSWORD_LENGTH = 12
    MIN_SECRET_KEY_LENGTH = 32

    @classmethod
    def validate_all(cls) -> Tuple[bool, List[SecurityIssue]]:
        """Validate all security configuration.

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Validate required secrets
        issues.extend(cls._validate_required_secrets())

        # Validate password strength
        issues.extend(cls._validate_password_strength())

        # Validate JWT secret
        issues.extend(cls._validate_jwt_secret())

        # Validate API keys
        issues.extend(cls._validate_api_keys())

        # Check for critical issues
        has_critical = any(issue.severity == "critical" for issue in issues)

        return not has_critical, issues

    @classmethod
    def _validate_required_secrets(cls) -> List[SecurityIssue]:
        """Validate that required secrets are set."""
        issues = []

        # JWT Secret Key
        if not os.getenv("JWT_SECRET_KEY"):
            issues.append(
                SecurityIssue(
                    severity="critical",
                    message="JWT_SECRET_KEY environment variable is not set",
                    recommendation=(
                        "Set JWT_SECRET_KEY to a strong random string. "
                        "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
                    ),
                )
            )

        # Admin Password
        if not os.getenv("ADMIN_PASSWORD"):
            issues.append(
                SecurityIssue(
                    severity="critical",
                    message="ADMIN_PASSWORD environment variable is not set",
                    recommendation="Set ADMIN_PASSWORD to a strong password (minimum 12 characters)",
                )
            )

        return issues

    @classmethod
    def _validate_password_strength(cls) -> List[SecurityIssue]:
        """Validate admin password strength."""
        issues = []
        admin_password = os.getenv("ADMIN_PASSWORD", "")

        if not admin_password:
            return issues  # Already reported in required_secrets

        # Check length
        if len(admin_password) < cls.MIN_PASSWORD_LENGTH:
            issues.append(
                SecurityIssue(
                    severity="high",
                    message=f"ADMIN_PASSWORD is too short ({len(admin_password)} characters)",
                    recommendation=f"Use a password with at least {cls.MIN_PASSWORD_LENGTH} characters",
                )
            )

        # Check against weak passwords
        if admin_password.lower() in cls.WEAK_PASSWORDS:
            issues.append(
                SecurityIssue(
                    severity="critical",
                    message=f"ADMIN_PASSWORD is a commonly used weak password: '{admin_password}'",
                    recommendation="Use a unique, strong password. Consider using a password manager.",
                )
            )

        # Check complexity
        has_upper = any(c.isupper() for c in admin_password)
        has_lower = any(c.islower() for c in admin_password)
        has_digit = any(c.isdigit() for c in admin_password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in admin_password)

        complexity_score = sum([has_upper, has_lower, has_digit, has_special])

        if complexity_score < 3:
            issues.append(
                SecurityIssue(
                    severity="medium",
                    message="ADMIN_PASSWORD lacks complexity",
                    recommendation=(
                        "Use a password with a mix of uppercase, lowercase, "
                        "digits, and special characters"
                    ),
                )
            )

        return issues

    @classmethod
    def _validate_jwt_secret(cls) -> List[SecurityIssue]:
        """Validate JWT secret key."""
        issues = []
        jwt_secret = os.getenv("JWT_SECRET_KEY", "")

        if not jwt_secret:
            return issues  # Already reported in required_secrets

        # Check length
        if len(jwt_secret) < cls.MIN_SECRET_KEY_LENGTH:
            issues.append(
                SecurityIssue(
                    severity="high",
                    message=f"JWT_SECRET_KEY is too short ({len(jwt_secret)} characters)",
                    recommendation=f"Use a secret key with at least {cls.MIN_SECRET_KEY_LENGTH} characters",
                )
            )

        # Check if it looks like a default/example value
        if any(word in jwt_secret.lower() for word in ["secret", "key", "example", "changeme", "default"]):
            issues.append(
                SecurityIssue(
                    severity="high",
                    message="JWT_SECRET_KEY appears to be a default or example value",
                    recommendation="Use a cryptographically random secret key",
                )
            )

        return issues

    @classmethod
    def _validate_api_keys(cls) -> List[SecurityIssue]:
        """Validate LLM API keys configuration."""
        issues = []

        # Check if at least one LLM provider is configured
        has_openai = bool(os.getenv("OPENAI_API_KEY"))
        has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))
        has_google = bool(os.getenv("GOOGLE_API_KEY"))

        if not (has_openai or has_anthropic or has_google):
            issues.append(
                SecurityIssue(
                    severity="high",
                    message="No LLM provider API keys configured",
                    recommendation=(
                        "Set at least one of: OPENAI_API_KEY, ANTHROPIC_API_KEY, or GOOGLE_API_KEY"
                    ),
                )
            )

        return issues

    @classmethod
    def validate_and_raise(cls) -> None:
        """Validate security configuration and raise if critical issues found.

        Raises:
            ValueError: If critical security issues are found
        """
        is_valid, issues = cls.validate_all()

        if not is_valid:
            # Log all issues
            for issue in issues:
                if issue.severity == "critical":
                    logger.error(f"[CRITICAL] {issue.message}")
                    logger.error(f"  → {issue.recommendation}")
                elif issue.severity == "high":
                    logger.warning(f"[HIGH] {issue.message}")
                    logger.warning(f"  → {issue.recommendation}")
                else:
                    logger.info(f"[{issue.severity.upper()}] {issue.message}")

            # Raise error for critical issues
            critical_issues = [i for i in issues if i.severity == "critical"]
            if critical_issues:
                error_messages = [i.message for i in critical_issues]
                raise ValueError(
                    f"Critical security configuration issues found:\n" + "\n".join(f"  - {msg}" for msg in error_messages)
                )

        # Log warnings for non-critical issues
        for issue in issues:
            if issue.severity in ["high", "medium"]:
                logger.warning(f"[{issue.severity.upper()}] {issue.message}")
                logger.warning(f"  → {issue.recommendation}")

    @classmethod
    def get_security_report(cls) -> Dict[str, Any]:
        """Get a detailed security configuration report.

        Returns:
            Dictionary containing security status and recommendations
        """
        is_valid, issues = cls.validate_all()

        critical = [i for i in issues if i.severity == "critical"]
        high = [i for i in issues if i.severity == "high"]
        medium = [i for i in issues if i.severity == "medium"]
        low = [i for i in issues if i.severity == "low"]

        return {
            "is_secure": is_valid and len(high) == 0,
            "is_valid": is_valid,
            "summary": {
                "critical": len(critical),
                "high": len(high),
                "medium": len(medium),
                "low": len(low),
                "total": len(issues),
            },
            "issues": {
                "critical": [{"message": i.message, "recommendation": i.recommendation} for i in critical],
                "high": [{"message": i.message, "recommendation": i.recommendation} for i in high],
                "medium": [{"message": i.message, "recommendation": i.recommendation} for i in medium],
                "low": [{"message": i.message, "recommendation": i.recommendation} for i in low],
            },
        }
