"""Example 10: Complete CI/CD Pipeline Integration

This example demonstrates a complete CI/CD pipeline with multiple stages.
"""

import asyncio
import json
from datetime import datetime


async def github_actions_workflow():
    """Generate a complete GitHub Actions workflow."""

    print("🔄 Complete CI/CD Pipeline with GitHub Actions")
    print("="*60)

    workflow = """name: AIOps CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  release:
    types: [created]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  # Stage 1: Code Quality & Testing
  test:
    name: Test & Quality Checks
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Cache dependencies
        uses: actions/cache@v3
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run linting
        run: |
          echo "🔍 Running flake8..."
          flake8 aiops/ --count --show-source --statistics

          echo "🔍 Running black..."
          black --check aiops/

          echo "🔍 Running mypy..."
          mypy aiops/

      - name: Run unit tests
        run: |
          echo "🧪 Running unit tests..."
          pytest aiops/tests/unit/ \\
            --cov=aiops \\
            --cov-report=xml \\
            --cov-report=html \\
            -v

      - name: Run integration tests
        run: |
          echo "🧪 Running integration tests..."
          pytest aiops/tests/integration/ -v

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          flags: unittests
          name: codecov-${{ matrix.python-version }}

  # Stage 2: Security Scanning
  security:
    name: Security Scan
    runs-on: ubuntu-latest
    needs: test

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Upload Trivy results to GitHub Security
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'

      - name: Run Bandit security linter
        run: |
          pip install bandit
          bandit -r aiops/ -f json -o bandit-report.json

      - name: Check for secrets
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ github.event.repository.default_branch }}
          head: HEAD

      - name: Dependency vulnerability check
        run: |
          pip install safety
          safety check --json

  # Stage 3: Build Docker Image
  build:
    name: Build & Push Docker Image
    runs-on: ubuntu-latest
    needs: [test, security]
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha,prefix={{branch}}-

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=registry,ref=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:buildcache
          cache-to: type=registry,ref=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:buildcache,mode=max

      - name: Scan Docker image for vulnerabilities
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ steps.meta.outputs.version }}
          format: 'sarif'
          output: 'trivy-image-results.sarif'

  # Stage 4: Deploy to Development
  deploy-dev:
    name: Deploy to Development
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/develop'
    environment:
      name: development
      url: https://dev.aiops.example.com

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Configure kubectl
        uses: azure/k8s-set-context@v3
        with:
          method: kubeconfig
          kubeconfig: ${{ secrets.KUBE_CONFIG_DEV }}

      - name: Deploy to Kubernetes
        run: |
          kubectl apply -k k8s/overlays/dev
          kubectl set image deployment/aiops-api \\
            api=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} \\
            -n aiops-dev
          kubectl rollout status deployment/aiops-api -n aiops-dev

      - name: Run smoke tests
        run: |
          pip install requests pytest
          pytest tests/smoke/ --base-url=https://dev.aiops.example.com

  # Stage 5: Deploy to Staging
  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    needs: deploy-dev
    if: github.ref == 'refs/heads/main'
    environment:
      name: staging
      url: https://staging.aiops.example.com

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Configure kubectl
        uses: azure/k8s-set-context@v3
        with:
          method: kubeconfig
          kubeconfig: ${{ secrets.KUBE_CONFIG_STAGING }}

      - name: Deploy to Kubernetes
        run: |
          kubectl apply -k k8s/overlays/staging
          kubectl set image deployment/aiops-api \\
            api=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} \\
            -n aiops-staging
          kubectl rollout status deployment/aiops-api -n aiops-staging

      - name: Run integration tests
        run: |
          pytest tests/integration/ --base-url=https://staging.aiops.example.com

      - name: Run performance tests
        run: |
          pip install locust
          locust -f tests/performance/locustfile.py \\
            --host=https://staging.aiops.example.com \\
            --users=100 \\
            --spawn-rate=10 \\
            --run-time=5m \\
            --headless

  # Stage 6: Deploy to Production
  deploy-production:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: deploy-staging
    if: github.event_name == 'release'
    environment:
      name: production
      url: https://aiops.example.com

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Configure kubectl
        uses: azure/k8s-set-context@v3
        with:
          method: kubeconfig
          kubeconfig: ${{ secrets.KUBE_CONFIG_PROD }}

      - name: Backup database
        run: |
          kubectl create job backup-pre-deploy-${{ github.sha }} \\
            --from=cronjob/database-backup \\
            -n aiops-prod
          kubectl wait --for=condition=complete job/backup-pre-deploy-${{ github.sha }} \\
            -n aiops-prod \\
            --timeout=300s

      - name: Deploy canary (10%)
        run: |
          kubectl apply -f k8s/overlays/prod/canary.yaml
          kubectl set image deployment/aiops-api-canary \\
            api=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.event.release.tag_name }} \\
            -n aiops-prod
          kubectl rollout status deployment/aiops-api-canary -n aiops-prod

      - name: Monitor canary metrics
        run: |
          sleep 300  # Wait 5 minutes

          # Check error rate
          ERROR_RATE=$(curl -s "http://prometheus:9090/api/v1/query?query=rate(aiops_errors_total[5m])" | jq -r '.data.result[0].value[1]')

          if (( $(echo "$ERROR_RATE > 0.01" | bc -l) )); then
            echo "Canary failed: high error rate"
            kubectl delete deployment aiops-api-canary -n aiops-prod
            exit 1
          fi

      - name: Full production rollout
        run: |
          kubectl set image deployment/aiops-api \\
            api=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.event.release.tag_name }} \\
            -n aiops-prod
          kubectl rollout status deployment/aiops-api -n aiops-prod

          # Cleanup canary
          kubectl delete deployment aiops-api-canary -n aiops-prod

      - name: Verify deployment
        run: |
          curl -f https://aiops.example.com/health || exit 1
          curl -f https://aiops.example.com/ready || exit 1

      - name: Notify Slack
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "🚀 AIOps ${{ github.event.release.tag_name }} deployed to production",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "✅ *Deployment Successful*\\n*Version:* ${{ github.event.release.tag_name }}\\n*Environment:* Production\\n*Deployed by:* ${{ github.actor }}"
                  }
                }
              ]
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
"""

    print("\n📄 Complete GitHub Actions Workflow (.github/workflows/cicd.yml):")
    print(workflow)


async def demonstrate_pipeline_stages():
    """Show the different stages of the CI/CD pipeline."""

    print("\n\n🔄 CI/CD Pipeline Stages")
    print("="*60)

    stages = [
        {
            "name": "Stage 1: Code Quality",
            "duration": "~3-5 minutes",
            "steps": [
                "Checkout code",
                "Set up Python environment",
                "Install dependencies",
                "Run linters (flake8, black, mypy)",
                "Run unit tests with coverage",
                "Upload coverage reports",
            ],
            "success_criteria": [
                "All linters pass",
                "Test coverage > 75%",
                "All tests pass",
            ],
        },
        {
            "name": "Stage 2: Security Scanning",
            "duration": "~2-3 minutes",
            "steps": [
                "Scan code for vulnerabilities (Trivy)",
                "Check for security issues (Bandit)",
                "Scan for exposed secrets (TruffleHog)",
                "Check dependencies (Safety)",
            ],
            "success_criteria": [
                "No critical vulnerabilities",
                "No exposed secrets",
                "No known vulnerable dependencies",
            ],
        },
        {
            "name": "Stage 3: Build & Push",
            "duration": "~5-7 minutes",
            "steps": [
                "Build Docker image with BuildKit",
                "Tag with version and SHA",
                "Push to container registry",
                "Scan Docker image",
                "Generate SBOM (Software Bill of Materials)",
            ],
            "success_criteria": [
                "Image builds successfully",
                "No critical vulnerabilities in image",
                "Image size optimized",
            ],
        },
        {
            "name": "Stage 4: Deploy to Dev",
            "duration": "~2-3 minutes",
            "steps": [
                "Apply Kubernetes manifests",
                "Update deployment image",
                "Wait for rollout completion",
                "Run smoke tests",
            ],
            "success_criteria": [
                "Deployment successful",
                "All pods healthy",
                "Smoke tests pass",
            ],
        },
        {
            "name": "Stage 5: Deploy to Staging",
            "duration": "~5-7 minutes",
            "steps": [
                "Deploy to staging cluster",
                "Run integration tests",
                "Run performance tests",
                "Validate against SLOs",
            ],
            "success_criteria": [
                "Integration tests pass",
                "Performance meets benchmarks",
                "Error rate < 0.1%",
            ],
        },
        {
            "name": "Stage 6: Deploy to Production",
            "duration": "~15-20 minutes",
            "steps": [
                "Backup database",
                "Deploy canary (10% traffic)",
                "Monitor metrics for 5 minutes",
                "Gradual rollout to 100%",
                "Post-deployment verification",
                "Send notifications",
            ],
            "success_criteria": [
                "Canary healthy",
                "Full rollout successful",
                "All health checks pass",
                "No alerts triggered",
            ],
        },
    ]

    total_duration = 0
    for i, stage in enumerate(stages, 1):
        print(f"\n{'='*60}")
        print(f"{stage['name']}")
        print(f"⏱️  Duration: {stage['duration']}")
        print(f"{'='*60}")

        print("\n📋 Steps:")
        for step_num, step in enumerate(stage['steps'], 1):
            print(f"  {step_num}. {step}")
            await asyncio.sleep(0.2)

        print("\n✅ Success Criteria:")
        for criterion in stage['success_criteria']:
            print(f"  • {criterion}")

        # Extract minutes from duration string
        duration_parts = stage['duration'].split('-')
        avg_minutes = (int(duration_parts[0].replace('~', '')) +
                      int(duration_parts[1].split()[0])) / 2
        total_duration += avg_minutes

    print(f"\n\n⏱️  Total Pipeline Duration: ~{int(total_duration)} minutes")
    print("   (Development deployment: ~10-15 min)")
    print("   (Production deployment: ~30-40 min)")


async def create_pipeline_monitoring():
    """Create monitoring dashboards for the CI/CD pipeline."""

    print("\n\n📊 CI/CD Pipeline Monitoring")
    print("="*60)

    metrics = {
        "Build Metrics": [
            {"name": "Build Success Rate", "value": "98.5%", "target": ">95%"},
            {"name": "Average Build Time", "value": "4.2 min", "target": "<5 min"},
            {"name": "Build Queue Time", "value": "12 sec", "target": "<30 sec"},
        ],
        "Deployment Metrics": [
            {"name": "Deployment Frequency", "value": "15/day", "target": ">10/day"},
            {"name": "Lead Time", "value": "2.5 hours", "target": "<4 hours"},
            {"name": "MTTR", "value": "18 min", "target": "<30 min"},
            {"name": "Change Failure Rate", "value": "2.1%", "target": "<5%"},
        ],
        "Quality Metrics": [
            {"name": "Test Coverage", "value": "82%", "target": ">75%"},
            {"name": "Code Quality Score", "value": "A", "target": "A"},
            {"name": "Security Vulnerabilities", "value": "0 critical", "target": "0"},
        ],
    }

    for category, category_metrics in metrics.items():
        print(f"\n📈 {category}:")
        for metric in category_metrics:
            status = "✅" if metric['value'] >= metric['target'] or metric['value'] == metric['target'] else "⚠️"
            print(f"  {status} {metric['name']}: {metric['value']} (target: {metric['target']})")

    # Grafana dashboard config
    print("\n\n📊 Grafana Dashboard Configuration:")
    print("""
{
  "dashboard": {
    "title": "CI/CD Pipeline Metrics",
    "panels": [
      {
        "title": "Build Success Rate",
        "targets": [
          {
            "expr": "rate(cicd_builds_total{status='success'}[1h]) / rate(cicd_builds_total[1h])"
          }
        ]
      },
      {
        "title": "Deployment Frequency",
        "targets": [
          {
            "expr": "sum(rate(cicd_deployments_total[24h]))"
          }
        ]
      },
      {
        "title": "Lead Time for Changes",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, cicd_lead_time_seconds_bucket)"
          }
        ]
      },
      {
        "title": "Change Failure Rate",
        "targets": [
          {
            "expr": "rate(cicd_deployments_total{status='failed'}[7d]) / rate(cicd_deployments_total[7d])"
          }
        ]
      }
    ]
  }
}
""")


async def demonstrate_rollback_procedures():
    """Show automated rollback procedures."""

    print("\n\n🔙 Automated Rollback Procedures")
    print("="*60)

    print("\n1️⃣  Automatic Rollback on Failed Health Checks:")
    print("""
# In deployment.yaml
spec:
  progressDeadlineSeconds: 600
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1

# If deployment doesn't progress within 10 minutes, it fails
# Kubernetes will automatically stop the rollout
""")

    print("\n2️⃣  Manual Rollback Command:")
    print("""
# Rollback to previous version
kubectl rollout undo deployment/aiops-api -n aiops-prod

# Rollback to specific revision
kubectl rollout undo deployment/aiops-api --to-revision=5 -n aiops-prod

# Check rollback status
kubectl rollout status deployment/aiops-api -n aiops-prod
""")

    print("\n3️⃣  Automated Rollback Based on Metrics:")
    rollback_script = """#!/bin/bash
# Automated rollback based on error rate

ERROR_THRESHOLD=0.05
DEPLOYMENT="aiops-api"
NAMESPACE="aiops-prod"

# Query Prometheus for error rate
ERROR_RATE=$(curl -s "http://prometheus:9090/api/v1/query?query=rate(aiops_errors_total[5m])" | \\
  jq -r '.data.result[0].value[1]')

echo "Current error rate: ${ERROR_RATE}"

if (( $(echo "$ERROR_RATE > $ERROR_THRESHOLD" | bc -l) )); then
  echo "🚨 Error rate exceeded threshold! Initiating rollback..."

  # Rollback deployment
  kubectl rollout undo deployment/${DEPLOYMENT} -n ${NAMESPACE}

  # Wait for rollback
  kubectl rollout status deployment/${DEPLOYMENT} -n ${NAMESPACE}

  # Send alert
  curl -X POST $SLACK_WEBHOOK \\
    -H 'Content-Type: application/json' \\
    -d '{
      "text": "⚠️ Automatic rollback initiated",
      "attachments": [{
        "color": "danger",
        "fields": [
          {"title": "Reason", "value": "High error rate: '${ERROR_RATE}'"},
          {"title": "Deployment", "value": "'${DEPLOYMENT}'"},
          {"title": "Namespace", "value": "'${NAMESPACE}'"}
        ]
      }]
    }'

  echo "✅ Rollback completed"
else
  echo "✅ Error rate within acceptable range"
fi
"""

    print(rollback_script)


async def show_cicd_best_practices():
    """Display CI/CD best practices."""

    print("\n\n💡 CI/CD Best Practices")
    print("="*60)

    best_practices = {
        "Build & Test": [
            "Run tests in parallel to reduce build time",
            "Use Docker layer caching to speed up builds",
            "Fail fast - run quick tests first",
            "Maintain >75% code coverage",
            "Run linters before tests",
        ],
        "Security": [
            "Scan for vulnerabilities at every stage",
            "Never commit secrets to Git",
            "Use secret scanning in CI/CD",
            "Scan Docker images before deployment",
            "Keep dependencies up to date",
        ],
        "Deployment": [
            "Use canary deployments for production",
            "Always backup database before deployment",
            "Implement automated rollback",
            "Monitor metrics after deployment",
            "Use feature flags for gradual rollout",
        ],
        "Monitoring": [
            "Track DORA metrics (deployment frequency, lead time, MTTR, change failure rate)",
            "Set up alerts for failed builds/deployments",
            "Monitor build queue times",
            "Track test execution times",
            "Measure test flakiness",
        ],
        "Documentation": [
            "Document deployment procedures",
            "Maintain runbooks for common issues",
            "Keep deployment checklists updated",
            "Document rollback procedures",
            "Create troubleshooting guides",
        ],
    }

    for category, practices in best_practices.items():
        print(f"\n✅ {category}:")
        for practice in practices:
            print(f"  • {practice}")


if __name__ == "__main__":
    print("🔄 Complete CI/CD Pipeline Examples")
    print("="*60)

    # Run examples
    asyncio.run(github_actions_workflow())

    print("\n" + "="*60)
    asyncio.run(demonstrate_pipeline_stages())

    print("\n" + "="*60)
    asyncio.run(create_pipeline_monitoring())

    print("\n" + "="*60)
    asyncio.run(demonstrate_rollback_procedures())

    print("\n" + "="*60)
    asyncio.run(show_cicd_best_practices())

    print("\n✅ All CI/CD pipeline examples complete!\n")
