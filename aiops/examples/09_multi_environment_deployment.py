"""Example 9: Multi-Environment Deployment (Dev/Staging/Production)

This example demonstrates how to manage deployments across multiple environments.
"""

import asyncio
import json
from typing import Dict, Any


async def compare_environments():
    """Compare configuration across different environments."""

    print("🌍 Multi-Environment Configuration")
    print("="*60)

    environments = {
        "development": {
            "replicas": 1,
            "resources": {
                "cpu": "250m",
                "memory": "512Mi",
            },
            "llm_provider": "openai",
            "llm_model": "gpt-3.5-turbo",
            "database": {
                "host": "localhost",
                "pool_size": 5,
                "ssl": False,
            },
            "redis": {
                "host": "localhost",
                "db": 0,
            },
            "logging": {
                "level": "DEBUG",
                "structured": True,
            },
            "monitoring": {
                "enabled": False,
            },
            "cost_tracking": {
                "enabled": False,
            },
        },
        "staging": {
            "replicas": 2,
            "resources": {
                "cpu": "500m",
                "memory": "1Gi",
            },
            "llm_provider": "openai",
            "llm_model": "gpt-4-turbo-preview",
            "database": {
                "host": "staging-db.example.com",
                "pool_size": 10,
                "ssl": True,
            },
            "redis": {
                "host": "staging-redis.example.com",
                "db": 0,
            },
            "logging": {
                "level": "INFO",
                "structured": True,
            },
            "monitoring": {
                "enabled": True,
                "metrics_interval": "30s",
            },
            "cost_tracking": {
                "enabled": True,
                "budget_alert_threshold": 100.0,
            },
        },
        "production": {
            "replicas": 5,
            "autoscaling": {
                "min_replicas": 3,
                "max_replicas": 10,
                "cpu_threshold": 70,
            },
            "resources": {
                "cpu": "1000m",
                "memory": "2Gi",
            },
            "llm_provider": "openai",
            "llm_model": "gpt-4-turbo-preview",
            "database": {
                "host": "prod-db-cluster.example.com",
                "pool_size": 20,
                "ssl": True,
                "read_replicas": ["replica1.example.com", "replica2.example.com"],
            },
            "redis": {
                "host": "prod-redis-cluster.example.com",
                "sentinel": True,
                "db": 0,
            },
            "logging": {
                "level": "WARNING",
                "structured": True,
                "aggregation": "elasticsearch",
            },
            "monitoring": {
                "enabled": True,
                "metrics_interval": "10s",
                "alerting": True,
            },
            "cost_tracking": {
                "enabled": True,
                "budget_alert_threshold": 1000.0,
                "daily_budget": 50.0,
            },
            "security": {
                "rate_limiting": True,
                "rate_limit_per_minute": 100,
                "ip_whitelist": ["10.0.0.0/8"],
            },
        },
    }

    # Compare key differences
    print("\n📊 Environment Comparison:\n")

    comparison_matrix = [
        ("Replicas", lambda e: e.get("replicas", "N/A")),
        ("CPU", lambda e: e.get("resources", {}).get("cpu", "N/A")),
        ("Memory", lambda e: e.get("resources", {}).get("memory", "N/A")),
        ("LLM Model", lambda e: e.get("llm_model", "N/A")),
        ("DB Pool Size", lambda e: e.get("database", {}).get("pool_size", "N/A")),
        ("SSL Enabled", lambda e: e.get("database", {}).get("ssl", False)),
        ("Log Level", lambda e: e.get("logging", {}).get("level", "N/A")),
        ("Monitoring", lambda e: "✅" if e.get("monitoring", {}).get("enabled") else "❌"),
        ("Cost Tracking", lambda e: "✅" if e.get("cost_tracking", {}).get("enabled") else "❌"),
    ]

    # Print header
    print(f"{'Setting':<20} {'Dev':<15} {'Staging':<15} {'Production':<15}")
    print("-" * 70)

    # Print comparison
    for setting_name, extractor in comparison_matrix:
        dev_val = str(extractor(environments["development"]))
        staging_val = str(extractor(environments["staging"]))
        prod_val = str(extractor(environments["production"]))
        print(f"{setting_name:<20} {dev_val:<15} {staging_val:<15} {prod_val:<15}")

    return environments


async def generate_environment_configs():
    """Generate Kubernetes configurations for each environment."""

    print("\n\n⚙️  Environment-Specific Kubernetes Configs")
    print("="*60)

    # Development config
    dev_config = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: aiops-api
  namespace: aiops-dev
spec:
  replicas: 1
  selector:
    matchLabels:
      app: aiops-api
      env: development
  template:
    metadata:
      labels:
        app: aiops-api
        env: development
    spec:
      containers:
      - name: api
        image: aiops:dev
        env:
        - name: ENVIRONMENT
          value: "development"
        - name: LOG_LEVEL
          value: "DEBUG"
        - name: DATABASE_URL
          value: "postgresql://localhost:5432/aiops_dev"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "250m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
"""

    print("\n🔧 Development (k8s/overlays/dev/deployment.yaml):")
    print(dev_config)

    # Production config
    prod_config = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: aiops-api
  namespace: aiops-prod
spec:
  replicas: 5
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: aiops-api
      env: production
  template:
    metadata:
      labels:
        app: aiops-api
        env: production
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: app
                operator: In
                values:
                - aiops-api
            topologyKey: "kubernetes.io/hostname"
      containers:
      - name: api
        image: aiops:1.0.0  # Pinned version
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: LOG_LEVEL
          value: "WARNING"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: aiops-secrets
              key: database-url
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: aiops-secrets
              key: openai-api-key
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 20
          periodSeconds: 5
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: aiops-api-hpa
  namespace: aiops-prod
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: aiops-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
"""

    print("\n\n🚀 Production (k8s/overlays/prod/deployment.yaml):")
    print(prod_config)


async def deployment_workflow():
    """Demonstrate deployment workflow across environments."""

    print("\n\n🚀 Deployment Workflow")
    print("="*60)

    workflow_steps = [
        {
            "stage": "Development",
            "steps": [
                "Developer commits code to feature branch",
                "GitHub Actions: Run tests and linting",
                "Build Docker image: aiops:dev-{commit-sha}",
                "Deploy to dev environment",
                "Run smoke tests",
            ],
            "automation": "Automatic on commit",
            "approval": "None required",
        },
        {
            "stage": "Staging",
            "steps": [
                "PR merged to main branch",
                "GitHub Actions: Build release candidate",
                "Tag image: aiops:rc-{version}",
                "Deploy to staging environment",
                "Run integration tests",
                "Run security scans",
                "Performance benchmarks",
            ],
            "automation": "Automatic on merge to main",
            "approval": "QA team approval required",
        },
        {
            "stage": "Production",
            "steps": [
                "QA approval received",
                "Create release tag: v{version}",
                "Build production image: aiops:{version}",
                "Backup current production database",
                "Deploy to production (canary: 10%)",
                "Monitor metrics for 15 minutes",
                "Gradually increase to 100%",
                "Post-deployment verification",
            ],
            "automation": "Manual trigger after approval",
            "approval": "Engineering lead + Product owner",
        },
    ]

    for stage_info in workflow_steps:
        print(f"\n{'='*60}")
        print(f"🎯 {stage_info['stage']} Deployment")
        print(f"{'='*60}")
        print(f"\n📋 Automation: {stage_info['automation']}")
        print(f"✅ Approval: {stage_info['approval']}\n")
        print("Steps:")
        for i, step in enumerate(stage_info['steps'], 1):
            print(f"  {i}. {step}")
            await asyncio.sleep(0.3)  # Simulate progress

    print("\n\n🔄 Rollback Procedure:")
    print("  1. Detect issue in production")
    print("  2. Trigger rollback: kubectl rollout undo deployment/aiops-api")
    print("  3. Verify previous version is healthy")
    print("  4. Investigate issue in staging")
    print("  5. Prepare hotfix if needed")


async def environment_promotion_checklist():
    """Generate deployment checklist for environment promotion."""

    print("\n\n✅ Environment Promotion Checklist")
    print("="*60)

    checklists = {
        "Dev → Staging": [
            "All tests passing in dev environment",
            "Code review completed",
            "No critical security vulnerabilities",
            "Database migrations tested",
            "API documentation updated",
            "Feature flags configured",
        ],
        "Staging → Production": [
            "All integration tests passing",
            "Performance benchmarks meet SLO",
            "Security audit completed",
            "Database backup completed",
            "Rollback plan documented",
            "Monitoring dashboards updated",
            "Runbook updated",
            "Stakeholders notified",
            "Deployment window scheduled",
            "On-call engineer assigned",
        ],
    }

    for promotion, checklist in checklists.items():
        print(f"\n📝 {promotion}:")
        for i, item in enumerate(checklist, 1):
            print(f"  {i}. [ ] {item}")


async def create_environment_specific_scripts():
    """Create deployment scripts for each environment."""

    print("\n\n📜 Environment-Specific Deployment Scripts")
    print("="*60)

    # Development deployment
    dev_deploy = """#!/bin/bash
# Deploy to Development Environment

set -e

ENVIRONMENT="dev"
NAMESPACE="aiops-dev"
IMAGE_TAG="dev-$(git rev-parse --short HEAD)"

echo "🚀 Deploying to Development"
echo "Image: aiops:${IMAGE_TAG}"

# Build and push image
docker build -t aiops:${IMAGE_TAG} .
docker tag aiops:${IMAGE_TAG} registry.example.com/aiops:${IMAGE_TAG}
docker push registry.example.com/aiops:${IMAGE_TAG}

# Apply Kubernetes manifests
kubectl apply -k k8s/overlays/dev

# Update image
kubectl set image deployment/aiops-api \\
  api=registry.example.com/aiops:${IMAGE_TAG} \\
  -n ${NAMESPACE}

# Wait for rollout
kubectl rollout status deployment/aiops-api -n ${NAMESPACE}

echo "✅ Deployment to dev completed"
"""

    print("\n🔧 Development Deploy (deploy-dev.sh):")
    print(dev_deploy)

    # Production deployment
    prod_deploy = """#!/bin/bash
# Deploy to Production Environment (with Canary)

set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <version>"
  exit 1
fi

VERSION=$1
ENVIRONMENT="prod"
NAMESPACE="aiops-prod"
IMAGE="registry.example.com/aiops:${VERSION}"

echo "🚀 Deploying to Production"
echo "Version: ${VERSION}"
echo ""
read -p "Have you completed the deployment checklist? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
  echo "Deployment cancelled. Please complete checklist first."
  exit 1
fi

# Backup database
echo "📦 Creating database backup..."
./scripts/backup-database.sh

# Canary deployment - 10%
echo "🐤 Starting canary deployment (10%)..."
kubectl apply -f k8s/overlays/prod/canary.yaml
kubectl set image deployment/aiops-api-canary \\
  api=${IMAGE} \\
  -n ${NAMESPACE}

kubectl rollout status deployment/aiops-api-canary -n ${NAMESPACE}

echo "⏳ Monitoring canary for 5 minutes..."
sleep 300

# Check canary metrics
ERROR_RATE=$(curl -s http://prometheus/api/v1/query?query=aiops_errors_total | jq '.data.result[0].value[1]')

if (( $(echo "$ERROR_RATE > 0.01" | bc -l) )); then
  echo "❌ Canary error rate too high: ${ERROR_RATE}"
  echo "Rolling back canary..."
  kubectl delete deployment aiops-api-canary -n ${NAMESPACE}
  exit 1
fi

echo "✅ Canary healthy, proceeding with full deployment"

# Full deployment
kubectl set image deployment/aiops-api \\
  api=${IMAGE} \\
  -n ${NAMESPACE}

kubectl rollout status deployment/aiops-api -n ${NAMESPACE}

# Cleanup canary
kubectl delete deployment aiops-api-canary -n ${NAMESPACE}

echo "✅ Production deployment completed successfully"
echo "📊 Monitor: https://grafana.example.com/d/aiops"
"""

    print("\n\n🚀 Production Deploy (deploy-prod.sh):")
    print(prod_deploy)


async def demonstrate_feature_flags():
    """Show how to use feature flags for gradual rollout."""

    print("\n\n🚩 Feature Flags for Gradual Rollout")
    print("="*60)

    feature_flags = {
        "new_llm_model": {
            "dev": {"enabled": True, "rollout": 100},
            "staging": {"enabled": True, "rollout": 100},
            "production": {"enabled": True, "rollout": 10},  # 10% rollout
        },
        "advanced_caching": {
            "dev": {"enabled": True, "rollout": 100},
            "staging": {"enabled": True, "rollout": 100},
            "production": {"enabled": False, "rollout": 0},
        },
        "cost_optimizer_v2": {
            "dev": {"enabled": True, "rollout": 100},
            "staging": {"enabled": False, "rollout": 0},
            "production": {"enabled": False, "rollout": 0},
        },
    }

    print("\n📊 Feature Flag Status:\n")
    print(f"{'Feature':<25} {'Dev':<15} {'Staging':<15} {'Production':<15}")
    print("-" * 75)

    for feature, envs in feature_flags.items():
        dev_status = f"{'✅' if envs['dev']['enabled'] else '❌'} {envs['dev']['rollout']}%"
        staging_status = f"{'✅' if envs['staging']['enabled'] else '❌'} {envs['staging']['rollout']}%"
        prod_status = f"{'✅' if envs['production']['enabled'] else '❌'} {envs['production']['rollout']}%"

        print(f"{feature:<25} {dev_status:<15} {staging_status:<15} {prod_status:<15}")

    # Example code
    print("\n\n💻 Feature Flag Usage Example:")
    print("""
from aiops.core.feature_flags import is_feature_enabled

async def analyze_code(code: str):
    # Use new LLM model for 10% of production traffic
    if is_feature_enabled("new_llm_model", user_id=user_id):
        model = "gpt-4-turbo-preview"
    else:
        model = "gpt-3.5-turbo"

    return await llm.analyze(code, model=model)
""")


if __name__ == "__main__":
    print("🌍 Multi-Environment Deployment Examples")
    print("="*60)

    # Run examples
    asyncio.run(compare_environments())

    print("\n" + "="*60)
    asyncio.run(generate_environment_configs())

    print("\n" + "="*60)
    asyncio.run(deployment_workflow())

    print("\n" + "="*60)
    asyncio.run(environment_promotion_checklist())

    print("\n" + "="*60)
    asyncio.run(create_environment_specific_scripts())

    print("\n" + "="*60)
    asyncio.run(demonstrate_feature_flags())

    print("\n✅ All multi-environment deployment examples complete!\n")
