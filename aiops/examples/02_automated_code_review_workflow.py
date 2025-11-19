"""Example 2: Automated Code Review Workflow

This example demonstrates a complete code review workflow including:
- Code quality analysis
- Security scanning
- Performance analysis
- Auto-fix suggestions
"""

import asyncio
from pathlib import Path
from aiops.agents.code_reviewer import CodeReviewAgent
from aiops.agents.security_scanner import SecurityScannerAgent
from aiops.agents.performance_analyzer import PerformanceAnalyzerAgent
from aiops.agents.auto_fixer import AutoFixerAgent


async def comprehensive_code_review(file_path: str):
    """Perform comprehensive code review with multiple agents."""

    print(f"📝 Comprehensive Code Review: {file_path}")
    print("="*60)

    # Read code
    with open(file_path, 'r') as f:
        code = f.read()

    language = Path(file_path).suffix.lstrip('.')

    # 1. Code Quality Review
    print("\n🔍 Step 1: Code Quality Analysis")
    print("-" * 60)

    reviewer = CodeReviewAgent()
    review = await reviewer.execute(
        code=code,
        language=language,
        standards=["PEP 8", "Clean Code", "SOLID Principles"]
    )

    print(f"Overall Score: {review.overall_score}/100")
    print(f"Issues Found: {len(review.issues)}")

    # Print critical issues
    critical = [i for i in review.issues if i.severity == "critical"]
    if critical:
        print("\n🚨 Critical Issues:")
        for issue in critical:
            print(f"  - Line {issue.line_number}: {issue.description}")
            print(f"    Suggestion: {issue.suggestion}")

    # Print strengths
    if review.strengths:
        print("\n✅ Strengths:")
        for strength in review.strengths:
            print(f"  - {strength}")

    # 2. Security Scan
    print("\n🔒 Step 2: Security Vulnerability Scan")
    print("-" * 60)

    scanner = SecurityScannerAgent()
    security = await scanner.execute(code=code, language=language)

    print(f"Risk Score: {security.risk_score}/100")
    print(f"Vulnerabilities: {security.total_issues}")
    print(f"  - Critical: {security.critical_count}")
    print(f"  - High: {security.high_count}")
    print(f"  - Medium: {security.medium_count}")

    if security.vulnerabilities:
        print("\n⚠️  Top Vulnerabilities:")
        for vuln in security.vulnerabilities[:3]:
            print(f"  [{vuln.severity.upper()}] {vuln.category}")
            print(f"    {vuln.description}")
            print(f"    Fix: {vuln.remediation}")

    # 3. Performance Analysis
    print("\n⚡ Step 3: Performance Analysis")
    print("-" * 60)

    perf_analyzer = PerformanceAnalyzerAgent()
    performance = await perf_analyzer.execute(code=code, language=language)

    print(f"Performance Score: {performance.overall_score}/100")

    if performance.issues:
        print("\n🐌 Performance Issues:")
        for issue in performance.issues:
            print(f"  [{issue.severity.upper()}] {issue.category}")
            print(f"    {issue.description}")
            print(f"    Impact: {issue.impact}")

    if performance.optimizations:
        print("\n💡 Optimization Suggestions:")
        for opt in performance.optimizations[:3]:
            print(f"  - {opt.target}")
            print(f"    {opt.recommendation}")
            print(f"    Expected improvement: {opt.estimated_improvement}")

    # 4. Auto-Fix (if enabled)
    print("\n🔧 Step 4: Auto-Fix Suggestions")
    print("-" * 60)

    auto_fixer = AutoFixerAgent()

    # Collect all issues
    all_issues = []
    all_issues.extend([{
        "type": "code_quality",
        "severity": i.severity,
        "line": i.line_number,
        "description": i.description,
        "suggestion": i.suggestion,
    } for i in review.issues])

    all_issues.extend([{
        "type": "security",
        "severity": v.severity,
        "description": v.description,
        "remediation": v.remediation,
    } for v in security.vulnerabilities])

    if all_issues:
        fixes = await auto_fixer.execute(
            code=code,
            issues=all_issues,
            language=language
        )

        if hasattr(fixes, 'fixed_code') and fixes.fixed_code:
            print("✅ Auto-fixes available!")
            print(f"   {fixes.fixes_applied} issues fixed automatically")

            # Optionally save fixed code
            fixed_path = file_path.replace('.py', '_fixed.py')
            with open(fixed_path, 'w') as f:
                f.write(fixes.fixed_code)
            print(f"   Saved to: {fixed_path}")
        else:
            print("ℹ️  No automatic fixes available - manual review required")

    # 5. Generate Report
    print("\n📊 Final Report")
    print("="*60)

    overall_status = "PASS" if (
        review.overall_score >= 70 and
        security.critical_count == 0 and
        performance.overall_score >= 60
    ) else "NEEDS WORK"

    print(f"\nStatus: {overall_status}")
    print(f"\nScores:")
    print(f"  - Code Quality: {review.overall_score}/100")
    print(f"  - Security: {100 - security.risk_score:.0f}/100")
    print(f"  - Performance: {performance.overall_score}/100")

    # Calculate priorities
    print(f"\n📋 Action Items (by priority):")

    high_priority = []
    medium_priority = []

    if security.critical_count > 0:
        high_priority.append(f"Fix {security.critical_count} critical security issues")

    if critical:
        high_priority.append(f"Address {len(critical)} critical code quality issues")

    if security.high_count > 0:
        medium_priority.append(f"Fix {security.high_count} high-severity security issues")

    if performance.issues:
        perf_critical = [i for i in performance.issues if i.severity == "high"]
        if perf_critical:
            medium_priority.append(f"Optimize {len(perf_critical)} performance bottlenecks")

    if high_priority:
        print("\n  🔴 High Priority:")
        for item in high_priority:
            print(f"    - {item}")

    if medium_priority:
        print("\n  🟡 Medium Priority:")
        for item in medium_priority:
            print(f"    - {item}")

    print("\n✅ Review Complete!\n")

    return {
        "status": overall_status,
        "code_quality": review.overall_score,
        "security_score": 100 - security.risk_score,
        "performance_score": performance.overall_score,
        "total_issues": len(review.issues) + security.total_issues + len(performance.issues),
    }


async def batch_review(directory: str, pattern: str = "*.py"):
    """Review all files in a directory."""

    print(f"📁 Batch Code Review: {directory}")
    print(f"Pattern: {pattern}")
    print("="*60)

    files = list(Path(directory).rglob(pattern))
    print(f"\nFound {len(files)} files to review\n")

    results = []

    for file_path in files:
        try:
            result = await comprehensive_code_review(str(file_path))
            results.append({
                "file": str(file_path),
                **result
            })
        except Exception as e:
            print(f"❌ Error reviewing {file_path}: {e}")

    # Summary
    print("\n" + "="*60)
    print("📊 BATCH REVIEW SUMMARY")
    print("="*60)

    if results:
        passed = sum(1 for r in results if r["status"] == "PASS")
        avg_quality = sum(r["code_quality"] for r in results) / len(results)
        avg_security = sum(r["security_score"] for r in results) / len(results)
        avg_performance = sum(r["performance_score"] for r in results) / len(results)

        print(f"\nFiles Reviewed: {len(results)}")
        print(f"Passed: {passed}/{len(results)}")
        print(f"\nAverage Scores:")
        print(f"  - Code Quality: {avg_quality:.1f}/100")
        print(f"  - Security: {avg_security:.1f}/100")
        print(f"  - Performance: {avg_performance:.1f}/100")

        # Files needing attention
        needs_work = [r for r in results if r["status"] == "NEEDS WORK"]
        if needs_work:
            print(f"\n⚠️  Files Needing Attention:")
            for r in sorted(needs_work, key=lambda x: x["total_issues"], reverse=True):
                print(f"  - {r['file']} ({r['total_issues']} issues)")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        target = sys.argv[1]

        if Path(target).is_file():
            # Review single file
            asyncio.run(comprehensive_code_review(target))
        elif Path(target).is_dir():
            # Review directory
            asyncio.run(batch_review(target))
        else:
            print(f"❌ Invalid path: {target}")
    else:
        print("Usage: python 02_automated_code_review_workflow.py <file_or_directory>")
        print("\nExample:")
        print("  python 02_automated_code_review_workflow.py mycode.py")
        print("  python 02_automated_code_review_workflow.py ./src")
