"""Example 3: Comprehensive Security Audit Pipeline

This example shows how to perform a complete security audit including:
- Code security scanning
- Dependency vulnerability checking
- Secret detection
- Configuration security review
"""

import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any
from aiops.agents.security_scanner import SecurityScannerAgent
from aiops.agents.dependency_analyzer import DependencyAnalyzerAgent
from aiops.agents.secret_scanner import SecretScannerAgent
from aiops.agents.config_drift_detector import ConfigurationDriftDetector


class SecurityAuditPipeline:
    """Complete security audit pipeline."""

    def __init__(self):
        self.security_scanner = SecurityScannerAgent()
        self.dependency_analyzer = DependencyAnalyzerAgent()
        self.secret_scanner = SecretScannerAgent()
        self.config_detector = ConfigurationDriftDetector()

        self.findings = {
            "code_vulnerabilities": [],
            "dependency_issues": [],
            "secrets_found": [],
            "config_issues": [],
        }

    async def scan_code_files(self, directory: str):
        """Scan all code files for vulnerabilities."""

        print("\n🔍 Step 1: Scanning Code for Vulnerabilities")
        print("-" * 60)

        code_files = list(Path(directory).rglob("*.py"))
        print(f"Found {len(code_files)} Python files")

        for file_path in code_files:
            try:
                with open(file_path, 'r') as f:
                    code = f.read()

                result = await self.security_scanner.execute(
                    code=code,
                    language="python"
                )

                if result.critical_count > 0 or result.high_count > 0:
                    self.findings["code_vulnerabilities"].append({
                        "file": str(file_path),
                        "risk_score": result.risk_score,
                        "critical": result.critical_count,
                        "high": result.high_count,
                        "vulnerabilities": [
                            {
                                "severity": v.severity,
                                "category": v.category,
                                "description": v.description,
                                "owasp": v.owasp_category,
                            }
                            for v in result.vulnerabilities
                        ]
                    })
                    print(f"  ⚠️  {file_path.name}: {result.total_issues} issues")
                else:
                    print(f"  ✅ {file_path.name}: Clean")

            except Exception as e:
                print(f"  ❌ Error scanning {file_path}: {e}")

    async def check_dependencies(self, requirements_file: str):
        """Check dependencies for known vulnerabilities."""

        print("\n📦 Step 2: Checking Dependencies")
        print("-" * 60)

        try:
            with open(requirements_file, 'r') as f:
                dependencies = f.read()

            result = await self.dependency_analyzer.execute(
                dependencies=dependencies,
                language="python"
            )

            print(f"Total packages: {result.total_packages}")
            print(f"Vulnerable packages: {result.vulnerable_count}")
            print(f"Outdated packages: {result.outdated_count}")

            if result.vulnerabilities:
                self.findings["dependency_issues"] = [
                    {
                        "package": v.package_name,
                        "version": v.current_version,
                        "severity": v.severity,
                        "description": v.description,
                        "fix_version": v.fixed_version,
                    }
                    for v in result.vulnerabilities
                ]

                print("\n⚠️  Vulnerable Packages:")
                for v in result.vulnerabilities:
                    print(f"  - {v.package_name} {v.current_version}")
                    print(f"    {v.description}")
                    print(f"    Fix: Upgrade to {v.fixed_version}")

        except Exception as e:
            print(f"❌ Error checking dependencies: {e}")

    async def scan_secrets(self, directory: str):
        """Scan for exposed secrets and credentials."""

        print("\n🔐 Step 3: Scanning for Secrets")
        print("-" * 60)

        # Common files that might contain secrets
        patterns = [
            "*.py", "*.js", "*.ts", "*.json", "*.yaml", "*.yml",
            ".env*", "config.*", "*.conf"
        ]

        files_to_scan = []
        for pattern in patterns:
            files_to_scan.extend(Path(directory).rglob(pattern))

        print(f"Scanning {len(files_to_scan)} files for secrets...")

        secrets_found = 0

        for file_path in files_to_scan:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()

                result = await self.secret_scanner.execute(
                    content=content,
                    file_path=str(file_path)
                )

                if result.secrets_found > 0:
                    secrets_found += result.secrets_found
                    self.findings["secrets_found"].append({
                        "file": str(file_path),
                        "count": result.secrets_found,
                        "types": result.secret_types,
                        "risk_score": result.risk_score,
                    })
                    print(f"  🚨 {file_path.name}: {result.secrets_found} secrets found!")

            except Exception as e:
                # Skip binary files
                continue

        if secrets_found == 0:
            print("✅ No secrets found")
        else:
            print(f"\n⚠️  Total secrets found: {secrets_found}")

    async def review_configurations(self, config_files: List[str]):
        """Review configuration files for security issues."""

        print("\n⚙️  Step 4: Reviewing Configurations")
        print("-" * 60)

        for config_file in config_files:
            try:
                with open(config_file, 'r') as f:
                    config = f.read()

                # Determine config type
                if config_file.endswith('.py'):
                    config_type = "django"
                elif config_file.endswith(('.yaml', '.yml')):
                    config_type = "kubernetes"
                else:
                    config_type = "general"

                result = await self.security_scanner.scan_config(
                    config=config,
                    config_type=config_type
                )

                if result.total_issues > 0:
                    self.findings["config_issues"].append({
                        "file": config_file,
                        "type": config_type,
                        "issues": result.total_issues,
                        "critical": result.critical_count,
                    })
                    print(f"  ⚠️  {Path(config_file).name}: {result.total_issues} issues")
                else:
                    print(f"  ✅ {Path(config_file).name}: Secure")

            except Exception as e:
                print(f"  ❌ Error reviewing {config_file}: {e}")

    def generate_report(self, output_file: str = "security_audit_report.json"):
        """Generate comprehensive security audit report."""

        print("\n" + "="*60)
        print("📊 SECURITY AUDIT REPORT")
        print("="*60)

        # Calculate overall risk score
        total_critical = sum(
            finding.get("critical", 0)
            for finding in self.findings["code_vulnerabilities"]
        )
        total_high = sum(
            finding.get("high", 0)
            for finding in self.findings["code_vulnerabilities"]
        )
        total_secrets = sum(
            finding.get("count", 0)
            for finding in self.findings["secrets_found"]
        )
        total_dep_issues = len(self.findings["dependency_issues"])

        # Summary
        print(f"\n🔍 Code Vulnerabilities:")
        print(f"   Files with issues: {len(self.findings['code_vulnerabilities'])}")
        print(f"   Critical: {total_critical}")
        print(f"   High: {total_high}")

        print(f"\n📦 Dependency Issues:")
        print(f"   Vulnerable packages: {total_dep_issues}")

        print(f"\n🔐 Secrets Exposed:")
        print(f"   Files with secrets: {len(self.findings['secrets_found'])}")
        print(f"   Total secrets: {total_secrets}")

        print(f"\n⚙️  Configuration Issues:")
        print(f"   Files with issues: {len(self.findings['config_issues'])}")

        # Risk level
        if total_critical > 0 or total_secrets > 0:
            risk_level = "CRITICAL"
            emoji = "🔴"
        elif total_high > 0 or total_dep_issues > 0:
            risk_level = "HIGH"
            emoji = "🟠"
        elif len(self.findings["config_issues"]) > 0:
            risk_level = "MEDIUM"
            emoji = "🟡"
        else:
            risk_level = "LOW"
            emoji = "🟢"

        print(f"\n{emoji} Overall Risk Level: {risk_level}")

        # Recommendations
        print(f"\n📋 Priority Actions:")
        priority_actions = []

        if total_secrets > 0:
            priority_actions.append("1. IMMEDIATE: Remove exposed secrets from repository")
        if total_critical > 0:
            priority_actions.append("2. HIGH: Fix critical code vulnerabilities")
        if total_dep_issues > 0:
            priority_actions.append("3. HIGH: Update vulnerable dependencies")
        if total_high > 0:
            priority_actions.append("4. MEDIUM: Address high-severity code issues")
        if len(self.findings["config_issues"]) > 0:
            priority_actions.append("5. MEDIUM: Review and secure configurations")

        if priority_actions:
            for action in priority_actions:
                print(f"   {action}")
        else:
            print("   ✅ No critical actions required")

        # Save detailed report
        report = {
            "summary": {
                "risk_level": risk_level,
                "total_critical": total_critical,
                "total_high": total_high,
                "total_secrets": total_secrets,
                "total_dependency_issues": total_dep_issues,
            },
            "findings": self.findings,
            "priority_actions": priority_actions,
        }

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n📄 Detailed report saved to: {output_file}")

        return report


async def run_security_audit(project_dir: str):
    """Run complete security audit on a project."""

    print("🛡️  Starting Comprehensive Security Audit")
    print("="*60)
    print(f"Project: {project_dir}")

    pipeline = SecurityAuditPipeline()

    # 1. Scan code files
    await pipeline.scan_code_files(project_dir)

    # 2. Check dependencies
    requirements = Path(project_dir) / "requirements.txt"
    if requirements.exists():
        await pipeline.check_dependencies(str(requirements))

    # 3. Scan for secrets
    await pipeline.scan_secrets(project_dir)

    # 4. Review configurations
    config_files = []
    for pattern in ["settings.py", "config.py", "*.yaml", "*.yml", ".env*"]:
        config_files.extend(str(p) for p in Path(project_dir).rglob(pattern))

    if config_files:
        await pipeline.review_configurations(config_files)

    # 5. Generate report
    report = pipeline.generate_report()

    print("\n✅ Security Audit Complete!\n")

    return report


if __name__ == "__main__":
    import sys

    project_dir = sys.argv[1] if len(sys.argv) > 1 else "."

    report = asyncio.run(run_security_audit(project_dir))

    # Exit with error code if critical issues found
    if report["summary"]["risk_level"] == "CRITICAL":
        sys.exit(1)
