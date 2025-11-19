# AIOps Framework

<div align="center">

**🤖 Enterprise-Grade AI-Powered DevOps Automation Platform**

A production-ready, comprehensive framework for integrating LLMs and AI into DevOps workflows with multi-provider support, advanced monitoring, and extensible architecture.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Test Coverage](https://img.shields.io/badge/coverage-75%25-brightgreen.svg)]()
[![Production Ready](https://img.shields.io/badge/status-production--ready-success.svg)]()

[Features](#-features) • [Installation](#-installation) • [Quick Start](#-quick-start) • [API Reference](#-api-reference) • [Examples](#-examples) • [Documentation](#-documentation)

</div>

---

## 🎯 Overview

AIOps Framework is a **production-ready, enterprise-grade** platform that leverages Large Language Models (LLMs) to automate and enhance DevOps workflows. Built with modern best practices, it provides comprehensive tooling for code review, security analysis, testing, deployment, monitoring, and more.

### 🌟 What Makes AIOps Special?

- **🚀 Production-Ready**: Enterprise architecture with comprehensive error handling, monitoring, and observability
- **🔄 Multi-LLM Support**: Automatic failover between OpenAI, Anthropic, and Google Gemini
- **🧪 75% Test Coverage**: Extensive test suite with unit, integration, and E2E tests
- **📊 Full Observability**: OpenTelemetry tracing, Prometheus metrics, and structured logging
- **🔌 Extensible**: Plugin system for custom agents and integrations
- **🌐 REST API**: Comprehensive FastAPI-based API for all functionality
- **🔔 Multi-Channel Notifications**: Slack, Microsoft Teams, and more
- **☸️ Kubernetes-Ready**: Complete K8s manifests, HPA, and monitoring
- **📚 13+ Examples**: Production-ready examples for common use cases

---

## ✨ Features

### 🤖 AI Agents (26 Specialized Agents)

#### Code Quality & Security
- **Code Reviewer**: Automated code review with quality scoring
- **Security Scanner**: OWASP Top 10 vulnerability detection
- **Test Generator**: Unit, integration, and E2E test generation
- **Documentation Generator**: Automated API and code documentation
- **Performance Analyzer**: Code performance optimization

#### Infrastructure & DevOps
- **Kubernetes Optimizer**: Resource optimization and cost reduction
- **Cost Optimizer**: Cloud infrastructure cost analysis
- **CI/CD Optimizer**: Pipeline performance optimization
- **Disaster Recovery Planner**: DR plan generation and validation
- **Auto-Scaler**: Intelligent scaling recommendations

#### Monitoring & Analytics
- **Log Analyzer**: Intelligent log analysis and root cause detection
- **Anomaly Detector**: Real-time anomaly detection in metrics
- **Performance Monitor**: System performance tracking
- **Alert Manager**: Smart alerting with noise reduction

### 🔄 LLM Provider Management

- **Multi-Provider Support**: OpenAI, Anthropic Claude, Google Gemini
- **Automatic Failover**: Seamless switching between providers
- **Health Monitoring**: Real-time provider health checks
- **Cost Tracking**: Per-provider and per-agent cost analytics
- **Rate Limit Handling**: Intelligent rate limit management
- **Configurable Priority**: Custom provider ordering

### 🌐 REST API

Comprehensive FastAPI-based REST API with:
- **Agent Execution**: Sync and async agent execution
- **LLM Management**: Provider health, statistics, and generation
- **Notifications**: Multi-channel notification sending
- **Analytics**: System metrics, cost breakdowns, usage trends
- **Health Checks**: Kubernetes liveness and readiness probes
- **OpenAPI/Swagger**: Auto-generated API documentation

### 📊 Observability & Monitoring

- **OpenTelemetry Tracing**: Distributed tracing across all components
- **Prometheus Metrics**: 60+ custom metrics for monitoring
- **Structured Logging**: JSON logs with trace IDs and context
- **Grafana Dashboards**: Pre-built dashboards for visualization
- **Sentry Integration**: Error tracking and reporting

### 🔔 Integrations

- **Slack**: Webhook and bot API support with rich formatting
- **Microsoft Teams**: Adaptive Cards for beautiful notifications
- **GitHub Actions**: Complete CI/CD workflow integration
- **Kubernetes**: Full deployment configs with HPA and monitoring
- **PostgreSQL**: Persistent data storage with migrations
- **Celery**: Async task queue for background processing
- **Redis**: Caching and session management

### 🔌 Plugin System

- **Extensible Architecture**: Add custom agents and integrations
- **Plugin Types**: Agent, Integration, and general-purpose plugins
- **Lifecycle Management**: Initialize, execute, and cleanup hooks
- **Dynamic Loading**: Load plugins at runtime
- **Enable/Disable**: Toggle plugins without restart

### 📦 Production Features

- **Database Support**: PostgreSQL with SQLAlchemy ORM
- **Task Queue**: Celery with Redis broker
- **Caching**: Redis caching layer
- **Authentication**: JWT-based auth (ready to integrate)
- **Rate Limiting**: Per-user and global rate limits
- **Health Checks**: Comprehensive health monitoring
- **Error Recovery**: Automatic retry with exponential backoff
- **Graceful Degradation**: Continue operating with partial failures

---

## 📦 Installation

### Prerequisites

- Python 3.10 or higher
- PostgreSQL 13+ (for production)
- Redis 6+ (for caching and tasks)
- Docker & Kubernetes (optional, for deployment)

### Quick Install

```bash
# Clone the repository
git clone https://github.com/your-org/AIOps.git
cd AIOps

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Environment Variables

```bash
# LLM Providers (at least one required)
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
GOOGLE_API_KEY=your-google-key

# Provider Priority (optional)
LLM_PROVIDER_PRIORITY=openai,anthropic,google

# Database (optional, uses SQLite by default)
DATABASE_URL=postgresql://user:pass@localhost:5432/aiops

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# Notifications (optional)
SLACK_WEBHOOK_URL=your-slack-webhook
TEAMS_WEBHOOK_URL=your-teams-webhook

# Monitoring (optional)
SENTRY_DSN=your-sentry-dsn
```

---

## 🚀 Quick Start

### 1. Command Line Usage

```bash
# Run code review
python -m aiops.cli review --file src/main.py

# Generate tests
python -m aiops.cli generate-tests --file src/utils.py

# Analyze security
python -m aiops.cli security-scan --directory src/

# Optimize Kubernetes
python -m aiops.cli optimize-k8s --manifest k8s/deployment.yaml
```

### 2. Python API

```python
from aiops.agents import CodeReviewAgent

# Initialize agent
agent = CodeReviewAgent()

# Review code
result = await agent.execute(code="""
def calculate_total(items):
    total = sum(items)
    return total
""")

print(f"Quality Score: {result.score}/100")
print(f"Issues Found: {len(result.issues)}")
```

### 3. REST API

```bash
# Start the API server
python -m aiops.api.app

# API will be available at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

```bash
# Execute agent via API
curl -X POST http://localhost:8000/api/v1/agents/execute \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "code_reviewer",
    "input_data": {"code": "def hello(): return \"world\""}
  }'
```

### 4. LLM Failover Example

```python
from aiops.core.llm_config import load_config_from_env
from aiops.core.llm_config import create_llm_manager_from_config

# Load configuration
config = load_config_from_env()

# Create manager with automatic failover
manager = create_llm_manager_from_config(config)

# Generate text (automatically fails over if primary provider fails)
result, provider = await manager.generate(
    prompt="Explain what is AIOps",
    max_tokens=100,
)

print(f"Response from {provider}: {result}")
```

### 5. Plugin System

```python
from aiops.plugins import AgentPlugin, get_plugin_manager

# Create custom agent plugin
class CustomAnalyzer(AgentPlugin):
    def get_agent_type(self) -> str:
        return "custom_analyzer"

    async def analyze(self, input_data):
        # Your custom analysis logic
        return {"result": "analysis complete"}

# Load and use plugin
manager = get_plugin_manager()
await manager.load_plugin(CustomAnalyzer)
result = await manager.execute_plugin("CustomAnalyzer", input_data={})
```

---

## 📚 Examples

The framework includes **13 comprehensive examples** in `aiops/examples/`:

1. **GitHub Actions Integration** - Automated PR review workflow
2. **Automated Code Review** - Multi-agent review pipeline
3. **Security Audit Pipeline** - Complete security scanning
4. **Kubernetes Cost Optimization** - Resource and cost optimization
5. **Test Generation Automation** - Automated test creation
6. **Performance Optimization** - Performance analysis guide
7. **Monitoring and Alerting** - Integration with monitoring systems
8. **Disaster Recovery** - DR planning and backup validation
9. **Multi-Environment Deployment** - Dev/Staging/Production workflows
10. **Complete CI/CD Pipeline** - End-to-end pipeline with GitHub Actions
11. **LLM Failover** - Multi-provider failover demonstration
12. **Slack/Teams Integration** - Notification examples
13. **Plugin System** - Custom plugin creation guide

Run any example:
```bash
python aiops/examples/01_github_actions_integration.py
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        REST API Layer (FastAPI)                  │
│  /agents • /llm • /notifications • /analytics • /health         │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────────┐
│                     LLM Provider Manager                          │
│  Multi-Provider Failover • Health Monitoring • Cost Tracking    │
│  OpenAI • Anthropic • Google Gemini                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────────┐
│                      AI Agent Layer (26 Agents)                   │
│  Code • Security • Testing • Infrastructure • Monitoring         │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────────┐
│                    Core Services & Infrastructure                │
│  Database • Cache • Task Queue • Logging • Metrics • Tracing    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Monitoring & Metrics

### Prometheus Metrics

The framework exports 60+ metrics including:

```prometheus
# Agent Execution
aiops_agent_executions_total{agent_type, status}
aiops_agent_execution_duration_seconds{agent_type}

# LLM Usage
aiops_llm_requests_total{provider, model, status}
aiops_llm_tokens_total{provider, model, type}
aiops_llm_cost_total{provider, model}

# System Metrics
aiops_http_requests_total{method, endpoint, status_code}
aiops_http_request_duration_seconds{method, endpoint}
aiops_cache_hits_total{cache_type}
```

### Grafana Dashboards

Pre-built dashboards available in `monitoring/grafana/`:
- System Overview
- LLM Provider Health
- Agent Performance
- Cost Analysis
- Error Tracking

---

## 🔧 Configuration

### LLM Provider Configuration

```python
from aiops.core.llm_config import LLMConfig, ProviderConfig, ProviderType

config = LLMConfig(
    providers=[
        ProviderConfig(
            type=ProviderType.OPENAI,
            api_key_env="OPENAI_API_KEY",
            priority=3,  # Highest priority
            max_retries=3,
            timeout=30.0,
        ),
        ProviderConfig(
            type=ProviderType.ANTHROPIC,
            api_key_env="ANTHROPIC_API_KEY",
            priority=2,  # Fallback
        ),
    ],
    failover_enabled=True,
    health_check_interval=60,
)
```

### Notification Configuration

```python
from aiops.integrations import NotificationManager, NotificationChannel

manager = NotificationManager()

# Register channels
manager.register_channel(NotificationChannel.SLACK, slack_client)
manager.register_channel(NotificationChannel.TEAMS, teams_client)

# Send notification
await manager.send_alert(
    title="Deployment Complete",
    message="Application deployed successfully",
    level=NotificationLevel.SUCCESS,
    channels=[NotificationChannel.SLACK, NotificationChannel.TEAMS],
)
```

---

## ☸️ Kubernetes Deployment

### Quick Deploy

```bash
# Create namespace
kubectl create namespace aiops

# Deploy PostgreSQL
kubectl apply -f k8s/base/postgres.yaml

# Deploy Redis
kubectl apply -f k8s/base/redis.yaml

# Deploy AIOps API
kubectl apply -f k8s/base/deployment.yaml
kubectl apply -f k8s/base/service.yaml
kubectl apply -f k8s/base/hpa.yaml

# Deploy monitoring
kubectl apply -f k8s/monitoring/
```

### Helm Chart (Coming Soon)

```bash
helm install aiops ./helm/aiops \
  --set image.tag=1.0.0 \
  --set llm.openai.apiKey=$OPENAI_API_KEY \
  --set ingress.enabled=true
```

---

## 📖 Documentation

Comprehensive documentation available in `docs/`:

- **[Deployment Guide](docs/DEPLOYMENT.md)** - Complete deployment instructions
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Best Practices](docs/BEST_PRACTICES.md)** - Architecture and operational guidelines
- **[API Reference](http://localhost:8000/docs)** - Auto-generated OpenAPI docs

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=aiops --cov-report=html

# Run specific test suite
pytest aiops/tests/test_llm_failover.py

# Run integration tests
pytest aiops/tests/integration/ -v

# Run with real LLM providers (requires API keys)
pytest --run-integration
```

**Test Coverage**: 75%+
- Unit Tests: 300+ test cases
- Integration Tests: 50+ scenarios
- E2E Tests: 20+ workflows

---

## 🤝 Contributing

Contributions are welcome! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run linters
black aiops/
flake8 aiops/
mypy aiops/

# Run tests
pytest
```

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Built with:
- [OpenAI](https://openai.com/) - GPT models
- [Anthropic](https://anthropic.com/) - Claude models
- [Google](https://ai.google.dev/) - Gemini models
- [FastAPI](https://fastapi.tiangolo.com/) - REST API framework
- [LangChain](https://langchain.com/) - LLM orchestration
- [OpenTelemetry](https://opentelemetry.io/) - Observability
- [Prometheus](https://prometheus.io/) - Metrics and monitoring

---

## 📞 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/your-org/AIOps/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/AIOps/discussions)

---

<div align="center">

**⭐ Star this repo if you find it useful!**

Made with ❤️ by the AIOps Team

</div>
