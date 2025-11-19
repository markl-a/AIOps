"""Tests for Kubernetes Optimizer Agent."""

import pytest
from unittest.mock import AsyncMock, patch
from aiops.agents.k8s_optimizer import (
    KubernetesOptimizerAgent,
    K8sOptimizationResult,
    ResourceOptimization,
    HPARecommendation,
)


@pytest.fixture
def k8s_agent():
    """Create K8s optimizer agent."""
    return KubernetesOptimizerAgent()


@pytest.fixture
def sample_k8s_manifest():
    """Sample Kubernetes manifest."""
    return """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: app
        image: myapp:latest
        resources:
          requests:
            memory: "64Mi"
            cpu: "250m"
          limits:
            memory: "128Mi"
            cpu: "500m"
"""


@pytest.fixture
def sample_metrics():
    """Sample resource metrics."""
    return {
        "cpu_usage_avg": 15.2,
        "memory_usage_avg": 45.8,
        "cpu_usage_p95": 32.5,
        "memory_usage_p95": 78.3,
        "request_count": 10000,
    }


@pytest.mark.asyncio
async def test_analyze_resources(k8s_agent, sample_k8s_manifest, sample_metrics):
    """Test resource analysis."""
    mock_result = K8sOptimizationResult(
        resource_optimizations=[
            ResourceOptimization(
                resource_type="deployment",
                resource_name="web-app",
                current_cpu_request="250m",
                recommended_cpu_request="100m",
                current_memory_request="64Mi",
                recommended_memory_request="32Mi",
                potential_savings_percent=60.0,
                justification="CPU usage averaging only 15%, can reduce safely",
            )
        ],
        hpa_recommendations=[
            HPARecommendation(
                resource_name="web-app",
                min_replicas=2,
                max_replicas=10,
                target_cpu_percent=70,
                target_memory_percent=80,
                justification="Enable autoscaling for variable load",
            )
        ],
        cost_savings_monthly=245.50,
        overall_score=85.0,
    )

    with patch.object(
        k8s_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await k8s_agent.execute(
            manifest=sample_k8s_manifest, metrics=sample_metrics
        )

        assert isinstance(result, K8sOptimizationResult)
        assert len(result.resource_optimizations) == 1
        assert result.cost_savings_monthly > 0
        assert result.overall_score == 85.0


@pytest.mark.asyncio
async def test_optimize_namespace(k8s_agent):
    """Test namespace optimization."""
    namespace_config = {
        "deployments": 5,
        "total_cpu_requested": "2000m",
        "total_memory_requested": "4Gi",
    }

    mock_result = K8sOptimizationResult(
        resource_optimizations=[],
        hpa_recommendations=[],
        cost_savings_monthly=500.0,
        overall_score=90.0,
    )

    with patch.object(
        k8s_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await k8s_agent.optimize_namespace(
            namespace="production", config=namespace_config
        )

        assert isinstance(result, K8sOptimizationResult)
        assert result.cost_savings_monthly >= 0


@pytest.mark.asyncio
async def test_error_handling(k8s_agent):
    """Test error handling."""
    with patch.object(
        k8s_agent,
        "_generate_structured_response",
        side_effect=Exception("API Error"),
    ):
        result = await k8s_agent.execute(manifest="invalid", metrics={})

        assert isinstance(result, K8sOptimizationResult)
        assert result.overall_score == 0


@pytest.mark.asyncio
async def test_hpa_recommendations(k8s_agent, sample_k8s_manifest):
    """Test HPA recommendation generation."""
    mock_result = K8sOptimizationResult(
        resource_optimizations=[],
        hpa_recommendations=[
            HPARecommendation(
                resource_name="web-app",
                min_replicas=2,
                max_replicas=10,
                target_cpu_percent=70,
            )
        ],
        cost_savings_monthly=0,
        overall_score=75.0,
    )

    with patch.object(
        k8s_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await k8s_agent.execute(manifest=sample_k8s_manifest)

        assert len(result.hpa_recommendations) == 1
        assert result.hpa_recommendations[0].min_replicas >= 1


def test_create_system_prompt(k8s_agent):
    """Test system prompt creation."""
    prompt = k8s_agent._create_system_prompt()

    assert "kubernetes" in prompt.lower()
    assert "resources" in prompt.lower()
    assert "optimization" in prompt.lower()
