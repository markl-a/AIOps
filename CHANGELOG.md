# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Nothing yet

### Changed
- Nothing yet

### Fixed
- Nothing yet

## [0.1.0] - 2024-01-15

### Added

#### Core Framework
- Multi-provider LLM support (OpenAI, Anthropic Claude, Google Gemini)
- Automatic LLM failover with configurable provider priority
- Token usage tracking and cost management
- Daily/monthly budget limits

#### AI Agents (29 Total)
- **Code Quality & Security**: Code Reviewer, Security Scanner, Test Generator, Doc Generator, Performance Analyzer, Secret Scanner, Container Security
- **Infrastructure & DevOps**: K8s Optimizer, Cost Optimizer, CI/CD Optimizer, Disaster Recovery, IaC Validator, Config Drift Detector, Service Mesh Analyzer, Dependency Analyzer
- **Monitoring & Analytics**: Log Analyzer, Anomaly Detector, Intelligent Monitor, API Performance Analyzer, DB Query Analyzer, SLA Monitor
- **Enterprise & Governance**: Incident Response, Compliance Checker, Migration Planner, Release Manager, Chaos Engineer

#### REST API
- FastAPI-based REST API with OpenAPI documentation
- JWT and API Key authentication
- Role-Based Access Control (RBAC)
- Rate limiting middleware
- Request validation and error handling

#### Integrations
- Slack integration with rich message formatting
- Microsoft Teams integration with Adaptive Cards
- GitHub webhook handler (push, PR, issues, releases, workflows)
- GitLab webhook handler (push, merge requests, pipelines)
- Jira webhook handler (issues, sprints)
- PagerDuty webhook handler (incidents)

#### Observability
- Prometheus metrics (60+ custom metrics)
- OpenTelemetry distributed tracing
- Structured logging with Loguru
- Sentry error tracking integration

#### Infrastructure
- PostgreSQL database with SQLAlchemy ORM
- Redis caching layer
- Celery async task queue with scheduler
- Docker and Docker Compose setup
- Kubernetes manifests with HPA and Ingress

#### Developer Experience
- Rich CLI interface with Click
- 15+ working examples
- Comprehensive documentation
- Validation and health check scripts
- Performance benchmark suite

### Security
- Security headers middleware
- CORS configuration
- Input validation
- Audit logging

[Unreleased]: https://github.com/markl-a/AIOps/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/markl-a/AIOps/releases/tag/v0.1.0
