"""
Unit tests for Migration Planner Agent
"""

import pytest
from unittest.mock import AsyncMock, patch
from aiops.agents.migration_planner import (
    MigrationPlannerAgent,
    MigrationPhase,
    MigrationRisk,
    MigrationTestCase,
    MigrationPlan
)


class TestMigrationPhase:
    """Tests for MigrationPhase model"""

    def test_create_phase(self):
        """Test creating a migration phase"""
        phase = MigrationPhase(
            phase_number=1,
            name="Assessment",
            duration_days=5,
            tasks=["Audit current systems", "Document dependencies"],
            dependencies=[],
            success_criteria=["All systems documented"],
            rollback_procedure="Revert documentation",
            risk_level="low"
        )
        assert phase.phase_number == 1
        assert phase.name == "Assessment"
        assert phase.duration_days == 5
        assert len(phase.tasks) == 2

    def test_phase_risk_levels(self):
        """Test different risk levels"""
        for risk_level in ["low", "medium", "high", "critical"]:
            phase = MigrationPhase(
                phase_number=1,
                name="Test",
                duration_days=1,
                tasks=[],
                dependencies=[],
                success_criteria=[],
                rollback_procedure="",
                risk_level=risk_level
            )
            assert phase.risk_level == risk_level

    def test_phase_with_dependencies(self):
        """Test phase with dependencies"""
        phase = MigrationPhase(
            phase_number=2,
            name="Implementation",
            duration_days=10,
            tasks=["Deploy new infrastructure"],
            dependencies=["Phase 1: Assessment"],
            success_criteria=["Infrastructure operational"],
            rollback_procedure="Destroy new infrastructure",
            risk_level="medium"
        )
        assert len(phase.dependencies) == 1
        assert "Phase 1" in phase.dependencies[0]


class TestMigrationRisk:
    """Tests for MigrationRisk model"""

    def test_create_risk(self):
        """Test creating a migration risk"""
        risk = MigrationRisk(
            risk_id="RISK-001",
            category="technical",
            description="Data loss during migration",
            probability="medium",
            impact="critical",
            mitigation="Full backup before migration",
            contingency="Restore from backup"
        )
        assert risk.risk_id == "RISK-001"
        assert risk.category == "technical"
        assert risk.impact == "critical"

    def test_risk_categories(self):
        """Test different risk categories"""
        for category in ["technical", "operational", "business"]:
            risk = MigrationRisk(
                risk_id="R1",
                category=category,
                description="Test",
                probability="low",
                impact="low",
                mitigation="Mitigate",
                contingency="Contingency"
            )
            assert risk.category == category

    def test_risk_probabilities(self):
        """Test different probabilities"""
        for probability in ["low", "medium", "high"]:
            risk = MigrationRisk(
                risk_id="R1",
                category="technical",
                description="Test",
                probability=probability,
                impact="medium",
                mitigation="Mitigate",
                contingency="Contingency"
            )
            assert risk.probability == probability


class TestMigrationTestCase:
    """Tests for MigrationTestCase model"""

    def test_create_test_case(self):
        """Test creating a test case"""
        test_case = MigrationTestCase(
            test_id="TC-001",
            name="Data Integrity Check",
            type="data integrity",
            description="Verify all data migrated correctly",
            expected_result="100% data match",
            priority="critical"
        )
        assert test_case.test_id == "TC-001"
        assert test_case.type == "data integrity"
        assert test_case.priority == "critical"

    def test_test_types(self):
        """Test different test types"""
        for test_type in ["functional", "performance", "data integrity"]:
            test_case = MigrationTestCase(
                test_id="TC",
                name="Test",
                type=test_type,
                description="Description",
                expected_result="Pass",
                priority="high"
            )
            assert test_case.type == test_type


class TestMigrationPlan:
    """Tests for MigrationPlan model"""

    def test_create_plan(self):
        """Test creating a migration plan"""
        plan = MigrationPlan(
            plan_id="MIG-001",
            migration_type="cloud-migration",
            source_environment="On-premise",
            target_environment="AWS",
            estimated_duration_days=90,
            total_cost_estimate=50000.0,
            phases=[],
            risks=[],
            test_cases=[],
            success_metrics=["Zero downtime", "All data migrated"],
            rollback_strategy="Revert DNS to on-premise",
            resource_requirements={"engineers": 5},
            communication_plan=["Weekly updates"],
            executive_summary="Cloud migration plan"
        )
        assert plan.plan_id == "MIG-001"
        assert plan.migration_type == "cloud-migration"
        assert plan.estimated_duration_days == 90
        assert plan.total_cost_estimate == 50000.0

    def test_plan_with_phases_and_risks(self):
        """Test plan with phases and risks"""
        phase = MigrationPhase(
            phase_number=1,
            name="Prep",
            duration_days=10,
            tasks=["Prepare"],
            dependencies=[],
            success_criteria=["Ready"],
            rollback_procedure="Undo",
            risk_level="low"
        )
        risk = MigrationRisk(
            risk_id="R1",
            category="technical",
            description="Risk",
            probability="low",
            impact="medium",
            mitigation="Mitigate",
            contingency="Fallback"
        )
        plan = MigrationPlan(
            plan_id="MIG-002",
            migration_type="database-migration",
            source_environment="MySQL",
            target_environment="PostgreSQL",
            estimated_duration_days=30,
            total_cost_estimate=10000.0,
            phases=[phase],
            risks=[risk],
            test_cases=[],
            success_metrics=[],
            rollback_strategy="Switch back to MySQL",
            resource_requirements={},
            communication_plan=[],
            executive_summary="DB migration"
        )
        assert len(plan.phases) == 1
        assert len(plan.risks) == 1


class TestMigrationPlannerAgent:
    """Tests for MigrationPlannerAgent"""

    @pytest.fixture
    def agent(self):
        """Create agent instance"""
        return MigrationPlannerAgent()

    @pytest.fixture
    def mock_plan_response(self):
        """Mock plan response from LLM"""
        return {
            "migration_type": "cloud-migration",
            "source_environment": "On-premise DC",
            "target_environment": "AWS us-east-1",
            "estimated_duration_days": 60,
            "total_cost_estimate": 75000.0,
            "phases": [
                {
                    "phase_number": 1,
                    "name": "Discovery",
                    "duration_days": 10,
                    "tasks": ["Inventory systems", "Map dependencies"],
                    "dependencies": [],
                    "success_criteria": ["All systems documented"],
                    "rollback_procedure": "Archive documentation",
                    "risk_level": "low"
                }
            ],
            "risks": [
                {
                    "risk_id": "R1",
                    "category": "technical",
                    "description": "Network connectivity issues",
                    "probability": "medium",
                    "impact": "high",
                    "mitigation": "Test connectivity beforehand",
                    "contingency": "Use VPN fallback"
                }
            ],
            "test_cases": [
                {
                    "test_id": "TC1",
                    "name": "Connectivity Test",
                    "type": "functional",
                    "description": "Test network connectivity",
                    "expected_result": "All services reachable",
                    "priority": "critical"
                }
            ],
            "success_metrics": ["Zero data loss", "99.9% uptime"],
            "rollback_strategy": "Failover to on-premise",
            "resource_requirements": {"engineers": 4, "tools": ["terraform"]},
            "communication_plan": ["Daily standup", "Weekly exec summary"],
            "executive_summary": "Cloud migration to AWS"
        }

    @pytest.mark.asyncio
    async def test_execute_cloud_migration(self, agent, mock_plan_response):
        """Test cloud migration planning"""
        agent._generate_structured_response = AsyncMock(return_value=mock_plan_response)

        source = {"type": "datacenter", "location": "NYC"}
        target = {"provider": "AWS", "region": "us-east-1"}

        plan = await agent.execute(
            migration_type="cloud-migration",
            source_environment=source,
            target_environment=target
        )

        assert isinstance(plan, MigrationPlan)
        assert "cloud" in plan.migration_type
        assert len(plan.phases) > 0
        assert len(plan.risks) > 0

    @pytest.mark.asyncio
    async def test_execute_with_constraints(self, agent, mock_plan_response):
        """Test planning with constraints"""
        agent._generate_structured_response = AsyncMock(return_value=mock_plan_response)

        constraints = {"max_downtime": "4 hours", "budget": 100000}

        await agent.execute(
            migration_type="database-migration",
            source_environment={"type": "MySQL"},
            target_environment={"type": "PostgreSQL"},
            constraints=constraints
        )

        call_args = agent._generate_structured_response.call_args
        prompt = call_args[0][0]
        assert "max_downtime" in prompt or "budget" in prompt

    @pytest.mark.asyncio
    async def test_execute_with_requirements(self, agent, mock_plan_response):
        """Test planning with business and technical requirements"""
        agent._generate_structured_response = AsyncMock(return_value=mock_plan_response)

        business_reqs = {"sla": "99.9%", "compliance": "SOC2"}
        technical_reqs = {"encryption": "required", "backup": "daily"}

        await agent.execute(
            migration_type="platform-migration",
            source_environment={},
            target_environment={},
            business_requirements=business_reqs,
            technical_requirements=technical_reqs
        )

        call_args = agent._generate_structured_response.call_args
        prompt = call_args[0][0]
        assert "sla" in prompt.lower() or "encryption" in prompt.lower()

    def test_migration_types(self, agent):
        """Test supported migration types"""
        expected_types = [
            "cloud-migration",
            "database-migration",
            "monolith-to-microservices",
            "platform-migration",
            "data-center-migration",
            "version-upgrade",
            "provider-switch"
        ]
        for migration_type in expected_types:
            assert migration_type in agent.MIGRATION_TYPES

    def test_build_planning_prompt(self, agent):
        """Test prompt building"""
        prompt = agent._build_planning_prompt(
            migration_type="cloud-migration",
            source_environment={"type": "on-premise"},
            target_environment={"provider": "AWS"},
            constraints={"budget": 50000},
            business_requirements={"sla": "99.9%"},
            technical_requirements={"encryption": True}
        )

        assert "cloud-migration" in prompt
        assert "on-premise" in prompt
        assert "AWS" in prompt
        assert "budget" in prompt
        assert "Rollback Strategy" in prompt

    @pytest.mark.asyncio
    async def test_generate_runbook(self, agent):
        """Test runbook generation"""
        phase = MigrationPhase(
            phase_number=1,
            name="Data Migration",
            duration_days=5,
            tasks=["Export data", "Import data", "Verify integrity"],
            dependencies=[],
            success_criteria=["All data transferred"],
            rollback_procedure="Restore from backup",
            risk_level="medium"
        )
        plan = MigrationPlan(
            plan_id="MIG-001",
            migration_type="database-migration",
            source_environment="MySQL",
            target_environment="PostgreSQL",
            estimated_duration_days=30,
            total_cost_estimate=10000.0,
            phases=[phase],
            risks=[],
            test_cases=[],
            success_metrics=[],
            rollback_strategy="Failback",
            resource_requirements={},
            communication_plan=[],
            executive_summary="Test"
        )

        agent._generate_response = AsyncMock(
            return_value="# Runbook for Phase 1: Data Migration\n..."
        )

        runbook = await agent.generate_runbook(plan, phase_number=1)

        assert runbook is not None
        assert "Data Migration" in runbook or "Runbook" in runbook

    @pytest.mark.asyncio
    async def test_generate_runbook_phase_not_found(self, agent):
        """Test runbook generation with invalid phase number"""
        plan = MigrationPlan(
            plan_id="MIG-001",
            migration_type="test",
            source_environment="",
            target_environment="",
            estimated_duration_days=1,
            total_cost_estimate=0,
            phases=[],
            risks=[],
            test_cases=[],
            success_metrics=[],
            rollback_strategy="",
            resource_requirements={},
            communication_plan=[],
            executive_summary=""
        )

        with pytest.raises(ValueError, match="Phase 99 not found"):
            await agent.generate_runbook(plan, phase_number=99)

    def test_agent_initialization(self):
        """Test agent initialization"""
        agent = MigrationPlannerAgent()
        assert agent.name == "MigrationPlanner"

    def test_agent_inherits_from_base(self):
        """Test agent inherits from BaseAgent"""
        from aiops.agents.base_agent import BaseAgent
        agent = MigrationPlannerAgent()
        assert isinstance(agent, BaseAgent)


class TestMigrationPlannerEdgeCases:
    """Edge case tests"""

    @pytest.fixture
    def agent(self):
        return MigrationPlannerAgent()

    @pytest.mark.asyncio
    async def test_empty_environments(self, agent):
        """Test with empty environments"""
        agent._generate_structured_response = AsyncMock(return_value={
            "migration_type": "unknown",
            "phases": [],
            "risks": [],
            "rollback_strategy": "",
            "executive_summary": "Empty migration"
        })

        plan = await agent.execute(
            migration_type="cloud-migration",
            source_environment={},
            target_environment={}
        )

        assert plan is not None

    @pytest.mark.asyncio
    async def test_complex_migration(self, agent):
        """Test complex multi-phase migration"""
        phases = [
            {
                "phase_number": i,
                "name": f"Phase {i}",
                "duration_days": 10,
                "tasks": [f"Task {i}"],
                "dependencies": [f"Phase {i-1}"] if i > 1 else [],
                "success_criteria": [f"Criterion {i}"],
                "rollback_procedure": f"Rollback {i}",
                "risk_level": "medium"
            }
            for i in range(1, 6)
        ]

        agent._generate_structured_response = AsyncMock(return_value={
            "migration_type": "monolith-to-microservices",
            "estimated_duration_days": 180,
            "total_cost_estimate": 500000.0,
            "phases": phases,
            "risks": [],
            "rollback_strategy": "Staged rollback",
            "executive_summary": "Complex migration"
        })

        plan = await agent.execute(
            migration_type="monolith-to-microservices",
            source_environment={"type": "monolith"},
            target_environment={"type": "microservices"}
        )

        assert len(plan.phases) == 5
        assert plan.estimated_duration_days == 180
