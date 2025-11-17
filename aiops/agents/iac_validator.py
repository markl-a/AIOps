"""
Infrastructure as Code (IaC) Validator Agent

Validates and optimizes Terraform, CloudFormation, and other IaC templates
for security, cost, and best practices.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from aiops.core.logger import get_logger
import re
import json

logger = get_logger(__name__)


class IaCIssue(BaseModel):
    """IaC validation issue"""
    severity: str = Field(description="critical, high, medium, low")
    category: str = Field(description="security, cost, compliance, best_practice")
    resource_type: str = Field(description="Type of resource")
    resource_name: str = Field(description="Name of resource")
    issue: str = Field(description="Description of the issue")
    recommendation: str = Field(description="How to fix it")
    line_number: Optional[int] = Field(description="Line number in template")
    code_snippet: Optional[str] = Field(description="Relevant code")


class IaCValidationResult(BaseModel):
    """IaC validation result"""
    analyzed_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    iac_type: str = Field(description="terraform, cloudformation, arm, etc.")
    file_path: str = Field(description="Path to IaC file")
    issues: List[IaCIssue] = Field(description="List of issues found")
    security_score: float = Field(description="Security score 0-100")
    cost_score: float = Field(description="Cost optimization score 0-100")
    compliance_score: float = Field(description="Compliance score 0-100")
    total_resources: int = Field(description="Total resources in template")
    summary: str = Field(description="Summary")


class IaCValidator:
    """Infrastructure as Code validator"""

    def __init__(self, llm_factory=None):
        self.llm_factory = llm_factory
        logger.info("IaC Validator Agent initialized")

    async def validate_terraform(self, terraform_code: str, file_path: str = "main.tf") -> IaCValidationResult:
        """Validate Terraform configuration"""
        issues = []

        # Check for hardcoded credentials
        if re.search(r'(password|secret|api_key)\s*=\s*["\'][^"\']+["\']', terraform_code, re.IGNORECASE):
            issues.append(IaCIssue(
                severity="critical",
                category="security",
                resource_type="credential",
                resource_name="hardcoded_secret",
                issue="Hardcoded credentials detected in Terraform code",
                recommendation="Use variables, AWS Secrets Manager, or environment variables instead",
                line_number=None,
                code_snippet=None
            ))

        # Check for public S3 buckets
        if 'acl = "public-read"' in terraform_code or 'acl = "public-read-write"' in terraform_code:
            issues.append(IaCIssue(
                severity="high",
                category="security",
                resource_type="aws_s3_bucket",
                resource_name="bucket",
                issue="S3 bucket configured with public ACL",
                recommendation="Use private ACL and configure bucket policies carefully. Enable bucket versioning and encryption.",
                line_number=None
            ))

        # Check for missing encryption
        if 'aws_db_instance' in terraform_code and 'storage_encrypted' not in terraform_code:
            issues.append(IaCIssue(
                severity="high",
                category="security",
                resource_type="aws_db_instance",
                resource_name="database",
                issue="RDS instance without encryption enabled",
                recommendation="Add 'storage_encrypted = true' to encrypt data at rest",
                line_number=None
            ))

        # Check for overly permissive security groups
        if '"0.0.0.0/0"' in terraform_code and 'ingress' in terraform_code:
            issues.append(IaCIssue(
                severity="high",
                category="security",
                resource_type="aws_security_group",
                resource_name="sg",
                issue="Security group allows ingress from 0.0.0.0/0",
                recommendation="Restrict ingress to specific IP ranges or security groups",
                line_number=None
            ))

        # Check for missing tags
        resource_count = terraform_code.count('resource "')
        tags_count = terraform_code.count('tags = {')
        if resource_count > tags_count:
            issues.append(IaCIssue(
                severity="medium",
                category="best_practice",
                resource_type="all",
                resource_name="resources",
                issue=f"{resource_count - tags_count} resources missing tags",
                recommendation="Add tags for cost tracking, ownership, and environment identification",
                line_number=None
            ))

        # Check for latest AMI usage
        if 'ami-' in terraform_code and 'data "aws_ami"' not in terraform_code:
            issues.append(IaCIssue(
                severity="medium",
                category="best_practice",
                resource_type="aws_instance",
                resource_name="ec2",
                issue="Using hardcoded AMI ID instead of dynamic lookup",
                recommendation="Use data source to get latest AMI for better security and updates",
                line_number=None
            ))

        # Calculate scores
        security_score = self._calculate_security_score(issues)
        cost_score = self._calculate_cost_score(issues)
        compliance_score = self._calculate_compliance_score(issues)

        summary = f"Found {len(issues)} issues. Security: {security_score:.0f}/100, Cost: {cost_score:.0f}/100"

        return IaCValidationResult(
            iac_type="terraform",
            file_path=file_path,
            issues=issues,
            security_score=security_score,
            cost_score=cost_score,
            compliance_score=compliance_score,
            total_resources=resource_count,
            summary=summary
        )

    def _calculate_security_score(self, issues: List[IaCIssue]) -> float:
        score = 100.0
        for issue in issues:
            if issue.category == "security":
                if issue.severity == "critical":
                    score -= 30
                elif issue.severity == "high":
                    score -= 20
                elif issue.severity == "medium":
                    score -= 10
        return max(0.0, score)

    def _calculate_cost_score(self, issues: List[IaCIssue]) -> float:
        score = 100.0
        for issue in issues:
            if issue.category == "cost":
                if issue.severity == "high":
                    score -= 20
                elif issue.severity == "medium":
                    score -= 10
        return max(0.0, score)

    def _calculate_compliance_score(self, issues: List[IaCIssue]) -> float:
        score = 100.0
        for issue in issues:
            if issue.category == "compliance":
                if issue.severity == "critical":
                    score -= 25
                elif issue.severity == "high":
                    score -= 15
        return max(0.0, score)
