"""
Configuration Drift Detector Agent

Detects configuration drift across environments, compares configurations,
and ensures consistency between dev, staging, and production.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from aiops.core.logger import get_logger
import json

logger = get_logger(__name__)


class ConfigDrift(BaseModel):
    """Configuration drift detected"""
    config_key: str = Field(description="Configuration key that drifted")
    expected_value: Any = Field(description="Expected value (from baseline)")
    actual_value: Any = Field(description="Actual value found")
    environment: str = Field(description="Environment where drift detected")
    severity: str = Field(description="critical, high, medium, low")
    impact: str = Field(description="Potential impact of this drift")
    recommendation: str = Field(description="How to remediate")


class DriftDetectionResult(BaseModel):
    """Configuration drift detection result"""
    analyzed_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    baseline_environment: str = Field(description="Reference environment")
    compared_environment: str = Field(description="Environment being compared")
    total_configs: int = Field(description="Total configurations checked")
    drifts_detected: int = Field(description="Number of drifts found")
    drifts: List[ConfigDrift] = Field(description="List of drifts")
    drift_score: float = Field(description="Drift score 0-100 (100=no drift)")
    compliance_status: str = Field(description="compliant, drifted, critical_drift")
    summary: str = Field(description="Summary")
    recommendations: List[str] = Field(description="Remediation steps")


class ConfigurationDriftDetector:
    """Configuration drift detection agent"""

    def __init__(self, llm_factory=None):
        self.llm_factory = llm_factory
        logger.info("Configuration Drift Detector initialized")

    async def detect_drift(
        self,
        baseline_config: Dict[str, Any],
        target_config: Dict[str, Any],
        baseline_env: str = "production",
        target_env: str = "staging",
        critical_keys: Optional[List[str]] = None
    ) -> DriftDetectionResult:
        """
        Detect configuration drift between environments.

        Args:
            baseline_config: Reference configuration (e.g., production)
            target_config: Configuration to compare (e.g., staging)
            baseline_env: Name of baseline environment
            target_env: Name of target environment
            critical_keys: List of critical configuration keys

        Returns:
            DriftDetectionResult with detected drifts
        """
        drifts = []
        critical_keys = critical_keys or [
            'database_url', 'api_keys', 'security', 'auth', 'encryption'
        ]

        # Compare configurations
        all_keys = set(baseline_config.keys()) | set(target_config.keys())

        for key in all_keys:
            baseline_value = baseline_config.get(key)
            target_value = target_config.get(key)

            # Check for missing keys
            if key in baseline_config and key not in target_config:
                severity = "critical" if any(ck in key.lower() for ck in critical_keys) else "high"
                drifts.append(ConfigDrift(
                    config_key=key,
                    expected_value=baseline_value,
                    actual_value=None,
                    environment=target_env,
                    severity=severity,
                    impact=f"Configuration '{key}' missing in {target_env}. May cause runtime errors.",
                    recommendation=f"Add '{key}' to {target_env} configuration"
                ))
                continue

            if key not in baseline_config and key in target_config:
                drifts.append(ConfigDrift(
                    config_key=key,
                    expected_value=None,
                    actual_value=target_value,
                    environment=target_env,
                    severity="medium",
                    impact=f"Extra configuration '{key}' in {target_env} not present in {baseline_env}",
                    recommendation=f"Review if '{key}' should be in {baseline_env} or removed from {target_env}"
                ))
                continue

            # Check for value differences
            if baseline_value != target_value:
                # Determine severity
                if any(ck in key.lower() for ck in critical_keys):
                    severity = "critical"
                    impact = f"Critical configuration mismatch. May cause security or data integrity issues."
                elif isinstance(baseline_value, (int, float)) and isinstance(target_value, (int, float)):
                    # Numeric configuration
                    diff_pct = abs(baseline_value - target_value) / baseline_value * 100 if baseline_value != 0 else 100
                    if diff_pct > 50:
                        severity = "high"
                        impact = f"Significant numeric difference ({diff_pct:.1f}%). May affect performance or behavior."
                    else:
                        severity = "medium"
                        impact = f"Numeric configuration differs by {diff_pct:.1f}%"
                else:
                    severity = "medium"
                    impact = f"Configuration value differs between environments"

                drifts.append(ConfigDrift(
                    config_key=key,
                    expected_value=baseline_value,
                    actual_value=target_value,
                    environment=target_env,
                    severity=severity,
                    impact=impact,
                    recommendation=f"Align '{key}' across environments or document the intentional difference"
                ))

        # Calculate drift score
        total_configs = len(all_keys)
        drift_score = ((total_configs - len(drifts)) / total_configs * 100) if total_configs > 0 else 100

        # Determine compliance status
        critical_drifts = sum(1 for d in drifts if d.severity == "critical")
        if critical_drifts > 0:
            compliance = "critical_drift"
        elif len(drifts) > 0:
            compliance = "drifted"
        else:
            compliance = "compliant"

        # Generate recommendations
        recommendations = self._generate_recommendations(drifts, baseline_env, target_env)

        # Generate summary
        summary = self._generate_summary(
            baseline_env, target_env, total_configs, len(drifts), drift_score, critical_drifts
        )

        return DriftDetectionResult(
            baseline_environment=baseline_env,
            compared_environment=target_env,
            total_configs=total_configs,
            drifts_detected=len(drifts),
            drifts=drifts,
            drift_score=drift_score,
            compliance_status=compliance,
            summary=summary,
            recommendations=recommendations
        )

    def _generate_recommendations(
        self,
        drifts: List[ConfigDrift],
        baseline_env: str,
        target_env: str
    ) -> List[str]:
        """Generate remediation recommendations"""
        recommendations = []

        critical_drifts = [d for d in drifts if d.severity == "critical"]
        if critical_drifts:
            recommendations.append(f"🚨 URGENT: Resolve {len(critical_drifts)} critical configuration drifts immediately")

        if drifts:
            recommendations.extend([
                f"Use infrastructure-as-code (Terraform/Ansible) to manage configurations",
                f"Implement automated configuration validation in CI/CD pipeline",
                f"Create configuration baseline documentation",
                f"Schedule regular drift detection scans",
                f"Use configuration management tools (e.g., Consul, etcd)"
            ])

            # Specific recommendations based on drift types
            if any('database' in d.config_key.lower() for d in drifts):
                recommendations.append("Review database connection strings across environments")

            if any('key' in d.config_key.lower() or 'secret' in d.config_key.lower() for d in drifts):
                recommendations.append("Ensure secrets are managed through secret management system")

        return recommendations[:6]

    def _generate_summary(
        self,
        baseline: str,
        target: str,
        total: int,
        drifts: int,
        score: float,
        critical: int
    ) -> str:
        """Generate executive summary"""
        summary = f"Configuration Drift Analysis\n"
        summary += f"Baseline: {baseline} → Target: {target}\n\n"
        summary += f"Configurations checked: {total}\n"
        summary += f"Drifts detected: {drifts}\n"
        summary += f"Drift score: {score:.1f}/100\n"

        if critical > 0:
            summary += f"\n⚠️  {critical} CRITICAL drifts require immediate attention\n"

        if score >= 95:
            summary += "\n✓ Environments are well-aligned"
        elif score >= 80:
            summary += "\n⚠ Minor drifts detected, review recommended"
        else:
            summary += "\n✗ Significant drift detected, remediation required"

        return summary
