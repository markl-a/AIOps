#!/usr/bin/env python3
"""
AIOps System Validation Script

Comprehensive validation of the AIOps system setup including:
- Environment variables
- Python dependencies
- Database connectivity
- Redis connectivity
- LLM providers
- AI agents
- Plugin system
- Webhook handlers
- API health
"""

import sys
import os
import asyncio
from typing import Dict, List, Tuple
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class Colors:
    """Terminal colors for output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓{Colors.RESET} {text}")


def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}✗{Colors.RESET} {text}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {text}")


def print_info(text: str):
    """Print info message"""
    print(f"  {text}")


def check_environment_variables() -> Tuple[int, int]:
    """Check environment variables"""
    print_header("Environment Variables")

    required_vars = []  # No strictly required vars
    optional_vars = [
        ("OPENAI_API_KEY", "OpenAI LLM provider"),
        ("ANTHROPIC_API_KEY", "Anthropic Claude provider"),
        ("GOOGLE_API_KEY", "Google Gemini provider"),
        ("DATABASE_URL", "PostgreSQL database"),
        ("REDIS_URL", "Redis cache"),
        ("SLACK_WEBHOOK_URL", "Slack notifications"),
        ("TEAMS_WEBHOOK_URL", "Microsoft Teams notifications"),
        ("GITHUB_WEBHOOK_SECRET", "GitHub webhook verification"),
        ("GITLAB_WEBHOOK_SECRET", "GitLab webhook verification"),
        ("JIRA_WEBHOOK_SECRET", "Jira webhook verification"),
        ("PAGERDUTY_WEBHOOK_SECRET", "PagerDuty webhook verification"),
        ("SENTRY_DSN", "Error tracking"),
    ]

    passed = 0
    failed = 0

    # Check required
    for var in required_vars:
        if os.getenv(var):
            print_success(f"{var} is set")
            passed += 1
        else:
            print_error(f"{var} is not set (REQUIRED)")
            failed += 1

    # Check optional
    for var, description in optional_vars:
        if os.getenv(var):
            print_success(f"{var} is set - {description}")
            passed += 1
        else:
            print_warning(f"{var} is not set - {description} (optional)")

    return passed, failed


def check_python_dependencies() -> Tuple[int, int]:
    """Check Python dependencies"""
    print_header("Python Dependencies")

    dependencies = [
        ("fastapi", "FastAPI web framework"),
        ("uvicorn", "ASGI server"),
        ("pydantic", "Data validation"),
        ("sqlalchemy", "Database ORM"),
        ("redis", "Redis client"),
        ("celery", "Task queue"),
        ("openai", "OpenAI client"),
        ("anthropic", "Anthropic client"),
        ("google.generativeai", "Google Gemini client"),
        ("prometheus_client", "Metrics"),
        ("opentelemetry", "Tracing"),
        ("aiohttp", "Async HTTP client"),
        ("click", "CLI framework"),
        ("rich", "Terminal formatting"),
        ("pytest", "Testing framework"),
    ]

    passed = 0
    failed = 0

    for package, description in dependencies:
        try:
            __import__(package.split(".")[0])
            print_success(f"{package} - {description}")
            passed += 1
        except ImportError:
            print_error(f"{package} - {description}")
            failed += 1

    return passed, failed


async def check_database_connectivity() -> Tuple[int, int]:
    """Check database connectivity"""
    print_header("Database Connectivity")

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print_warning("DATABASE_URL not set, skipping database check")
        return 0, 0

    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.pool import NullPool

        engine = create_engine(database_url, poolclass=NullPool)

        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()

        print_success("PostgreSQL connection successful")
        print_info(f"Database URL: {database_url.split('@')[1] if '@' in database_url else 'local'}")

        engine.dispose()
        return 1, 0

    except Exception as e:
        print_error(f"PostgreSQL connection failed: {e}")
        return 0, 1


async def check_redis_connectivity() -> Tuple[int, int]:
    """Check Redis connectivity"""
    print_header("Redis Connectivity")

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    try:
        import redis.asyncio as aioredis

        redis_client = await aioredis.from_url(redis_url)
        await redis_client.ping()

        print_success("Redis connection successful")
        print_info(f"Redis URL: {redis_url}")

        await redis_client.close()
        return 1, 0

    except Exception as e:
        print_error(f"Redis connection failed: {e}")
        print_info("Redis is optional but recommended for caching")
        return 0, 0  # Redis is optional


async def check_llm_providers() -> Tuple[int, int]:
    """Check LLM provider availability"""
    print_header("LLM Providers")

    passed = 0
    failed = 0

    # OpenAI
    if os.getenv("OPENAI_API_KEY"):
        try:
            import openai
            openai.api_key = os.getenv("OPENAI_API_KEY")
            print_success("OpenAI API key configured")
            passed += 1
        except Exception as e:
            print_error(f"OpenAI configuration failed: {e}")
            failed += 1
    else:
        print_warning("OpenAI API key not set")

    # Anthropic
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            import anthropic
            print_success("Anthropic API key configured")
            passed += 1
        except Exception as e:
            print_error(f"Anthropic configuration failed: {e}")
            failed += 1
    else:
        print_warning("Anthropic API key not set")

    # Google
    if os.getenv("GOOGLE_API_KEY"):
        try:
            import google.generativeai as genai
            print_success("Google Gemini API key configured")
            passed += 1
        except Exception as e:
            print_error(f"Google configuration failed: {e}")
            failed += 1
    else:
        print_warning("Google API key not set")

    if passed == 0:
        print_warning("No LLM providers configured - at least one is recommended")

    return passed, failed


def check_ai_agents() -> Tuple[int, int]:
    """Check AI agents can be imported"""
    print_header("AI Agents")

    agents = [
        "BaseAgent",
        "CodeReviewAgent",
        "TestGeneratorAgent",
        "SecurityScannerAgent",
        "KubernetesOptimizerAgent",
        "IncidentResponseAgent",
        "ComplianceCheckerAgent",
        "MigrationPlannerAgent",
        "ReleaseManagerAgent",
    ]

    passed = 0
    failed = 0

    try:
        import aiops.agents as agent_module

        for agent_name in agents:
            if hasattr(agent_module, agent_name):
                print_success(f"{agent_name} available")
                passed += 1
            else:
                print_error(f"{agent_name} not found")
                failed += 1

    except Exception as e:
        print_error(f"Failed to import agents: {e}")
        failed = len(agents)

    return passed, failed


def check_plugin_system() -> Tuple[int, int]:
    """Check plugin system"""
    print_header("Plugin System")

    try:
        from aiops.plugins import (
            Plugin,
            AgentPlugin,
            IntegrationPlugin,
            PluginManager,
            get_plugin_manager,
        )

        print_success("Plugin system imported successfully")
        print_info("Plugin classes: Plugin, AgentPlugin, IntegrationPlugin")
        print_info("Plugin manager available")

        return 1, 0

    except Exception as e:
        print_error(f"Plugin system check failed: {e}")
        return 0, 1


def check_webhook_handlers() -> Tuple[int, int]:
    """Check webhook handlers"""
    print_header("Webhook Handlers")

    handlers = [
        ("GitHubWebhookHandler", "GitHub"),
        ("GitLabWebhookHandler", "GitLab"),
        ("JiraWebhookHandler", "Jira"),
        ("PagerDutyWebhookHandler", "PagerDuty"),
    ]

    passed = 0
    failed = 0

    try:
        from aiops.webhooks import (
            WebhookHandler,
            WebhookRouter,
            GitHubWebhookHandler,
            GitLabWebhookHandler,
            JiraWebhookHandler,
            PagerDutyWebhookHandler,
        )

        for handler_name, service in handlers:
            print_success(f"{handler_name} - {service} webhooks")
            passed += 1

        print_info("WebhookRouter available for event routing")

    except Exception as e:
        print_error(f"Webhook handlers check failed: {e}")
        failed = len(handlers)

    return passed, failed


def check_api_structure() -> Tuple[int, int]:
    """Check API structure"""
    print_header("API Structure")

    api_files = [
        ("aiops/api/app.py", "Main FastAPI application"),
        ("aiops/api/routes/agents.py", "Agent execution routes"),
        ("aiops/api/routes/llm.py", "LLM management routes"),
        ("aiops/api/routes/notifications.py", "Notification routes"),
        ("aiops/api/routes/analytics.py", "Analytics routes"),
        ("aiops/api/routes/webhooks.py", "Webhook routes"),
    ]

    passed = 0
    failed = 0

    for file_path, description in api_files:
        full_path = project_root / file_path
        if full_path.exists():
            print_success(f"{description}")
            passed += 1
        else:
            print_error(f"{description} - File not found: {file_path}")
            failed += 1

    return passed, failed


def check_examples() -> Tuple[int, int]:
    """Check examples"""
    print_header("Examples")

    examples_dir = project_root / "aiops" / "examples"

    if not examples_dir.exists():
        print_error("Examples directory not found")
        return 0, 1

    examples = list(examples_dir.glob("*.py"))

    print_success(f"Found {len(examples)} example files")

    for example in sorted(examples)[:5]:  # Show first 5
        print_info(f"  • {example.name}")

    if len(examples) > 5:
        print_info(f"  ... and {len(examples) - 5} more")

    return 1, 0


async def main():
    """Run all validation checks"""
    print(f"\n{Colors.BOLD}🔍 AIOps System Validation{Colors.RESET}")
    print(f"{Colors.BOLD}Starting comprehensive system validation...{Colors.RESET}")

    total_passed = 0
    total_failed = 0

    # Run all checks
    checks = [
        ("Environment Variables", check_environment_variables),
        ("Python Dependencies", check_python_dependencies),
        ("Database Connectivity", check_database_connectivity),
        ("Redis Connectivity", check_redis_connectivity),
        ("LLM Providers", check_llm_providers),
        ("AI Agents", check_ai_agents),
        ("Plugin System", check_plugin_system),
        ("Webhook Handlers", check_webhook_handlers),
        ("API Structure", check_api_structure),
        ("Examples", check_examples),
    ]

    for name, check_func in checks:
        if asyncio.iscoroutinefunction(check_func):
            passed, failed = await check_func()
        else:
            passed, failed = check_func()

        total_passed += passed
        total_failed += failed

    # Summary
    print_header("Validation Summary")

    total_checks = total_passed + total_failed

    print(f"Total Checks: {total_checks}")
    print(f"{Colors.GREEN}Passed: {total_passed}{Colors.RESET}")

    if total_failed > 0:
        print(f"{Colors.RED}Failed: {total_failed}{Colors.RESET}")
    else:
        print(f"Failed: {total_failed}")

    success_rate = (total_passed / total_checks * 100) if total_checks > 0 else 0

    print(f"\n{Colors.BOLD}Success Rate: {success_rate:.1f}%{Colors.RESET}")

    if total_failed == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ All validation checks passed!{Colors.RESET}")
        print(f"{Colors.GREEN}AIOps system is properly configured and ready to use.{Colors.RESET}")
        return 0
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠ Some checks failed{Colors.RESET}")
        print(f"{Colors.YELLOW}Review the errors above and fix configuration issues.{Colors.RESET}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
