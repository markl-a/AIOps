"""
Unit tests for IaC Validator Agent
"""

import pytest
from aiops.agents.iac_validator import (
    IaCValidator,
    IaCIssue,
    IaCValidationResult
)


class TestIaCIssue:
    """Tests for IaCIssue model"""

    def test_create_issue(self):
        """Test creating an IaC issue"""
        issue = IaCIssue(
            severity="critical",
            category="security",
            resource_type="aws_s3_bucket",
            resource_name="my-bucket",
            issue="Public bucket detected",
            recommendation="Make bucket private",
            line_number=42,
            code_snippet='acl = "public-read"'
        )
        assert issue.severity == "critical"
        assert issue.category == "security"
        assert issue.line_number == 42

    def test_issue_severities(self):
        """Test different severity levels"""
        for severity in ["critical", "high", "medium", "low"]:
            issue = IaCIssue(
                severity=severity,
                category="security",
                resource_type="test",
                resource_name="test",
                issue="Test issue",
                recommendation="Fix it"
            )
            assert issue.severity == severity

    def test_issue_categories(self):
        """Test different categories"""
        for category in ["security", "cost", "compliance", "best_practice"]:
            issue = IaCIssue(
                severity="medium",
                category=category,
                resource_type="test",
                resource_name="test",
                issue="Test",
                recommendation="Fix"
            )
            assert issue.category == category

    def test_issue_optional_fields(self):
        """Test issue without optional fields"""
        issue = IaCIssue(
            severity="low",
            category="best_practice",
            resource_type="resource",
            resource_name="name",
            issue="Issue",
            recommendation="Fix"
        )
        assert issue.line_number is None
        assert issue.code_snippet is None


class TestIaCValidationResult:
    """Tests for IaCValidationResult model"""

    def test_create_result(self):
        """Test creating validation result"""
        result = IaCValidationResult(
            iac_type="terraform",
            file_path="main.tf",
            issues=[],
            security_score=100.0,
            cost_score=100.0,
            compliance_score=100.0,
            total_resources=5,
            summary="No issues found"
        )
        assert result.iac_type == "terraform"
        assert result.security_score == 100.0
        assert result.total_resources == 5

    def test_result_with_issues(self):
        """Test result with issues"""
        issues = [
            IaCIssue(
                severity="high",
                category="security",
                resource_type="s3",
                resource_name="bucket",
                issue="Public",
                recommendation="Fix"
            )
        ]
        result = IaCValidationResult(
            iac_type="terraform",
            file_path="main.tf",
            issues=issues,
            security_score=80.0,
            cost_score=100.0,
            compliance_score=100.0,
            total_resources=3,
            summary="1 issue"
        )
        assert len(result.issues) == 1


class TestIaCValidator:
    """Tests for IaCValidator"""

    @pytest.fixture
    def validator(self):
        """Create validator instance"""
        return IaCValidator()

    @pytest.mark.asyncio
    async def test_validate_clean_terraform(self, validator):
        """Test validation of clean Terraform code"""
        tf_code = '''
resource "aws_instance" "example" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t3.micro"

  tags = {
    Name = "example"
  }
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]
}
'''
        result = await validator.validate_terraform(tf_code)

        assert result.iac_type == "terraform"
        assert result.security_score > 0

    @pytest.mark.asyncio
    async def test_detect_hardcoded_credentials(self, validator):
        """Test detection of hardcoded credentials"""
        tf_code = '''
resource "aws_db_instance" "db" {
  password = "supersecretpassword123"
}
'''
        result = await validator.validate_terraform(tf_code)

        security_issues = [i for i in result.issues if i.category == "security"]
        assert len(security_issues) >= 1
        assert any("hardcoded" in i.issue.lower() or "credential" in i.issue.lower()
                   for i in security_issues)

    @pytest.mark.asyncio
    async def test_detect_public_s3_bucket(self, validator):
        """Test detection of public S3 bucket"""
        tf_code = '''
resource "aws_s3_bucket" "public" {
  bucket = "my-public-bucket"
  acl    = "public-read"
}
'''
        result = await validator.validate_terraform(tf_code)

        s3_issues = [i for i in result.issues if "s3" in i.resource_type.lower()]
        assert len(s3_issues) >= 1
        assert any("public" in i.issue.lower() for i in s3_issues)

    @pytest.mark.asyncio
    async def test_detect_public_s3_bucket_write(self, validator):
        """Test detection of public-read-write S3 bucket"""
        tf_code = '''
resource "aws_s3_bucket" "very_public" {
  bucket = "dangerous-bucket"
  acl    = "public-read-write"
}
'''
        result = await validator.validate_terraform(tf_code)

        s3_issues = [i for i in result.issues if "s3" in i.resource_type.lower()]
        assert len(s3_issues) >= 1

    @pytest.mark.asyncio
    async def test_detect_unencrypted_rds(self, validator):
        """Test detection of unencrypted RDS"""
        tf_code = '''
resource "aws_db_instance" "unencrypted" {
  allocated_storage = 20
  engine            = "mysql"
  instance_class    = "db.t3.micro"
}
'''
        result = await validator.validate_terraform(tf_code)

        rds_issues = [i for i in result.issues if "db_instance" in i.resource_type.lower()]
        assert len(rds_issues) >= 1
        assert any("encrypt" in i.issue.lower() for i in rds_issues)

    @pytest.mark.asyncio
    async def test_detect_open_security_group(self, validator):
        """Test detection of overly permissive security group"""
        tf_code = '''
resource "aws_security_group" "wide_open" {
  name = "wide-open"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
'''
        result = await validator.validate_terraform(tf_code)

        sg_issues = [i for i in result.issues if "security_group" in i.resource_type.lower()]
        assert len(sg_issues) >= 1
        assert any("0.0.0.0/0" in i.issue for i in sg_issues)

    @pytest.mark.asyncio
    async def test_detect_missing_tags(self, validator):
        """Test detection of missing tags"""
        tf_code = '''
resource "aws_instance" "no_tags" {
  ami           = "ami-12345"
  instance_type = "t3.micro"
}

resource "aws_instance" "has_tags" {
  ami           = "ami-12345"
  instance_type = "t3.micro"
  tags = {
    Name = "tagged"
  }
}
'''
        result = await validator.validate_terraform(tf_code)

        tag_issues = [i for i in result.issues if "tag" in i.issue.lower()]
        assert len(tag_issues) >= 1

    @pytest.mark.asyncio
    async def test_detect_hardcoded_ami(self, validator):
        """Test detection of hardcoded AMI"""
        tf_code = '''
resource "aws_instance" "hardcoded_ami" {
  ami           = "ami-0123456789abcdef0"
  instance_type = "t3.micro"
}
'''
        result = await validator.validate_terraform(tf_code)

        ami_issues = [i for i in result.issues if "ami" in i.issue.lower()]
        assert len(ami_issues) >= 1
        assert any("hardcoded" in i.issue.lower() or "dynamic" in i.recommendation.lower()
                   for i in ami_issues)

    @pytest.mark.asyncio
    async def test_custom_file_path(self, validator):
        """Test custom file path"""
        result = await validator.validate_terraform("", file_path="modules/vpc/main.tf")

        assert result.file_path == "modules/vpc/main.tf"

    @pytest.mark.asyncio
    async def test_resource_counting(self, validator):
        """Test resource counting"""
        tf_code = '''
resource "aws_instance" "one" {}
resource "aws_instance" "two" {}
resource "aws_s3_bucket" "three" {}
'''
        result = await validator.validate_terraform(tf_code)

        assert result.total_resources == 3

    def test_calculate_security_score_no_issues(self, validator):
        """Test security score with no issues"""
        score = validator._calculate_security_score([])
        assert score == 100.0

    def test_calculate_security_score_critical_issue(self, validator):
        """Test security score with critical issue"""
        issues = [
            IaCIssue(
                severity="critical",
                category="security",
                resource_type="test",
                resource_name="test",
                issue="Critical issue",
                recommendation="Fix"
            )
        ]
        score = validator._calculate_security_score(issues)
        assert score == 70.0  # 100 - 30

    def test_calculate_security_score_high_issue(self, validator):
        """Test security score with high severity issue"""
        issues = [
            IaCIssue(
                severity="high",
                category="security",
                resource_type="test",
                resource_name="test",
                issue="High issue",
                recommendation="Fix"
            )
        ]
        score = validator._calculate_security_score(issues)
        assert score == 80.0  # 100 - 20

    def test_calculate_security_score_medium_issue(self, validator):
        """Test security score with medium severity issue"""
        issues = [
            IaCIssue(
                severity="medium",
                category="security",
                resource_type="test",
                resource_name="test",
                issue="Medium issue",
                recommendation="Fix"
            )
        ]
        score = validator._calculate_security_score(issues)
        assert score == 90.0  # 100 - 10

    def test_calculate_security_score_ignores_non_security(self, validator):
        """Test that non-security issues don't affect security score"""
        issues = [
            IaCIssue(
                severity="critical",
                category="cost",
                resource_type="test",
                resource_name="test",
                issue="Cost issue",
                recommendation="Fix"
            )
        ]
        score = validator._calculate_security_score(issues)
        assert score == 100.0

    def test_calculate_security_score_minimum_zero(self, validator):
        """Test that security score doesn't go below 0"""
        issues = [
            IaCIssue(
                severity="critical",
                category="security",
                resource_type="test",
                resource_name="test",
                issue=f"Issue {i}",
                recommendation="Fix"
            )
            for i in range(10)  # 10 critical issues = -300
        ]
        score = validator._calculate_security_score(issues)
        assert score == 0.0

    def test_calculate_cost_score_no_issues(self, validator):
        """Test cost score with no issues"""
        score = validator._calculate_cost_score([])
        assert score == 100.0

    def test_calculate_cost_score_high_issue(self, validator):
        """Test cost score with high severity issue"""
        issues = [
            IaCIssue(
                severity="high",
                category="cost",
                resource_type="test",
                resource_name="test",
                issue="Cost issue",
                recommendation="Fix"
            )
        ]
        score = validator._calculate_cost_score(issues)
        assert score == 80.0

    def test_calculate_compliance_score_no_issues(self, validator):
        """Test compliance score with no issues"""
        score = validator._calculate_compliance_score([])
        assert score == 100.0

    def test_calculate_compliance_score_critical(self, validator):
        """Test compliance score with critical issue"""
        issues = [
            IaCIssue(
                severity="critical",
                category="compliance",
                resource_type="test",
                resource_name="test",
                issue="Compliance issue",
                recommendation="Fix"
            )
        ]
        score = validator._calculate_compliance_score(issues)
        assert score == 75.0

    def test_validator_initialization(self):
        """Test validator initialization"""
        validator = IaCValidator()
        assert validator.llm_factory is None

        mock_factory = object()
        validator_with_factory = IaCValidator(llm_factory=mock_factory)
        assert validator_with_factory.llm_factory is mock_factory


class TestIaCValidatorEdgeCases:
    """Edge case tests"""

    @pytest.fixture
    def validator(self):
        return IaCValidator()

    @pytest.mark.asyncio
    async def test_empty_terraform_code(self, validator):
        """Test with empty Terraform code"""
        result = await validator.validate_terraform("")

        assert result.total_resources == 0
        assert result.security_score == 100.0

    @pytest.mark.asyncio
    async def test_comments_only(self, validator):
        """Test with only comments"""
        tf_code = """
# This is a comment
# resource "aws_instance" "fake" {}
"""
        result = await validator.validate_terraform(tf_code)

        assert result.total_resources == 0

    @pytest.mark.asyncio
    async def test_multiple_issues_same_type(self, validator):
        """Test with multiple issues of same type"""
        tf_code = '''
resource "aws_s3_bucket" "bucket1" {
  acl = "public-read"
}
resource "aws_s3_bucket" "bucket2" {
  acl = "public-read"
}
'''
        result = await validator.validate_terraform(tf_code)

        # Should detect public bucket issue
        assert len([i for i in result.issues if "s3" in i.resource_type.lower()]) >= 1

    @pytest.mark.asyncio
    async def test_encrypted_rds_no_issue(self, validator):
        """Test that encrypted RDS doesn't trigger issue"""
        tf_code = '''
resource "aws_db_instance" "encrypted" {
  allocated_storage    = 20
  engine               = "mysql"
  instance_class       = "db.t3.micro"
  storage_encrypted    = true
}
'''
        result = await validator.validate_terraform(tf_code)

        rds_encryption_issues = [
            i for i in result.issues
            if "db_instance" in i.resource_type.lower() and "encrypt" in i.issue.lower()
        ]
        assert len(rds_encryption_issues) == 0

    @pytest.mark.asyncio
    async def test_private_s3_bucket_no_issue(self, validator):
        """Test that private S3 bucket doesn't trigger issue"""
        tf_code = '''
resource "aws_s3_bucket" "private" {
  bucket = "my-private-bucket"
  acl    = "private"
}
'''
        result = await validator.validate_terraform(tf_code)

        public_bucket_issues = [
            i for i in result.issues
            if "s3" in i.resource_type.lower() and "public" in i.issue.lower()
        ]
        assert len(public_bucket_issues) == 0

    @pytest.mark.asyncio
    async def test_restricted_security_group_no_issue(self, validator):
        """Test that restricted security group doesn't trigger issue"""
        tf_code = '''
resource "aws_security_group" "restricted" {
  name = "restricted"

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }
}
'''
        result = await validator.validate_terraform(tf_code)

        open_sg_issues = [
            i for i in result.issues
            if "security_group" in i.resource_type.lower() and "0.0.0.0/0" in i.issue
        ]
        assert len(open_sg_issues) == 0

    @pytest.mark.asyncio
    async def test_dynamic_ami_no_issue(self, validator):
        """Test that dynamic AMI lookup doesn't trigger issue"""
        tf_code = '''
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]
}

resource "aws_instance" "example" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t3.micro"
}
'''
        result = await validator.validate_terraform(tf_code)

        ami_issues = [i for i in result.issues if "ami" in i.issue.lower() and "hardcoded" in i.issue.lower()]
        assert len(ami_issues) == 0

    @pytest.mark.asyncio
    async def test_all_resources_tagged(self, validator):
        """Test that fully tagged resources don't trigger tag issue"""
        tf_code = '''
resource "aws_instance" "one" {
  ami = "ami-123"
  tags = { Name = "one" }
}

resource "aws_instance" "two" {
  ami = "ami-123"
  tags = { Name = "two" }
}
'''
        result = await validator.validate_terraform(tf_code)

        tag_issues = [i for i in result.issues if "missing" in i.issue.lower() and "tag" in i.issue.lower()]
        assert len(tag_issues) == 0
