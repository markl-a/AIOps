"""
Unit tests for Release Manager Agent
"""

import pytest
from unittest.mock import AsyncMock
from aiops.agents.release_manager import (
    ReleaseManagerAgent,
    ReleaseChange,
    ReleaseRisk,
    RolloutStrategy,
    ValidationCheck,
    ReleasePlan
)


class TestReleaseChange:
    """Tests for ReleaseChange model"""

    def test_create_change(self):
        """Test creating a release change"""
        change = ReleaseChange(
            change_id="PR-123",
            type="feature",
            description="Add user authentication",
            risk_level="medium",
            impact_areas=["auth", "api", "frontend"],
            requires_migration=True,
            breaking_change=False
        )
        assert change.change_id == "PR-123"
        assert change.type == "feature"
        assert len(change.impact_areas) == 3
        assert change.requires_migration is True

    def test_change_types(self):
        """Test different change types"""
        for change_type in ["feature", "bugfix", "hotfix", "refactor"]:
            change = ReleaseChange(
                change_id="C1",
                type=change_type,
                description="Test",
                risk_level="low",
                impact_areas=[],
                requires_migration=False,
                breaking_change=False
            )
            assert change.type == change_type

    def test_change_risk_levels(self):
        """Test different risk levels"""
        for risk in ["low", "medium", "high", "critical"]:
            change = ReleaseChange(
                change_id="C1",
                type="feature",
                description="Test",
                risk_level=risk,
                impact_areas=[],
                requires_migration=False,
                breaking_change=False
            )
            assert change.risk_level == risk

    def test_breaking_change(self):
        """Test breaking change flag"""
        change = ReleaseChange(
            change_id="C1",
            type="feature",
            description="API v2 breaking changes",
            risk_level="high",
            impact_areas=["api"],
            requires_migration=True,
            breaking_change=True
        )
        assert change.breaking_change is True


class TestReleaseRisk:
    """Tests for ReleaseRisk model"""

    def test_create_risk(self):
        """Test creating a release risk"""
        risk = ReleaseRisk(
            risk_id="RISK-001",
            description="Database migration may cause downtime",
            category="technical",
            probability="medium",
            impact="high",
            mitigation="Test migration on staging first",
            monitoring="Monitor error rate and latency"
        )
        assert risk.risk_id == "RISK-001"
        assert risk.category == "technical"
        assert risk.impact == "high"

    def test_risk_categories(self):
        """Test different risk categories"""
        for category in ["technical", "operational", "business"]:
            risk = ReleaseRisk(
                risk_id="R1",
                description="Test",
                category=category,
                probability="low",
                impact="low",
                mitigation="",
                monitoring=""
            )
            assert risk.category == category


class TestRolloutStrategy:
    """Tests for RolloutStrategy model"""

    def test_create_canary_strategy(self):
        """Test creating canary rollout strategy"""
        strategy = RolloutStrategy(
            strategy_type="canary",
            phases=[
                {"name": "canary", "traffic_percent": 5},
                {"name": "partial", "traffic_percent": 25},
                {"name": "full", "traffic_percent": 100}
            ],
            success_criteria=["Error rate < 0.1%", "P99 latency < 200ms"],
            rollback_triggers=["Error rate > 1%", "P99 latency > 1s"],
            estimated_duration_minutes=60
        )
        assert strategy.strategy_type == "canary"
        assert len(strategy.phases) == 3
        assert len(strategy.success_criteria) == 2

    def test_strategy_types(self):
        """Test different strategy types"""
        for strategy_type in ["blue-green", "canary", "rolling", "big-bang"]:
            strategy = RolloutStrategy(
                strategy_type=strategy_type,
                phases=[],
                success_criteria=[],
                rollback_triggers=[],
                estimated_duration_minutes=30
            )
            assert strategy.strategy_type == strategy_type


class TestValidationCheck:
    """Tests for ValidationCheck model"""

    def test_create_validation(self):
        """Test creating a validation check"""
        check = ValidationCheck(
            check_id="CHK-001",
            name="Smoke Test",
            type="smoke",
            description="Basic functionality check",
            command="./run-smoke-tests.sh",
            expected_result="All tests pass",
            priority="critical"
        )
        assert check.check_id == "CHK-001"
        assert check.type == "smoke"
        assert check.priority == "critical"

    def test_validation_types(self):
        """Test different validation types"""
        for val_type in ["smoke", "functional", "performance", "security"]:
            check = ValidationCheck(
                check_id="C1",
                name="Test",
                type=val_type,
                description="",
                command=None,
                expected_result="Pass",
                priority="high"
            )
            assert check.type == val_type

    def test_validation_without_command(self):
        """Test validation without automated command"""
        check = ValidationCheck(
            check_id="C1",
            name="Manual Check",
            type="functional",
            description="Manually verify UI",
            command=None,
            expected_result="UI works correctly",
            priority="medium"
        )
        assert check.command is None


class TestReleasePlan:
    """Tests for ReleasePlan model"""

    def test_create_plan(self):
        """Test creating a release plan"""
        strategy = RolloutStrategy(
            strategy_type="canary",
            phases=[{"name": "full", "percent": 100}],
            success_criteria=[],
            rollback_triggers=[],
            estimated_duration_minutes=30
        )
        plan = ReleasePlan(
            release_id="REL-001",
            version="v2.5.0",
            release_date="2024-01-20 10:00:00",
            environment="production",
            changes=[],
            risks=[],
            risk_score=25.0,
            rollout_strategy=strategy,
            validation_checks=[],
            rollback_plan="Revert to v2.4.1",
            communication_plan=["Notify stakeholders"],
            dependencies=["Database v5.0"],
            team_assignments={"lead": ["Alice"], "support": ["Bob"]},
            go_no_go_criteria=["All tests pass"],
            executive_summary="Regular release"
        )
        assert plan.version == "v2.5.0"
        assert plan.risk_score == 25.0
        assert plan.environment == "production"

    def test_plan_with_full_data(self):
        """Test plan with all components"""
        change = ReleaseChange(
            change_id="PR-1",
            type="feature",
            description="New feature",
            risk_level="low",
            impact_areas=["api"],
            requires_migration=False,
            breaking_change=False
        )
        risk = ReleaseRisk(
            risk_id="R1",
            description="Risk",
            category="technical",
            probability="low",
            impact="low",
            mitigation="Mitigate",
            monitoring="Monitor"
        )
        check = ValidationCheck(
            check_id="C1",
            name="Test",
            type="smoke",
            description="",
            command=None,
            expected_result="Pass",
            priority="high"
        )
        strategy = RolloutStrategy(
            strategy_type="rolling",
            phases=[],
            success_criteria=[],
            rollback_triggers=[],
            estimated_duration_minutes=45
        )
        plan = ReleasePlan(
            release_id="REL-002",
            version="v3.0.0",
            release_date="2024-02-01",
            environment="production",
            changes=[change],
            risks=[risk],
            risk_score=15.0,
            rollout_strategy=strategy,
            validation_checks=[check],
            rollback_plan="Rollback",
            communication_plan=[],
            dependencies=[],
            team_assignments={},
            go_no_go_criteria=[],
            executive_summary="Major release"
        )
        assert len(plan.changes) == 1
        assert len(plan.risks) == 1
        assert len(plan.validation_checks) == 1


class TestReleaseManagerAgent:
    """Tests for ReleaseManagerAgent"""

    @pytest.fixture
    def agent(self):
        """Create agent instance"""
        return ReleaseManagerAgent()

    @pytest.fixture
    def mock_plan_response(self):
        """Mock plan response from LLM"""
        return {
            "changes": [
                {
                    "change_id": "PR-100",
                    "type": "feature",
                    "description": "New dashboard",
                    "risk_level": "medium",
                    "impact_areas": ["frontend", "api"],
                    "requires_migration": False,
                    "breaking_change": False
                }
            ],
            "risks": [
                {
                    "risk_id": "R1",
                    "description": "Frontend performance",
                    "category": "technical",
                    "probability": "low",
                    "impact": "medium",
                    "mitigation": "Load testing",
                    "monitoring": "Monitor page load times"
                }
            ],
            "risk_score": 35.0,
            "rollout_strategy": {
                "strategy_type": "canary",
                "phases": [
                    {"name": "canary", "percent": 5},
                    {"name": "full", "percent": 100}
                ],
                "success_criteria": ["Error rate < 0.5%"],
                "rollback_triggers": ["Error rate > 2%"],
                "estimated_duration_minutes": 60
            },
            "validation_checks": [
                {
                    "check_id": "CHK1",
                    "name": "Smoke Test",
                    "type": "smoke",
                    "description": "Basic checks",
                    "command": "./smoke.sh",
                    "expected_result": "Pass",
                    "priority": "critical"
                }
            ],
            "rollback_plan": "Revert deployment",
            "communication_plan": ["Email stakeholders"],
            "dependencies": [],
            "team_assignments": {"release_lead": ["Alice"]},
            "go_no_go_criteria": ["Tests pass", "Staging verified"],
            "executive_summary": "Feature release"
        }

    @pytest.mark.asyncio
    async def test_execute_basic(self, agent, mock_plan_response):
        """Test basic execution"""
        agent._generate_structured_response = AsyncMock(return_value=mock_plan_response)

        changes = [{"type": "feature", "description": "New feature"}]

        plan = await agent.execute(
            version="v1.0.0",
            release_date="2024-01-15 10:00",
            environment="production",
            changes=changes
        )

        assert isinstance(plan, ReleasePlan)
        assert plan.version == "v1.0.0"
        assert len(plan.changes) > 0

    @pytest.mark.asyncio
    async def test_execute_with_metrics(self, agent, mock_plan_response):
        """Test execution with previous release metrics"""
        agent._generate_structured_response = AsyncMock(return_value=mock_plan_response)

        prev_metrics = {"success_rate": 99.5, "rollback_rate": 2.0}

        await agent.execute(
            version="v2.0.0",
            release_date="2024-01-20",
            environment="production",
            changes=[{"type": "feature", "description": "Test"}],
            previous_release_metrics=prev_metrics
        )

        call_args = agent._generate_structured_response.call_args
        prompt = call_args[0][0]
        assert "Previous Release Metrics" in prompt

    @pytest.mark.asyncio
    async def test_execute_with_infrastructure(self, agent, mock_plan_response):
        """Test execution with infrastructure details"""
        agent._generate_structured_response = AsyncMock(return_value=mock_plan_response)

        infra = {"kubernetes": True, "replicas": 5}

        await agent.execute(
            version="v2.0.0",
            release_date="2024-01-20",
            environment="staging",
            changes=[],
            infrastructure_details=infra
        )

        call_args = agent._generate_structured_response.call_args
        prompt = call_args[0][0]
        assert "Infrastructure" in prompt

    @pytest.mark.asyncio
    async def test_execute_with_traffic_pattern(self, agent, mock_plan_response):
        """Test execution with traffic pattern"""
        agent._generate_structured_response = AsyncMock(return_value=mock_plan_response)

        traffic = {"peak_hours": "9-17", "daily_users": 100000}

        await agent.execute(
            version="v2.0.0",
            release_date="2024-01-20",
            environment="production",
            changes=[],
            user_traffic_pattern=traffic
        )

        call_args = agent._generate_structured_response.call_args
        prompt = call_args[0][0]
        assert "Traffic" in prompt

    def test_build_planning_prompt(self, agent):
        """Test prompt building"""
        changes = [
            {"type": "feature", "description": "Feature 1"},
            {"type": "bugfix", "description": "Bug fix 1"}
        ]

        prompt = agent._build_planning_prompt(
            version="v1.0.0",
            release_date="2024-01-15",
            environment="production",
            changes=changes,
            previous_release_metrics=None,
            infrastructure_details=None,
            user_traffic_pattern=None
        )

        assert "v1.0.0" in prompt
        assert "2024-01-15" in prompt
        assert "production" in prompt
        assert "Feature 1" in prompt
        assert "Bug fix 1" in prompt
        assert "Rollback" in prompt

    @pytest.mark.asyncio
    async def test_assess_go_no_go(self, agent):
        """Test go/no-go assessment"""
        strategy = RolloutStrategy(
            strategy_type="canary",
            phases=[],
            success_criteria=[],
            rollback_triggers=[],
            estimated_duration_minutes=30
        )
        plan = ReleasePlan(
            release_id="REL-001",
            version="v1.0.0",
            release_date="2024-01-15 10:00",
            environment="production",
            changes=[],
            risks=[],
            risk_score=20.0,
            rollout_strategy=strategy,
            validation_checks=[],
            rollback_plan="Rollback",
            communication_plan=[],
            dependencies=[],
            team_assignments={},
            go_no_go_criteria=["Tests pass", "Staging OK"],
            executive_summary="Test"
        )

        agent._generate_response = AsyncMock(
            return_value="GO - All criteria met. Confidence: 95%"
        )

        result = await agent.assess_go_no_go(
            release_plan=plan,
            current_system_health={"status": "healthy", "error_rate": 0.01},
            pre_release_test_results={"passed": 100, "failed": 0}
        )

        assert "recommendation" in result
        assert "assessed_at" in result
        assert "release_id" in result
        assert "GO" in result["recommendation"]

    def test_agent_initialization(self):
        """Test agent initialization"""
        agent = ReleaseManagerAgent()
        assert agent.name == "ReleaseManager"

    def test_agent_inherits_from_base(self):
        """Test agent inherits from BaseAgent"""
        from aiops.agents.base_agent import BaseAgent
        agent = ReleaseManagerAgent()
        assert isinstance(agent, BaseAgent)


class TestReleaseManagerEdgeCases:
    """Edge case tests"""

    @pytest.fixture
    def agent(self):
        return ReleaseManagerAgent()

    @pytest.mark.asyncio
    async def test_empty_changes(self, agent):
        """Test with no changes"""
        agent._generate_structured_response = AsyncMock(return_value={
            "changes": [],
            "risks": [],
            "risk_score": 0.0,
            "rollout_strategy": {
                "strategy_type": "big-bang",
                "phases": [],
                "success_criteria": [],
                "rollback_triggers": [],
                "estimated_duration_minutes": 5
            },
            "rollback_plan": "No rollback needed",
            "executive_summary": "No changes"
        })

        plan = await agent.execute(
            version="v1.0.1",
            release_date="2024-01-15",
            environment="staging",
            changes=[]
        )

        assert len(plan.changes) == 0
        assert plan.risk_score == 0.0

    @pytest.mark.asyncio
    async def test_high_risk_release(self, agent):
        """Test high risk release"""
        agent._generate_structured_response = AsyncMock(return_value={
            "changes": [
                {
                    "change_id": "PR-1",
                    "type": "feature",
                    "description": "Major architecture change",
                    "risk_level": "critical",
                    "impact_areas": ["all"],
                    "requires_migration": True,
                    "breaking_change": True
                }
            ],
            "risks": [
                {
                    "risk_id": "R1",
                    "description": "Data loss risk",
                    "category": "technical",
                    "probability": "medium",
                    "impact": "critical",
                    "mitigation": "Full backup",
                    "monitoring": "Monitor data integrity"
                }
            ],
            "risk_score": 85.0,
            "rollout_strategy": {
                "strategy_type": "canary",
                "phases": [
                    {"name": "canary", "percent": 1},
                    {"name": "expand", "percent": 5},
                    {"name": "full", "percent": 100}
                ],
                "success_criteria": ["Zero data loss", "Error rate < 0.01%"],
                "rollback_triggers": ["Any data corruption"],
                "estimated_duration_minutes": 180
            },
            "rollback_plan": "Immediate rollback and restore from backup",
            "executive_summary": "High-risk release requiring careful monitoring"
        })

        plan = await agent.execute(
            version="v2.0.0",
            release_date="2024-02-01 02:00",
            environment="production",
            changes=[{"type": "feature", "description": "Major change"}]
        )

        assert plan.risk_score >= 80
        assert plan.changes[0].breaking_change is True
        assert plan.rollout_strategy.strategy_type == "canary"

    @pytest.mark.asyncio
    async def test_multiple_environments(self, agent):
        """Test release to different environments"""
        base_response = {
            "changes": [],
            "risks": [],
            "risk_score": 10.0,
            "rollout_strategy": {
                "strategy_type": "rolling",
                "phases": [],
                "success_criteria": [],
                "rollback_triggers": [],
                "estimated_duration_minutes": 15
            },
            "rollback_plan": "",
            "executive_summary": ""
        }

        agent._generate_structured_response = AsyncMock(return_value=base_response)

        for env in ["development", "staging", "production"]:
            plan = await agent.execute(
                version="v1.0.0",
                release_date="2024-01-15",
                environment=env,
                changes=[]
            )
            assert plan.environment == env

    @pytest.mark.asyncio
    async def test_go_no_go_with_failing_tests(self, agent):
        """Test go/no-go with failing tests"""
        strategy = RolloutStrategy(
            strategy_type="canary",
            phases=[],
            success_criteria=[],
            rollback_triggers=[],
            estimated_duration_minutes=30
        )
        plan = ReleasePlan(
            release_id="REL-001",
            version="v1.0.0",
            release_date="2024-01-15",
            environment="production",
            changes=[],
            risks=[],
            risk_score=50.0,
            rollout_strategy=strategy,
            validation_checks=[],
            rollback_plan="",
            communication_plan=[],
            dependencies=[],
            team_assignments={},
            go_no_go_criteria=["All tests must pass"],
            executive_summary=""
        )

        agent._generate_response = AsyncMock(
            return_value="NO-GO - 5 tests failing. Must fix before proceeding."
        )

        result = await agent.assess_go_no_go(
            release_plan=plan,
            current_system_health={"status": "healthy"},
            pre_release_test_results={"passed": 95, "failed": 5}
        )

        assert "NO-GO" in result["recommendation"]

    @pytest.mark.asyncio
    async def test_many_changes(self, agent):
        """Test release with many changes"""
        changes = [
            {
                "change_id": f"PR-{i}",
                "type": "feature" if i % 2 == 0 else "bugfix",
                "description": f"Change {i}",
                "risk_level": "low",
                "impact_areas": [f"area-{i % 5}"],
                "requires_migration": False,
                "breaking_change": False
            }
            for i in range(50)
        ]

        agent._generate_structured_response = AsyncMock(return_value={
            "changes": changes,
            "risks": [],
            "risk_score": 45.0,
            "rollout_strategy": {
                "strategy_type": "canary",
                "phases": [],
                "success_criteria": [],
                "rollback_triggers": [],
                "estimated_duration_minutes": 120
            },
            "rollback_plan": "Staged rollback",
            "executive_summary": "Large release with 50 changes"
        })

        plan = await agent.execute(
            version="v3.0.0",
            release_date="2024-03-01",
            environment="production",
            changes=[{"type": "feature", "description": f"Change {i}"} for i in range(50)]
        )

        assert len(plan.changes) == 50
