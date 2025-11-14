"""Full project integration example showing complete AIOps workflow."""

import asyncio
from pathlib import Path
from aiops.agents.code_reviewer import CodeReviewAgent
from aiops.agents.security_scanner import SecurityScannerAgent
from aiops.agents.dependency_analyzer import DependencyAnalyzerAgent
from aiops.agents.code_quality import CodeQualityAgent
from aiops.tools.batch_processor import BatchProcessor
from aiops.tools.project_scanner import ProjectScanner
from aiops.tools.notifications import NotificationService
from aiops.core.logger import setup_logger


async def complete_project_analysis(project_path: Path):
    """
    Perform complete project analysis with all agents.

    This demonstrates a real-world workflow for analyzing a project.
    """
    print("\n" + "=" * 60)
    print("  Complete Project Analysis with AIOps")
    print("=" * 60 + "\n")

    # Step 1: Scan project structure
    print("📁 Step 1: Scanning project structure...")
    scanner = ProjectScanner(project_path)
    project_info = scanner.get_project_structure()

    print(f"  ✓ Found {project_info['total_files']} files")
    print(f"  ✓ Total lines of code: {project_info['total_lines']:,}")

    # Step 2: Identify project type
    print("\n🔍 Step 2: Identifying project type...")
    project_type = scanner.identify_project_type()
    print(f"  ✓ Languages: {', '.join(project_type['languages'])}")
    if project_type['frameworks']:
        print(f"  ✓ Frameworks: {', '.join(project_type['frameworks'])}")

    # Step 3: Security scanning
    print("\n🔒 Step 3: Security analysis...")
    python_files = list(project_path.glob("**/*.py"))[:5]  # Limit for demo

    if python_files:
        security_agent = SecurityScannerAgent()

        for file in python_files:
            code = file.read_text()
            result = await security_agent.execute(code=code, language="python")

            print(f"\n  File: {file.name}")
            print(f"  Security Score: {result.security_score}/100")

            if result.code_vulnerabilities:
                print(f"  ⚠️  {len(result.code_vulnerabilities)} vulnerabilities found")
                for vuln in result.code_vulnerabilities[:2]:  # Show top 2
                    print(f"    - [{vuln.severity}] {vuln.title}")
            else:
                print("  ✅ No vulnerabilities detected")

    # Step 4: Code quality analysis
    print("\n📊 Step 4: Code quality analysis...")
    quality_agent = CodeQualityAgent()

    if python_files:
        total_score = 0
        for file in python_files[:3]:  # Analyze 3 files
            code = file.read_text()
            result = await quality_agent.execute(code=code, language="python")

            print(f"\n  File: {file.name}")
            print(f"  Quality Score: {result.overall_quality_score}/100 (Grade: {result.grade})")
            print(f"  Maintainability Index: {result.maintainability_index}/100")
            print(f"  Code Smells: {len(result.code_smells)}")

            total_score += result.overall_quality_score

        avg_score = total_score / min(3, len(python_files))
        print(f"\n  Average Quality Score: {avg_score:.1f}/100")

    # Step 5: Dependency analysis
    print("\n📦 Step 5: Dependency analysis...")
    req_file = project_path / "requirements.txt"

    if req_file.exists():
        dep_agent = DependencyAnalyzerAgent()
        deps = req_file.read_text()
        result = await dep_agent.execute(dependencies=deps, dependency_type="python")

        print(f"  Total Dependencies: {result.total_dependencies}")
        print(f"  Outdated: {result.outdated_count}")

        if result.issues:
            print(f"  ⚠️  {len(result.issues)} issues found")
            for issue in result.issues[:3]:
                print(f"    - [{issue.severity}] {issue.package_name}: {issue.description}")
    else:
        print("  ℹ️  No requirements.txt found")

    # Step 6: Test coverage analysis
    print("\n🧪 Step 6: Test coverage analysis...")
    test_coverage = scanner.calculate_test_coverage_potential()

    print(f"  Source Files: {test_coverage['source_files']}")
    print(f"  Test Files: {test_coverage['test_files']}")
    print(f"  Coverage Ratio: {test_coverage['coverage_ratio']:.1%}")
    print(f"  Files Without Tests: {test_coverage['files_without_tests']}")

    # Step 7: Batch code review
    print("\n👁️  Step 7: Batch code review...")
    processor = BatchProcessor(max_concurrent=3)

    if python_files:
        review_results = await processor.review_project(
            project_path=project_path,
            language="python",
            exclude_patterns=["venv", "__pycache__", "tests"],
        )

        print(f"  Files Reviewed: {review_results['files_reviewed']}")
        print(f"  Average Score: {review_results['average_score']:.1f}/100")
        print(f"  Total Issues: {review_results['total_issues']}")
        print(f"  Critical Issues: {review_results['critical_issues']}")

    # Step 8: Generate comprehensive report
    print("\n📝 Step 8: Generating comprehensive report...")
    report = scanner.generate_project_report()

    report_file = project_path / "AIOps_Analysis_Report.md"
    report_file.write_text(report)
    print(f"  ✓ Report saved to: {report_file}")

    # Step 9: Send notifications (if configured)
    print("\n📬 Step 9: Sending notifications...")
    await NotificationService.send_slack(
        message=f"🤖 AIOps Analysis Complete for {project_path.name}\n\n"
        f"Files Reviewed: {review_results.get('files_reviewed', 0)}\n"
        f"Average Score: {review_results.get('average_score', 0):.1f}/100\n"
        f"Critical Issues: {review_results.get('critical_issues', 0)}"
    )
    print("  ✓ Notifications sent (if webhooks configured)")

    print("\n" + "=" * 60)
    print("  ✅ Analysis Complete!")
    print("=" * 60 + "\n")


async def ci_cd_integration_example():
    """
    Example of CI/CD integration workflow.

    This shows how to use AIOps in a CI/CD pipeline.
    """
    print("\n" + "=" * 60)
    print("  CI/CD Integration Example")
    print("=" * 60 + "\n")

    # Simulate getting changed files from git
    changed_files = [
        "src/api/handler.py",
        "src/utils/validator.py",
    ]

    print(f"📝 Changed files in this PR: {len(changed_files)}")

    # Review each changed file
    reviewer = CodeReviewAgent()
    all_issues = []

    for file_path in changed_files:
        print(f"\n🔍 Reviewing: {file_path}")

        # In real scenario, read actual file
        sample_code = """
def process_user_input(user_data):
    # Simulate processing
    result = eval(user_data)  # Security issue!
    return result
"""

        result = await reviewer.execute(code=sample_code, language="python")

        print(f"  Score: {result.overall_score}/100")
        print(f"  Issues: {len(result.issues)}")

        all_issues.extend(result.issues)

        # Check if review passes threshold
        if result.overall_score < 70:
            print("  ❌ Review failed - score below threshold")
        else:
            print("  ✅ Review passed")

    # Security scan
    print("\n🔒 Running security scan...")
    security_scanner = SecurityScannerAgent()

    scan_result = await security_scanner.execute(code=sample_code, language="python")

    if scan_result.code_vulnerabilities:
        print(f"  ⚠️  {len(scan_result.code_vulnerabilities)} vulnerabilities found")

        # Block PR if critical vulnerabilities
        critical_vulns = [
            v for v in scan_result.code_vulnerabilities if v.severity == "critical"
        ]

        if critical_vulns:
            print("  ❌ BLOCKING: Critical security vulnerabilities must be fixed!")
            print("\n  Critical Issues:")
            for vuln in critical_vulns:
                print(f"    - {vuln.title}")
                print(f"      {vuln.remediation}")
        else:
            print("  ⚠️  WARNING: Non-critical vulnerabilities found")
    else:
        print("  ✅ No security issues detected")

    # Generate PR comment
    print("\n💬 Generating PR comment...")

    pr_comment = f"""## 🤖 AI Code Review

### Summary
- **Files Reviewed**: {len(changed_files)}
- **Total Issues**: {len(all_issues)}
- **Security Issues**: {len(scan_result.code_vulnerabilities)}

### Issues Found
"""

    for issue in all_issues[:5]:  # Top 5 issues
        pr_comment += f"\n#### [{issue.severity.upper()}] {issue.category}\n"
        pr_comment += f"{issue.description}\n\n"
        pr_comment += f"**Suggestion**: {issue.suggestion}\n"

    print(pr_comment)

    print("\n✅ CI/CD analysis complete")


async def main():
    """Run all examples."""
    setup_logger()

    print("\n🚀 AIOps Full Integration Examples\n")

    # Example 1: Analyze current project
    current_dir = Path.cwd()
    print(f"Analyzing current directory: {current_dir}\n")

    await complete_project_analysis(current_dir)

    # Example 2: CI/CD integration
    await ci_cd_integration_example()

    print("\n✨ All examples completed!\n")


if __name__ == "__main__":
    asyncio.run(main())
