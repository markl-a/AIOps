"""Tests for Cloud Cost Optimizer Agent."""

import pytest
from unittest.mock import AsyncMock, patch
from aiops.agents.cost_optimizer import (
    CloudCostOptimizerAgent,
    CostOptimizationResult,
    CostSaving,
    ResourceRecommendation,
)


@pytest.fixture
def cost_agent():
    """Create cost optimizer agent."""
    return CloudCostOptimizerAgent()


@pytest.fixture
def sample_cloud_resources():
    """Sample cloud resource usage."""
    return {
        "ec2_instances": [
            {"id": "i-123", "type": "m5.2xlarge", "utilization": 15.2, "monthly_cost": 245.0},
            {"id": "i-456", "type": "t3.medium", "utilization": 85.3, "monthly_cost": 30.0},
        ],
        "ebs_volumes": [
            {"id": "vol-789", "size_gb": 500, "iops": 3000, "attached": False, "monthly_cost": 50.0}
        ],
        "rds_instances": [
            {"id": "db-001", "type": "db.r5.large", "utilization": 25.0, "monthly_cost": 180.0}
        ],
    }


@pytest.mark.asyncio
async def test_analyze_costs(cost_agent, sample_cloud_resources):
    """Test cost analysis."""
    mock_result = CostOptimizationResult(
        total_monthly_cost=505.0,
        potential_savings=[
            CostSaving(
                resource_id="i-123",
                resource_type="ec2",
                current_cost=245.0,
                optimized_cost=60.0,
                savings=185.0,
                recommendation="Downsize to m5.large due to low utilization",
                risk_level="low",
            ),
            CostSaving(
                resource_id="vol-789",
                resource_type="ebs",
                current_cost=50.0,
                optimized_cost=0.0,
                savings=50.0,
                recommendation="Delete unattached volume",
                risk_level="none",
            ),
        ],
        recommendations=[
            ResourceRecommendation(
                category="rightsizing",
                action="Resize EC2 instance i-123",
                estimated_savings=185.0,
                implementation_effort="low",
            ),
            ResourceRecommendation(
                category="cleanup",
                action="Remove unattached EBS volume",
                estimated_savings=50.0,
                implementation_effort="very_low",
            ),
        ],
        total_potential_savings=235.0,
        optimization_score=75.0,
    )

    with patch.object(
        cost_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await cost_agent.execute(resources=sample_cloud_resources, cloud_provider="aws")

        assert isinstance(result, CostOptimizationResult)
        assert result.total_potential_savings == 235.0
        assert len(result.potential_savings) == 2
        assert result.optimization_score == 75.0


@pytest.mark.asyncio
async def test_reserved_instance_recommendations(cost_agent):
    """Test RI recommendation generation."""
    usage_pattern = {
        "instance_type": "m5.large",
        "running_hours_per_month": 720,  # 24/7
        "on_demand_cost": 100.0,
    }

    mock_result = CostOptimizationResult(
        total_monthly_cost=100.0,
        potential_savings=[
            CostSaving(
                resource_id="m5.large-ri",
                resource_type="reserved_instance",
                current_cost=100.0,
                optimized_cost=63.0,
                savings=37.0,
                recommendation="Purchase 1-year standard RI",
                risk_level="low",
            )
        ],
        recommendations=[],
        total_potential_savings=37.0,
        optimization_score=85.0,
    )

    with patch.object(
        cost_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await cost_agent.analyze_reserved_instances(usage=usage_pattern)

        assert isinstance(result, CostOptimizationResult)
        assert result.total_potential_savings > 0


@pytest.mark.asyncio
async def test_idle_resource_detection(cost_agent, sample_cloud_resources):
    """Test idle resource detection."""
    mock_result = CostOptimizationResult(
        total_monthly_cost=505.0,
        potential_savings=[
            CostSaving(
                resource_id="vol-789",
                resource_type="ebs",
                current_cost=50.0,
                optimized_cost=0.0,
                savings=50.0,
                recommendation="Delete idle unattached volume",
                risk_level="none",
            )
        ],
        recommendations=[],
        total_potential_savings=50.0,
        optimization_score=90.0,
    )

    with patch.object(
        cost_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await cost_agent.execute(resources=sample_cloud_resources)

        idle_resources = [
            saving for saving in result.potential_savings if "idle" in saving.recommendation.lower()
        ]
        assert len(idle_resources) > 0


@pytest.mark.asyncio
async def test_multi_cloud_analysis(cost_agent):
    """Test multi-cloud cost analysis."""
    resources_aws = {"ec2": [{"cost": 100}]}
    resources_azure = {"vm": [{"cost": 80}]}

    mock_result = CostOptimizationResult(
        total_monthly_cost=180.0,
        potential_savings=[],
        recommendations=[
            ResourceRecommendation(
                category="multi_cloud",
                action="Consider consolidating to single provider",
                estimated_savings=20.0,
            )
        ],
        total_potential_savings=20.0,
        optimization_score=70.0,
    )

    with patch.object(
        cost_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await cost_agent.analyze_multi_cloud(
            aws_resources=resources_aws, azure_resources=resources_azure
        )

        assert isinstance(result, CostOptimizationResult)


@pytest.mark.asyncio
async def test_error_handling(cost_agent):
    """Test error handling."""
    with patch.object(
        cost_agent,
        "_generate_structured_response",
        side_effect=Exception("Analysis failed"),
    ):
        result = await cost_agent.execute(resources={})

        assert isinstance(result, CostOptimizationResult)
        assert result.optimization_score == 0


def test_risk_level_validation(cost_agent, sample_cloud_resources):
    """Test risk level assignment."""
    # Risk levels should be: none, low, medium, high
    valid_risks = ["none", "low", "medium", "high"]

    mock_result = CostOptimizationResult(
        total_monthly_cost=0,
        potential_savings=[
            CostSaving(
                resource_id="test",
                resource_type="test",
                current_cost=0,
                optimized_cost=0,
                savings=0,
                recommendation="test",
                risk_level="low",
            )
        ],
        recommendations=[],
        total_potential_savings=0,
        optimization_score=0,
    )

    assert mock_result.potential_savings[0].risk_level in valid_risks
