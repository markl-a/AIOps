"""
Migration Planner Agent

This agent helps plan and execute complex migrations (cloud, platform,
database, monolith-to-microservices, etc.) with risk assessment and rollback strategies.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from aiops.agents.base_agent import BaseAgent
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class MigrationPhase(BaseModel):
    """Single phase in migration plan"""
    phase_number: int = Field(description="Phase sequence number")
    name: str = Field(description="Phase name")
    duration_days: int = Field(description="Estimated duration in days")
    tasks: List[str] = Field(description="Tasks to complete")
    dependencies: List[str] = Field(description="Dependencies on other phases")
    success_criteria: List[str] = Field(description="Success criteria")
    rollback_procedure: str = Field(description="Rollback procedure if needed")
    risk_level: str = Field(description="Risk level: low, medium, high, critical")


class MigrationRisk(BaseModel):
    """Identified migration risk"""
    risk_id: str = Field(description="Risk identifier")
    category: str = Field(description="Risk category")
    description: str = Field(description="Risk description")
    probability: str = Field(description="Likelihood: low, medium, high")
    impact: str = Field(description="Impact: low, medium, high, critical")
    mitigation: str = Field(description="Mitigation strategy")
    contingency: str = Field(description="Contingency plan")


class MigrationTestCase(BaseModel):
    """Test case for migration validation"""
    test_id: str = Field(description="Test case identifier")
    name: str = Field(description="Test name")
    type: str = Field(description="Test type: functional, performance, data integrity")
    description: str = Field(description="Test description")
    expected_result: str = Field(description="Expected result")
    priority: str = Field(description="Priority: critical, high, medium, low")


class MigrationPlan(BaseModel):
    """Complete migration plan"""
    plan_id: str = Field(description="Unique plan identifier")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    migration_type: str = Field(description="Type of migration")
    source_environment: str = Field(description="Source environment description")
    target_environment: str = Field(description="Target environment description")
    estimated_duration_days: int = Field(description="Total estimated duration")
    total_cost_estimate: float = Field(description="Estimated cost in USD")
    phases: List[MigrationPhase] = Field(description="Migration phases")
    risks: List[MigrationRisk] = Field(description="Identified risks")
    test_cases: List[MigrationTestCase] = Field(description="Test cases")
    success_metrics: List[str] = Field(description="Overall success metrics")
    rollback_strategy: str = Field(description="Overall rollback strategy")
    resource_requirements: Dict[str, Any] = Field(description="Required resources")
    communication_plan: List[str] = Field(description="Stakeholder communication")
    executive_summary: str = Field(description="Executive summary")


class MigrationPlannerAgent(BaseAgent):
    """
    AI-powered migration planner.

    Features:
    - Cloud migration planning (AWS, Azure, GCP)
    - Database migration strategies
    - Monolith to microservices decomposition
    - Platform migrations (Kubernetes, serverless)
    - Data center migrations
    - Risk assessment and mitigation
    - Rollback planning
    """

    MIGRATION_TYPES = [
        "cloud-migration",
        "database-migration",
        "monolith-to-microservices",
        "platform-migration",
        "data-center-migration",
        "version-upgrade",
        "provider-switch",
    ]

    def __init__(
        self,
        llm_provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = 0.3,
    ):
        super().__init__(
            name="MigrationPlanner",
            llm_provider=llm_provider,
            model=model,
            temperature=temperature,
        )

    async def execute(
        self,
        migration_type: str,
        source_environment: Dict[str, Any],
        target_environment: Dict[str, Any],
        constraints: Optional[Dict[str, Any]] = None,
        business_requirements: Optional[Dict[str, Any]] = None,
        technical_requirements: Optional[Dict[str, Any]] = None,
    ) -> MigrationPlan:
        """
        Create a detailed migration plan.

        Args:
            migration_type: Type of migration
            source_environment: Current environment details
            target_environment: Target environment details
            constraints: Time, budget, or other constraints
            business_requirements: Business requirements and SLAs
            technical_requirements: Technical requirements

        Returns:
            MigrationPlan with phases, risks, and strategies
        """
        logger.info(f"Creating {migration_type} migration plan")

        # Build migration planning prompt
        prompt = self._build_planning_prompt(
            migration_type, source_environment, target_environment,
            constraints, business_requirements, technical_requirements
        )

        # Define response schema
        schema = {
            "type": "object",
            "properties": {
                "migration_type": {"type": "string"},
                "source_environment": {"type": "string"},
                "target_environment": {"type": "string"},
                "estimated_duration_days": {"type": "integer"},
                "total_cost_estimate": {"type": "number"},
                "phases": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "phase_number": {"type": "integer"},
                            "name": {"type": "string"},
                            "duration_days": {"type": "integer"},
                            "tasks": {"type": "array", "items": {"type": "string"}},
                            "dependencies": {"type": "array", "items": {"type": "string"}},
                            "success_criteria": {"type": "array", "items": {"type": "string"}},
                            "rollback_procedure": {"type": "string"},
                            "risk_level": {"type": "string"},
                        },
                    },
                },
                "risks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "risk_id": {"type": "string"},
                            "category": {"type": "string"},
                            "description": {"type": "string"},
                            "probability": {"type": "string"},
                            "impact": {"type": "string"},
                            "mitigation": {"type": "string"},
                            "contingency": {"type": "string"},
                        },
                    },
                },
                "test_cases": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "test_id": {"type": "string"},
                            "name": {"type": "string"},
                            "type": {"type": "string"},
                            "description": {"type": "string"},
                            "expected_result": {"type": "string"},
                            "priority": {"type": "string"},
                        },
                    },
                },
                "success_metrics": {"type": "array", "items": {"type": "string"}},
                "rollback_strategy": {"type": "string"},
                "resource_requirements": {"type": "object"},
                "communication_plan": {"type": "array", "items": {"type": "string"}},
                "executive_summary": {"type": "string"},
            },
            "required": [
                "migration_type", "phases", "risks", "rollback_strategy", "executive_summary"
            ],
        }

        # Generate migration plan
        system_prompt = """You are an expert migration architect with experience in cloud, database,
        and platform migrations. Create comprehensive, risk-aware migration plans with clear phases,
        rollback strategies, and success criteria. Consider dependencies, downtime requirements,
        and business continuity."""

        response = await self._generate_structured_response(prompt, schema, system_prompt)

        # Create plan
        plan = MigrationPlan(
            plan_id=f"MIG-{migration_type}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            migration_type=response.get("migration_type", migration_type),
            source_environment=response.get("source_environment", str(source_environment)),
            target_environment=response.get("target_environment", str(target_environment)),
            estimated_duration_days=response.get("estimated_duration_days", 0),
            total_cost_estimate=response.get("total_cost_estimate", 0.0),
            phases=[MigrationPhase(**p) for p in response.get("phases", [])],
            risks=[MigrationRisk(**r) for r in response.get("risks", [])],
            test_cases=[MigrationTestCase(**t) for t in response.get("test_cases", [])],
            success_metrics=response.get("success_metrics", []),
            rollback_strategy=response.get("rollback_strategy", ""),
            resource_requirements=response.get("resource_requirements", {}),
            communication_plan=response.get("communication_plan", []),
            executive_summary=response.get("executive_summary", ""),
        )

        logger.info(
            f"Migration plan created: {len(plan.phases)} phases, "
            f"{plan.estimated_duration_days} days, {len(plan.risks)} risks identified"
        )

        return plan

    def _build_planning_prompt(
        self,
        migration_type: str,
        source_environment: Dict[str, Any],
        target_environment: Dict[str, Any],
        constraints: Optional[Dict[str, Any]],
        business_requirements: Optional[Dict[str, Any]],
        technical_requirements: Optional[Dict[str, Any]],
    ) -> str:
        """Build migration planning prompt"""
        prompt_parts = [
            f"# Migration Planning Request\n\n",
            f"## Migration Type\n{migration_type}\n\n",
            f"## Source Environment\n```yaml\n{source_environment}\n```\n\n",
            f"## Target Environment\n```yaml\n{target_environment}\n```\n\n",
        ]

        if constraints:
            prompt_parts.append(f"## Constraints\n")
            for key, value in constraints.items():
                prompt_parts.append(f"- **{key}**: {value}\n")
            prompt_parts.append("\n")

        if business_requirements:
            prompt_parts.append(f"## Business Requirements\n")
            for key, value in business_requirements.items():
                prompt_parts.append(f"- **{key}**: {value}\n")
            prompt_parts.append("\n")

        if technical_requirements:
            prompt_parts.append(f"## Technical Requirements\n```yaml\n{technical_requirements}\n```\n\n")

        prompt_parts.append("""
## Planning Requirements

Create a comprehensive migration plan including:

### 1. Phased Approach
- Break migration into manageable phases
- Define clear deliverables and success criteria for each phase
- Identify dependencies between phases
- Include rollback procedures for each phase

### 2. Risk Assessment
- Identify technical, operational, and business risks
- Assess probability and impact
- Provide mitigation strategies
- Create contingency plans

### 3. Testing Strategy
- Functional testing (features work correctly)
- Performance testing (meets SLAs)
- Data integrity testing (no data loss/corruption)
- Disaster recovery testing

### 4. Rollback Strategy
- Decision criteria for rollback
- Step-by-step rollback procedures
- Data synchronization during rollback
- Communication during rollback

### 5. Resource Planning
- Team composition and roles
- Tool and infrastructure requirements
- Training needs
- Budget allocation

### 6. Success Metrics
- Technical metrics (performance, availability)
- Business metrics (cost, user satisfaction)
- Validation checkpoints

### 7. Communication Plan
- Stakeholder updates
- Team coordination
- User communications
- Escalation procedures

Ensure the plan is:
- Realistic and achievable
- Risk-aware with clear mitigation
- Focused on zero downtime (or minimal downtime)
- Includes comprehensive testing
- Has clear rollback at every phase
""")

        return "".join(prompt_parts)

    async def generate_runbook(
        self,
        migration_plan: MigrationPlan,
        phase_number: int,
    ) -> str:
        """
        Generate a detailed runbook for a specific migration phase.

        Args:
            migration_plan: Complete migration plan
            phase_number: Phase number to generate runbook for

        Returns:
            Detailed runbook with step-by-step instructions
        """
        phase = next((p for p in migration_plan.phases if p.phase_number == phase_number), None)
        if not phase:
            raise ValueError(f"Phase {phase_number} not found in migration plan")

        prompt = f"""Generate a detailed execution runbook for the following migration phase:

# Migration: {migration_plan.migration_type}
# Phase {phase.phase_number}: {phase.name}

## Phase Details
- Duration: {phase.duration_days} days
- Risk Level: {phase.risk_level}
- Dependencies: {', '.join(phase.dependencies) if phase.dependencies else 'None'}

## Tasks
{chr(10).join(f'- {task}' for task in phase.tasks)}

## Success Criteria
{chr(10).join(f'- {criterion}' for criterion in phase.success_criteria)}

## Rollback Procedure
{phase.rollback_procedure}

Create a detailed runbook including:
1. Pre-migration checklist
2. Step-by-step execution instructions with commands
3. Validation steps after each major change
4. Monitoring and alerting setup
5. Troubleshooting guide
6. Rollback triggers and procedures
7. Post-migration verification

Format as a professional operations runbook with clear, executable instructions.
"""

        system_prompt = """You are a senior SRE creating a migration runbook. Provide clear,
        step-by-step instructions with actual commands, validation steps, and rollback procedures.
        Assume the operator is skilled but unfamiliar with this specific migration."""

        return await self._generate_response(prompt, system_prompt)
