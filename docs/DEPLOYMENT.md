# AIOps Deployment Guide

This document provides a complete deployment guide for the AIOps project, including deployment steps for local development, testing environments, and production environments.

## Table of Contents

- [Requirements](#requirements)
- [Local Development Deployment](#local-development-deployment)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Production Deployment](#kubernetes-production-deployment)
- [Configuration Management](#configuration-management)
- [Monitoring and Logging](#monitoring-and-logging)
- [Backup and Disaster Recovery](#backup-and-disaster-recovery)

---

## Requirements

### Minimum Requirements
- **Python**: 3.9+
- **PostgreSQL**: 13+
- **Redis**: 6.0+
- **CPU**: 2 cores
- **Memory**: 4GB
- **Storage**: 20GB

### Production Environment Recommendations
- **Python**: 3.11
- **PostgreSQL**: 15+ (with pgvector extension)
- **Redis**: 7.0+
- **CPU**: 4+ cores
- **Memory**: 16GB+
- **Storage**: 100GB+ SSD

### Dependency Services
- **LLM API**: OpenAI or Anthropic API key
- **Kubernetes**: 1.24+ (production environment)
- **Jaeger**: Distributed tracing (optional)
- **Prometheus**: Metrics monitoring (optional)
- **Grafana**: Visualization (optional)

---

## Local Development Deployment

### 1. Clone the Project

```bash
git clone https://github.com/markl-a/AIOps.git
cd AIOps
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
```

Edit the `.env` file:

```env
# LLM Configuration
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
DEFAULT_LLM_PROVIDER=openai
DEFAULT_MODEL=gpt-4-turbo-preview

# Database Configuration
DATABASE_URL=postgresql://aiops:aiops@localhost:5432/aiops

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# API Security
ENABLE_AUTH=true
JWT_SECRET_KEY=your_secret_key_here
ADMIN_PASSWORD=your_admin_password

# Logging Configuration
LOG_LEVEL=INFO
ENABLE_METRICS=true
```

### 5. Start Services

#### Option A: Using Docker Compose (Recommended)

```bash
docker-compose up -d
```

This will start:
- PostgreSQL
- Redis
- AIOps API
- AIOps Worker
- AIOps Beat
- Prometheus (optional)

#### Option B: Manual Start

**Start PostgreSQL and Redis** (assuming already installed)

```bash
# Create database
createdb aiops

# Run migrations
alembic upgrade head
```

**Start API Server**

```bash
uvicorn aiops.api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Start Celery Worker**

```bash
celery -A aiops.tasks.celery_app worker --loglevel=info
```

**Start Celery Beat**

```bash
celery -A aiops.tasks.celery_app beat --loglevel=info
```

### 6. Verify Deployment

Visit http://localhost:8000/docs to view API documentation

```bash
# Health check
curl http://localhost:8000/health

# Get Token
curl -X POST http://localhost:8000/api/v1/auth/token \
  -d "username=admin&password=admin"
```

---

## Docker Deployment

### 1. Build Image

```bash
docker build -t aiops:latest .
```

### 2. Using Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 3. Custom Configuration

Edit `docker-compose.yml`:

```yaml
services:
  aiops-api:
    environment:
      - DEFAULT_MODEL=gpt-4-turbo-preview
      - WORKERS=4
```

---

## Kubernetes Production Deployment

### Prerequisites

- Kubernetes cluster (1.24+)
- kubectl configured
- Helm 3.0+ (optional)

### 1. Create Namespace

```bash
kubectl create namespace aiops
```

### 2. Create Secrets

```bash
# Create API key Secret
kubectl create secret generic aiops-secrets \
  --from-literal=database-url=postgresql://user:pass@postgres:5432/aiops \
  --from-literal=openai-api-key=your_openai_key \
  --from-literal=anthropic-api-key=your_anthropic_key \
  -n aiops
```

### 3. Deploy PostgreSQL and Redis

```bash
# Deploy PostgreSQL using Helm
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install postgres bitnami/postgresql \
  --set auth.username=aiops \
  --set auth.password=aiops \
  --set auth.database=aiops \
  -n aiops

# Deploy Redis
helm install redis bitnami/redis \
  --set auth.enabled=false \
  -n aiops
```

### 4. Deploy AIOps Application

```bash
# Apply Kubernetes configuration
kubectl apply -f k8s/base/ -n aiops

# View deployment status
kubectl get pods -n aiops
kubectl get svc -n aiops
```

### 5. Configure Ingress

Edit `k8s/base/ingress.yaml` to set your domain:

```yaml
spec:
  tls:
  - hosts:
    - your-domain.com
  rules:
  - host: your-domain.com
```

Apply configuration:

```bash
kubectl apply -f k8s/base/ingress.yaml -n aiops
```

### 6. Configure Auto Scaling

HPA is included in the configuration, verify:

```bash
kubectl get hpa -n aiops
```

### 7. Run Database Migrations

```bash
# Enter API Pod
kubectl exec -it deployment/aiops-api -n aiops -- bash

# Run migrations
alembic upgrade head
```

---

## Configuration Management

### Environment Variables

All configuration is managed through environment variables:

#### Required Variables

| Variable Name | Description | Requirements |
|---------------|-------------|--------------|
| `JWT_SECRET_KEY` | JWT signing key | **Must be at least 32 characters** |
| `ADMIN_PASSWORD` | Administrator password | **Must be set** |
| `DATABASE_URL` | PostgreSQL connection string | Must be set |
| `OPENAI_API_KEY` | OpenAI API key | At least one LLM key required |
| `ANTHROPIC_API_KEY` | Anthropic API key | At least one LLM key required |

> **Security Warning**: `JWT_SECRET_KEY` and `ADMIN_PASSWORD` must be set in production environments, otherwise the application will fail to start.

Generate a secure JWT key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### Optional Variables

| Variable Name | Description | Default Value |
|---------------|-------------|---------------|
| `ENVIRONMENT` | Runtime environment | `development` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `DEFAULT_LLM_PROVIDER` | Default LLM provider | `openai` |
| `DEFAULT_MODEL` | Default model | `gpt-4-turbo-preview` |
| `LOG_LEVEL` | Log level | `INFO` |
| `ENABLE_AUTH` | Enable authentication | `true` |
| `ENABLE_METRICS` | Enable monitoring | `true` |
| `OTLP_ENDPOINT` | OpenTelemetry endpoint | - |

#### Database Connection Pool Configuration

| Variable Name | Description | Development Default | Production Default |
|---------------|-------------|---------------------|-------------------|
| `DB_POOL_SIZE` | Connection pool size | `5` | `20` |
| `DB_MAX_OVERFLOW` | Maximum overflow connections | `10` | `40` |
| `DB_POOL_TIMEOUT` | Connection timeout (seconds) | `30` | `30` |
| `DB_POOL_RECYCLE` | Connection recycle time (seconds) | `3600` | `3600` |

#### Production Environment Features

When `ENVIRONMENT=production`, the following features are automatically enabled:

- **API Documentation Disabled**: `/docs`, `/redoc`, `/openapi.json` endpoints will be unavailable
- **Enhanced Connection Pool**: Database connection pool automatically adjusts to production specifications
- **Strict Validation**: Webhooks must provide valid signatures

### ConfigMap Configuration

```bash
kubectl create configmap aiops-config \
  --from-literal=log-level=INFO \
  --from-literal=default-model=gpt-4-turbo-preview \
  -n aiops
```

---

## Monitoring and Logging

### Prometheus Metrics

AIOps exposes the following Prometheus metrics:

- `/metrics` - Application metrics endpoint

Key metrics:
- `aiops_http_requests_total` - Total HTTP requests
- `aiops_agent_executions_total` - Total agent executions
- `aiops_llm_requests_total` - Total LLM requests
- `aiops_llm_cost_total` - Total LLM cost
- `aiops_errors_total` - Total errors

### Deploy Prometheus

```bash
kubectl apply -f monitoring/prometheus/
```

### Grafana Dashboards

1. Deploy Grafana:
```bash
helm install grafana bitnami/grafana -n aiops
```

2. Import dashboards:
- Access Grafana UI
- Import `monitoring/grafana/dashboards/*.json`

### Log Aggregation

Logs are output in JSON format to the `logs/` directory.

**Using ELK/EFK Stack**:

```bash
# Install Filebeat
kubectl apply -f monitoring/logging/filebeat.yaml -n aiops
```

**View Logs**:

```bash
# Real-time API logs
kubectl logs -f deployment/aiops-api -n aiops

# View Worker logs
kubectl logs -f deployment/aiops-worker -n aiops
```

---

## Backup and Disaster Recovery

### Database Backup

**Manual Backup**:

```bash
# Backup database
pg_dump -h localhost -U aiops aiops > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore database
psql -h localhost -U aiops aiops < backup_20240101_120000.sql
```

**Automatic Backup (Kubernetes CronJob)**:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:15
            command:
            - /bin/sh
            - -c
            - pg_dump -h postgres -U aiops aiops | gzip > /backup/db_$(date +\%Y\%m\%d).sql.gz
```

### Disaster Recovery Plan

See [DISASTER_RECOVERY.md](./DISASTER_RECOVERY.md) for details

---

## Troubleshooting

### Common Issues

**1. API Cannot Connect to Database**

```bash
# Check database connection
kubectl exec deployment/aiops-api -n aiops -- \
  psql $DATABASE_URL -c "SELECT 1"
```

**2. Worker Cannot Process Tasks**

```bash
# Check Redis connection
kubectl exec deployment/aiops-worker -n aiops -- \
  redis-cli -u $REDIS_URL ping
```

**3. High Memory Usage**

```bash
# View resource usage
kubectl top pods -n aiops
```

For detailed troubleshooting, refer to [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)

---

## Security Best Practices

1. Use strong passwords and keys
2. Enable TLS/SSL encryption
3. Regularly update dependencies
4. Use Kubernetes Secrets to manage sensitive data
5. Enable Pod Security Policies
6. Regularly backup data
7. Enable audit logging
8. Implement API rate limiting

---

## Performance Tuning

### API Server

```yaml
# Increase worker count
command: ["uvicorn", "aiops.api.main:app", "--workers", "4"]

# Adjust resource limits
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "2000m"
```

### Worker Concurrency

```yaml
# Celery worker concurrency settings
args:
  - "--concurrency=8"
  - "--max-tasks-per-child=100"
```

### Database Connection Pool

```python
# Adjust connection pool size
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
)
```

---

## Scalability Considerations

- **Horizontal Scaling**: Use HPA for automatic Pod scaling
- **Vertical Scaling**: Increase Pod resource limits
- **Database**: Use PostgreSQL read replicas
- **Caching**: Use Redis Cluster
- **Load Balancing**: Use Ingress Controller

---

## Related Documentation

- [Troubleshooting Guide](./TROUBLESHOOTING.md)
- [Disaster Recovery Plan](./DISASTER_RECOVERY.md)
- [Best Practices](./BEST_PRACTICES.md)
- [API Documentation](./API.md)

---

**Last Updated**: 2024-01-15
**Version**: 1.0.0
