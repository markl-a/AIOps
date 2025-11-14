# AIOps Framework

<div align="center">

**🤖 AI-Powered DevOps Automation Framework**

An intelligent, comprehensive framework for integrating LLMs and AI into DevOps workflows.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[Features](#features) • [Installation](#installation) • [Quick Start](#quick-start) • [Documentation](#documentation) • [Examples](#examples)

</div>

---

## 🎯 Overview

AIOps Framework is a production-ready, AI-powered DevOps automation platform that leverages Large Language Models (LLMs) to automate and enhance various DevOps tasks. Built with modern best practices from 2025, it supports multiple LLM providers and offers a comprehensive suite of intelligent agents.

### Why AIOps Framework?

- **🚀 Production-Ready**: Built with enterprise-grade architecture and error handling
- **🧩 Modular Design**: Use individual agents or the complete framework
- **🔌 Multi-LLM Support**: Works with OpenAI, Anthropic Claude, and more
- **📊 Comprehensive**: Covers code review, testing, CI/CD, monitoring, and more
- **🎨 Easy to Use**: Simple CLI, REST API, and Python SDK
- **🔒 Safe by Default**: Conservative auto-fix recommendations with rollback plans

---

## ✨ Features

### 🟢 **Basic Layer** - Foundation

#### 1. **Code Review Agent**
- Automated code review with security analysis
- Detects bugs, performance issues, and code smells
- Provides actionable suggestions and best practices
- Supports multiple programming languages

#### 2. **Test Generator Agent**
- Generates comprehensive unit, integration, and e2e tests
- Covers edge cases and error conditions
- Framework-agnostic (pytest, jest, junit, etc.)
- TDD-ready test generation from requirements

#### 3. **Log Analyzer Agent**
- Intelligent log analysis and root cause detection
- Error correlation and pattern recognition
- Anomaly detection in log streams
- Actionable troubleshooting recommendations

### 🟡 **Intermediate Layer** - Enhancement

#### 4. **CI/CD Optimizer Agent**
- Pipeline performance optimization
- Build failure analysis and quick fixes
- Parallelization opportunities identification
- Resource allocation recommendations

#### 5. **Documentation Generator Agent**
- Automated API and code documentation
- README generation for projects
- Docstring generation and updates
- Multiple documentation formats

#### 6. **Performance Analyzer Agent**
- Code performance analysis
- Algorithmic complexity detection
- Database query optimization
- Caching strategy recommendations

### 🔴 **Advanced Layer** - Intelligence

#### 7. **Anomaly Detector Agent**
- Real-time anomaly detection in metrics
- Time series analysis
- Predictive failure detection
- Baseline comparison and trend analysis

#### 8. **Auto-Fixer Agent**
- Automated issue resolution
- Self-healing recommendations
- Rollback plan generation
- Risk assessment for fixes

#### 9. **Intelligent Monitor Agent**
- Smart alerting with noise reduction
- Alert quality analysis
- Capacity planning insights
- Incident correlation

---

## 📦 Installation

### Prerequisites

- Python 3.9 or higher
- pip or poetry
- OpenAI API key or Anthropic API key

### Install from Source

```bash
# Clone the repository
git clone https://github.com/markl-a/AIOps.git
cd AIOps

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

### Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env
```

Required environment variables:
```env
OPENAI_API_KEY=your_openai_api_key_here
# OR
ANTHROPIC_API_KEY=your_anthropic_api_key_here

DEFAULT_LLM_PROVIDER=openai  # or anthropic
DEFAULT_MODEL=gpt-4-turbo-preview
```

---

## 🚀 Quick Start

### Using the CLI

```bash
# Code review
aiops review path/to/code.py --language python

# Generate tests
aiops generate-tests path/to/code.py --output tests/test_code.py

# Analyze logs
aiops analyze-logs logs/application.log

# Optimize CI/CD pipeline
aiops optimize-pipeline .github/workflows/ci.yml

# Generate documentation
aiops generate-docs path/to/code.py --output docs/

# Analyze performance
aiops analyze-performance path/to/code.py
```

### Using Python SDK

```python
import asyncio
from aiops.agents.code_reviewer import CodeReviewAgent

async def main():
    # Initialize agent
    agent = CodeReviewAgent()

    # Review code
    code = """
    def calculate_total(items):
        total = 0
        for i in range(len(items)):
            total += items[i]
        return total
    """

    result = await agent.execute(code=code, language="python")

    print(f"Score: {result.overall_score}/100")
    print(f"Summary: {result.summary}")

    for issue in result.issues:
        print(f"\n[{issue.severity}] {issue.description}")
        print(f"Suggestion: {issue.suggestion}")

asyncio.run(main())
```

### Using REST API

```bash
# Start the API server
python -m aiops.api.main

# Or with uvicorn
uvicorn aiops.api.main:app --host 0.0.0.0 --port 8000
```

```python
# Make API requests
import requests

response = requests.post(
    "http://localhost:8000/api/v1/code/review",
    json={
        "code": "def hello(): print('world')",
        "language": "python"
    }
)

result = response.json()
print(f"Score: {result['overall_score']}")
```

---

## 📚 Documentation

### Architecture

```
aiops/
├── core/              # Core functionality
│   ├── config.py      # Configuration management
│   ├── llm_factory.py # LLM provider abstraction
│   └── logger.py      # Logging setup
├── agents/            # AI agents
│   ├── code_reviewer.py
│   ├── test_generator.py
│   ├── log_analyzer.py
│   ├── cicd_optimizer.py
│   ├── doc_generator.py
│   ├── performance_analyzer.py
│   ├── anomaly_detector.py
│   ├── auto_fixer.py
│   └── intelligent_monitor.py
├── api/               # REST API
│   └── main.py
├── cli/               # Command-line interface
│   └── main.py
└── examples/          # Usage examples
    ├── basic_usage.py
    └── advanced_usage.py
```

### Agent Usage Patterns

#### Basic Pattern

```python
from aiops.agents.{agent_name} import {AgentClass}

# Initialize agent
agent = AgentClass(
    llm_provider="openai",  # or "anthropic"
    model="gpt-4-turbo-preview",
    temperature=0.7
)

# Execute agent
result = await agent.execute(
    # Agent-specific parameters
)
```

#### Configuration

```python
from aiops.core.config import get_config

config = get_config()
config.default_llm_provider = "anthropic"
config.default_model = "claude-3-5-sonnet-20241022"
```

---

## 💡 Examples

### Example 1: Automated Code Review in CI/CD

```yaml
# .github/workflows/ai-review.yml
name: AI Code Review

on: [pull_request]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
      - name: Install AIOps
        run: pip install aiops-framework
      - name: Review Changes
        run: |
          git diff origin/main...HEAD > changes.diff
          aiops review changes.diff --language python
```

### Example 2: Automated Test Generation

```python
from aiops.agents.test_generator import TestGeneratorAgent

async def generate_tests_for_project():
    agent = TestGeneratorAgent()

    # Generate from code
    with open("src/calculator.py") as f:
        code = f.read()

    result = await agent.execute(code=code, language="python")

    # Save tests
    with open("tests/test_calculator.py", "w") as f:
        if result.setup_code:
            f.write(result.setup_code + "\n\n")
        for test in result.test_cases:
            f.write(f"{test.test_code}\n\n")
```

### Example 3: Intelligent Monitoring

```python
from aiops.agents.intelligent_monitor import IntelligentMonitorAgent

async def monitor_system():
    agent = IntelligentMonitorAgent()

    # Current metrics
    metrics = {
        "cpu_usage": 85.2,
        "memory_usage": 92.1,
        "error_rate": 5.2,
        "response_time_ms": 1200
    }

    # Historical baseline
    baseline = {
        "cpu_usage": 45.0,
        "memory_usage": 60.0,
        "error_rate": 0.5,
        "response_time_ms": 200
    }

    result = await agent.execute(
        metrics=metrics,
        historical_data=baseline
    )

    print(f"Health: {result.overall_health}")
    print(f"Score: {result.health_score}/100")

    # Process alerts
    for alert in result.alerts:
        if alert.severity in ["critical", "high"]:
            send_alert(alert)
```

### Example 4: Auto-Fix with Safety

```python
from aiops.agents.auto_fixer import AutoFixerAgent

async def auto_fix_issue():
    agent = AutoFixerAgent()

    result = await agent.execute(
        issue_description="High memory usage causing OOM",
        logs=error_logs,
        system_state={"memory_limit": "512Mi"},
        auto_apply=False  # Require approval
    )

    fix = result.recommended_fix

    if fix.risk_level == "low" and fix.confidence > 80:
        print(f"Safe fix available: {fix.description}")
        print("Commands:")
        for cmd in fix.commands:
            print(f"  {cmd}")

        if approve_fix():
            execute_fix(fix.commands)
    else:
        print("Manual review required")
```

---

## 🔧 Advanced Usage

### Custom Agents

```python
from aiops.agents.base_agent import BaseAgent

class CustomAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(name="CustomAgent", **kwargs)

    async def execute(self, *args, **kwargs):
        # Your custom logic
        prompt = "Your custom prompt"
        system_prompt = "Your system prompt"

        response = await self._generate_response(
            prompt=prompt,
            system_prompt=system_prompt
        )

        return response
```

### Multiple LLM Providers

```python
from aiops.core.llm_factory import LLMFactory

# Use different providers for different tasks
code_review_llm = LLMFactory.create(provider="anthropic", model="claude-3-5-sonnet-20241022")
test_gen_llm = LLMFactory.create(provider="openai", model="gpt-4-turbo-preview")
```

### Batch Processing

```python
import asyncio
from aiops.agents.code_reviewer import CodeReviewAgent

async def review_multiple_files(files):
    agent = CodeReviewAgent()

    tasks = [
        agent.execute(code=read_file(f), language="python")
        for f in files
    ]

    results = await asyncio.gather(*tasks)
    return results
```

---

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit your changes**: `git commit -m 'Add amazing feature'`
4. **Push to the branch**: `git push origin feature/amazing-feature`
5. **Open a Pull Request**

### Development Setup

```bash
# Clone your fork
git clone https://github.com/your-username/AIOps.git
cd AIOps

# Install development dependencies
pip install -r requirements.txt
pip install -e ".[dev]"

# Run tests
pytest

# Run linters
black aiops/
flake8 aiops/
mypy aiops/
```

---

## 📊 Roadmap

- [x] Core framework and agents
- [x] CLI tool
- [x] REST API
- [x] Multi-LLM support
- [ ] Web dashboard
- [ ] GitHub Actions integration
- [ ] Slack/Discord notifications
- [ ] Prometheus metrics
- [ ] Plugin system
- [ ] More LLM providers (DeepSeek, local models)

---

## 🙏 Acknowledgments

This framework is built using:
- [LangChain](https://github.com/langchain-ai/langchain) - LLM orchestration
- [FastAPI](https://fastapi.tiangolo.com/) - API framework
- [Typer](https://typer.tiangolo.com/) - CLI framework
- [Rich](https://rich.readthedocs.io/) - Terminal formatting

Inspired by:
- Modern AIOps and LLMOps best practices
- Research on AI-powered DevOps automation
- Community feedback and contributions

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 📞 Contact & Support

- **Issues**: [GitHub Issues](https://github.com/markl-a/AIOps/issues)
- **Discussions**: [GitHub Discussions](https://github.com/markl-a/AIOps/discussions)
- **Email**: support@aiops.dev

---

<div align="center">

**Made with ❤️ by the AIOps Team**

[⬆ Back to Top](#aiops-framework)

</div>
