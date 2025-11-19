"""Tests for Disaster Recovery Planner Agent."""

import pytest
from unittest.mock import AsyncMock, patch
from aiops.agents.disaster_recovery import (
    DisasterRecoveryAgent,
    DRPlan,
    RecoveryProcedure,
    BackupStrategy,
)


@pytest.fixture
def dr_agent():
    """Create disaster recovery agent."""
    return DisasterRecoveryAgent()


@pytest.fixture
def sample_infrastructure():
    """Sample infrastructure configuration."""
    return {
        "services": ["api-server", "database", "cache", "message-queue"],
        "databases": ["postgresql-primary", "postgresql-replica"],
        "storage": ["s3-bucket", "ebs-volumes"],
        "regions": ["us-east-1", "us-west-2"],
    }


@pytest.mark.asyncio
async def test_generate_dr_plan(dr_agent, sample_infrastructure):
    """Test DR plan generation."""
    mock_result = DRPlan(
        rto_minutes=30,
        rpo_minutes=5,
        recovery_procedures=[
            RecoveryProcedure(
                step=1,
                service="database",
                action="Failover to replica",
                estimated_time_minutes=5,
                automation_possible=True,
                commands=["pg_promote replica-db"],
            ),
            RecoveryProcedure(
                step=2,
                service="api-server",
                action="Update DNS to point to DR region",
                estimated_time_minutes=10,
                automation_possible=True,
            ),
        ],
        backup_strategies=[
            BackupStrategy(
                resource="postgresql-primary",
                backup_type="continuous",
                frequency="real-time",
                retention_days=30,
                storage_location="s3://dr-backups/db/",
            )
        ],
        estimated_cost_monthly=450.0,
        readiness_score=88.0,
    )

    with patch.object(
        dr_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await dr_agent.execute(infrastructure=sample_infrastructure, rto_target=30)

        assert isinstance(result, DRPlan)
        assert result.rto_minutes == 30
        assert len(result.recovery_procedures) == 2
        assert result.readiness_score == 88.0


@pytest.mark.asyncio
async def test_validate_dr_plan(dr_agent):
    """Test DR plan validation."""
    existing_plan = {
        "rto": 60,
        "rpo": 15,
        "procedures": ["manual_failover", "dns_update"],
    }

    mock_result = DRPlan(
        rto_minutes=60,
        rpo_minutes=15,
        recovery_procedures=[],
        backup_strategies=[],
        estimated_cost_monthly=0,
        readiness_score=65.0,
    )

    with patch.object(
        dr_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await dr_agent.validate_plan(plan=existing_plan)

        assert isinstance(result, DRPlan)
        assert result.readiness_score > 0


@pytest.mark.asyncio
async def test_backup_strategy_generation(dr_agent, sample_infrastructure):
    """Test backup strategy generation."""
    mock_result = DRPlan(
        rto_minutes=0,
        rpo_minutes=0,
        recovery_procedures=[],
        backup_strategies=[
            BackupStrategy(
                resource="postgresql-primary",
                backup_type="continuous",
                frequency="real-time",
                retention_days=30,
            ),
            BackupStrategy(
                resource="s3-bucket",
                backup_type="snapshot",
                frequency="daily",
                retention_days=90,
            ),
        ],
        estimated_cost_monthly=200.0,
        readiness_score=0,
    )

    with patch.object(
        dr_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await dr_agent.execute(infrastructure=sample_infrastructure)

        assert len(result.backup_strategies) == 2
        assert all(strategy.retention_days > 0 for strategy in result.backup_strategies)


@pytest.mark.asyncio
async def test_automation_opportunities(dr_agent, sample_infrastructure):
    """Test automation opportunity identification."""
    mock_result = DRPlan(
        rto_minutes=15,
        rpo_minutes=5,
        recovery_procedures=[
            RecoveryProcedure(
                step=1,
                service="api-server",
                action="Automated failover",
                estimated_time_minutes=2,
                automation_possible=True,
                commands=["aws route53 update-failover"],
            )
        ],
        backup_strategies=[],
        estimated_cost_monthly=0,
        readiness_score=92.0,
    )

    with patch.object(
        dr_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await dr_agent.execute(infrastructure=sample_infrastructure)

        automated_procedures = [
            proc for proc in result.recovery_procedures if proc.automation_possible
        ]
        assert len(automated_procedures) > 0


@pytest.mark.asyncio
async def test_error_handling(dr_agent):
    """Test error handling."""
    with patch.object(
        dr_agent,
        "_generate_structured_response",
        side_effect=Exception("Planning failed"),
    ):
        result = await dr_agent.execute(infrastructure={})

        assert isinstance(result, DRPlan)
        assert result.readiness_score == 0


def test_create_system_prompt(dr_agent):
    """Test system prompt creation."""
    prompt = dr_agent._create_system_prompt()

    assert "disaster recovery" in prompt.lower()
    assert "rto" in prompt.lower()
    assert "rpo" in prompt.lower()
