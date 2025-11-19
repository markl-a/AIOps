#!/usr/bin/env python3
"""
Setup Verification Script

Verifies that the AIOps project is properly set up and ready for development.
Run this after initial setup to ensure everything is configured correctly.
"""

import sys
import os
from pathlib import Path
from typing import List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(Colors.BLUE + "=" * 70 + Colors.RESET)


def print_check(passed: bool, message: str):
    if passed:
        print(f"{Colors.GREEN}✓{Colors.RESET} {message}")
    else:
        print(f"{Colors.RED}✗{Colors.RESET} {message}")


def print_info(message: str):
    print(f"  {message}")


def check_project_structure() -> Tuple[int, int]:
    """Check project directory structure"""
    print_header("Project Structure")

    required_dirs = [
        "aiops",
        "aiops/agents",
        "aiops/api",
        "aiops/api/routes",
        "aiops/core",
        "aiops/database",
        "aiops/integrations",
        "aiops/plugins",
        "aiops/webhooks",
        "aiops/observability",
        "aiops/cache",
        "aiops/cli",
        "aiops/tests",
        "aiops/examples",
        "k8s",
        "monitoring",
        "docs",
        "scripts",
    ]

    passed = 0
    failed = 0

    for dir_name in required_dirs:
        dir_path = project_root / dir_name
        if dir_path.exists() and dir_path.is_dir():
            print_check(True, f"{dir_name}/")
            passed += 1
        else:
            print_check(False, f"{dir_name}/ (missing)")
            failed += 1

    return passed, failed


def check_configuration_files() -> Tuple[int, int]:
    """Check configuration files"""
    print_header("Configuration Files")

    files = [
        ("requirements.txt", "Python dependencies"),
        ("docker-compose.yml", "Docker Compose config"),
        ("Dockerfile", "Docker image config"),
        ("Makefile", "Build automation"),
        (".env.example", "Environment variables template"),
        ("README.md", "Documentation"),
        ("pyproject.toml", "Python project config (optional)"),
    ]

    passed = 0
    failed = 0

    for file_name, description in files:
        file_path = project_root / file_name
        if file_path.exists():
            print_check(True, f"{file_name} - {description}")
            passed += 1
        else:
            print_check(False, f"{file_name} - {description}")
            if not file_name.startswith("pyproject"):
                failed += 1

    return passed, failed


def check_core_modules() -> Tuple[int, int]:
    """Check core module files"""
    print_header("Core Modules")

    modules = [
        "aiops/core/llm_providers.py",
        "aiops/core/llm_config.py",
        "aiops/core/structured_logger.py",
        "aiops/core/exceptions.py",
        "aiops/core/error_handler.py",
        "aiops/database/base.py",
        "aiops/database/models.py",
        "aiops/observability/metrics.py",
        "aiops/observability/tracing.py",
        "aiops/cache/redis_cache.py",
    ]

    passed = 0
    failed = 0

    for module in modules:
        module_path = project_root / module
        if module_path.exists():
            print_check(True, module)
            passed += 1
        else:
            print_check(False, f"{module} (missing)")
            failed += 1

    return passed, failed


def check_environment_setup() -> Tuple[int, int]:
    """Check environment setup"""
    print_header("Environment Setup")

    env_file = project_root / ".env"
    env_example = project_root / ".env.example"

    if env_file.exists():
        print_check(True, ".env file exists")
        print_info("Environment variables are configured")
        return 1, 0
    elif env_example.exists():
        print_check(False, ".env file not found")
        print_info("Copy .env.example to .env and configure your variables")
        print_info("Command: cp .env.example .env")
        return 0, 1
    else:
        print_check(False, "No environment configuration found")
        return 0, 1


def check_git_setup() -> Tuple[int, int]:
    """Check Git setup"""
    print_header("Git Setup")

    git_dir = project_root / ".git"

    if git_dir.exists():
        print_check(True, "Git repository initialized")

        # Check if there's a remote
        import subprocess
        try:
            result = subprocess.run(
                ["git", "remote", "-v"],
                cwd=project_root,
                capture_output=True,
                text=True
            )
            if result.stdout.strip():
                print_check(True, "Git remote configured")
                return 2, 0
            else:
                print_check(False, "No Git remote configured")
                print_info("Add a remote: git remote add origin <url>")
                return 1, 1
        except Exception:
            return 1, 0
    else:
        print_check(False, "Git repository not initialized")
        print_info("Initialize: git init")
        return 0, 1


def check_docker_setup() -> Tuple[int, int]:
    """Check Docker setup"""
    print_header("Docker Setup")

    import subprocess

    # Check Docker
    try:
        subprocess.run(["docker", "--version"], capture_output=True, check=True)
        print_check(True, "Docker is installed")
        docker_ok = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_check(False, "Docker is not installed")
        docker_ok = False

    # Check Docker Compose
    try:
        subprocess.run(["docker-compose", "--version"], capture_output=True, check=True)
        print_check(True, "Docker Compose is installed")
        compose_ok = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            subprocess.run(["docker", "compose", "version"], capture_output=True, check=True)
            print_check(True, "Docker Compose (V2) is installed")
            compose_ok = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print_check(False, "Docker Compose is not installed")
            compose_ok = False

    passed = (1 if docker_ok else 0) + (1 if compose_ok else 0)
    failed = (0 if docker_ok else 1) + (0 if compose_ok else 1)

    return passed, failed


def print_next_steps():
    """Print recommended next steps"""
    print_header("Next Steps")

    steps = [
        "1. Copy environment template: cp .env.example .env",
        "2. Configure environment variables in .env",
        "3. Install Python dependencies: pip install -r requirements.txt",
        "4. Start services: make docker-up (or docker-compose up -d)",
        "5. Run migrations: make db-migrate",
        "6. Run validation: python scripts/validate_system.py",
        "7. Start API server: make dev (or uvicorn aiops.api.app:app --reload)",
        "8. Check API docs: http://localhost:8000/docs",
        "9. Run tests: make test (or pytest)",
        "10. Explore examples: ls aiops/examples/",
    ]

    for step in steps:
        print(f"  {step}")


def main():
    """Run setup verification"""
    print(f"\n{Colors.BOLD}🔧 AIOps Setup Verification{Colors.RESET}")
    print(f"{Colors.BOLD}Checking project setup and configuration...{Colors.RESET}")

    total_passed = 0
    total_failed = 0

    # Run checks
    checks = [
        check_project_structure,
        check_configuration_files,
        check_core_modules,
        check_environment_setup,
        check_git_setup,
        check_docker_setup,
    ]

    for check_func in checks:
        passed, failed = check_func()
        total_passed += passed
        total_failed += failed

    # Summary
    print_header("Setup Summary")

    total = total_passed + total_failed
    print(f"Total Checks: {total}")
    print(f"{Colors.GREEN}Passed: {total_passed}{Colors.RESET}")

    if total_failed > 0:
        print(f"{Colors.RED}Failed: {total_failed}{Colors.RESET}")

    success_rate = (total_passed / total * 100) if total > 0 else 0
    print(f"\nSetup Completeness: {success_rate:.1f}%")

    if total_failed == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ Setup verification passed!{Colors.RESET}")
        print(f"{Colors.GREEN}Project is properly set up.{Colors.RESET}")
        print_next_steps()
        return 0
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠ Setup incomplete{Colors.RESET}")
        print(f"{Colors.YELLOW}Some components are missing or not configured.{Colors.RESET}")
        print_next_steps()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
