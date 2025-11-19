"""
Release Manager Agent

This agent helps plan, coordinate, and manage software releases with
risk assessment, rollout strategies, and automated release validation.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from aiops.agents.base_agent import BaseAgent
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class ReleaseChange(BaseModel):
    """Single change in a release"""
    change_id: str = Field(description="Change identifier (PR, commit, ticket)")
    type: str = Field(description="Change type: feature, bugfix, hotfix, refactor")
    description: str = Field(description="Change description")
    risk_level: str = Field(description="Risk: low, medium, high, critical")
    impact_areas: List[str] = Field(description="Affected components/areas")
    requires_migration: bool = Field(description="Requires database/data migration")
    breaking_change: bool = Field(description="Is this a breaking change")


class ReleaseRisk(BaseModel):
    """Identified release risk"""
    risk_id: str = Field(description="Risk identifier")
    description: str = Field(description="Risk description")
    category: str = Field(description="Category: technical, operational, business")
    probability: str = Field(description="Likelihood: low, medium, high")
    impact: str = Field(description="Impact: low, medium, high, critical")
    mitigation: str = Field(description="Risk mitigation strategy")
    monitoring: str = Field(description="How to monitor for this risk")


class RolloutStrategy(BaseModel):
    """Release rollout strategy"""
    strategy_type: str = Field(description="Type: blue-green, canary, rolling, big-bang")
    phases: List[Dict[str, Any]] = Field(description="Rollout phases")
    success_criteria: List[str] = Field(description="Criteria to proceed to next phase")
    rollback_triggers: List[str] = Field(description="Conditions that trigger rollback")
    estimated_duration_minutes: int = Field(description="Estimated total duration")


class ValidationCheck(BaseModel):
    """Post-release validation check"""
    check_id: str = Field(description="Check identifier")
    name: str = Field(description="Check name")
    type: str = Field(description="Type: smoke, functional, performance, security")
    description: str = Field(description="What to validate")
    command: Optional[str] = Field(description="Command to execute if automated")
    expected_result: str = Field(description="Expected result")
    priority: str = Field(description="Priority: critical, high, medium, low")


class ReleasePlan(BaseModel):
    """Complete release plan"""
    release_id: str = Field(description="Unique release identifier")
    version: str = Field(description="Release version")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    release_date: str = Field(description="Planned release date/time")
    environment: str = Field(description="Target environment")
    changes: List[ReleaseChange] = Field(description="Changes in this release")
    risks: List[ReleaseRisk] = Field(description="Identified risks")
    risk_score: float = Field(description="Overall risk score (0-100)")
    rollout_strategy: RolloutStrategy = Field(description="Rollout strategy")
    validation_checks: List[ValidationCheck] = Field(description="Validation checks")
    rollback_plan: str = Field(description="Detailed rollback procedure")
    communication_plan: List[str] = Field(description="Communication steps")
    dependencies: List[str] = Field(description="External dependencies")
    team_assignments: Dict[str, List[str]] = Field(description="Team member assignments")
    go_no_go_criteria: List[str] = Field(description="Go/No-Go decision criteria")
    executive_summary: str = Field(description="Executive summary")


class ReleaseManagerAgent(BaseAgent):
    """
    AI-powered release manager.

    Features:
    - Release planning and coordination
    - Risk assessment
    - Rollout strategy recommendation
    - Validation planning
    - Rollback procedures
    - Communication planning
    - Go/No-Go recommendations
    """

    def __init__(
        self,
        llm_provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = 0.3,
    ):
        super().__init__(
            name="ReleaseManager",
            llm_provider=llm_provider,
            model=model,
            temperature=temperature,
        )

    async def execute(
        self,
        version: str,
        release_date: str,
        environment: str,
        changes: List[Dict[str, Any]],
        previous_release_metrics: Optional[Dict[str, Any]] = None,
        infrastructure_details: Optional[Dict[str, Any]] = None,
        user_traffic_pattern: Optional[Dict[str, Any]] = None,
    ) -> ReleasePlan:
        """
        Create a comprehensive release plan.

        Args:
            version: Release version (e.g., "v2.5.0")
            release_date: Planned release date/time
            environment: Target environment (production, staging, etc.)
            changes: List of changes in this release
            previous_release_metrics: Metrics from previous releases
            infrastructure_details: Infrastructure configuration
            user_traffic_pattern: User traffic patterns for planning

        Returns:
            ReleasePlan with strategy, risks, and procedures
        """
        logger.info(f"Creating release plan for {version} to {environment}")

        # Build release planning prompt
        prompt = self._build_planning_prompt(
            version, release_date, environment, changes,
            previous_release_metrics, infrastructure_details, user_traffic_pattern
        )

        # Define response schema
        schema = {
            "type": "object",
            "properties": {
                "changes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "change_id": {"type": "string"},
                            "type": {"type": "string"},
                            "description": {"type": "string"},
                            "risk_level": {"type": "string"},
                            "impact_areas": {"type": "array", "items": {"type": "string"}},
                            "requires_migration": {"type": "boolean"},
                            "breaking_change": {"type": "boolean"},
                        },
                    },
                },
                "risks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "risk_id": {"type": "string"},
                            "description": {"type": "string"},
                            "category": {"type": "string"},
                            "probability": {"type": "string"},
                            "impact": {"type": "string"},
                            "mitigation": {"type": "string"},
                            "monitoring": {"type": "string"},
                        },
                    },
                },
                "risk_score": {"type": "number", "minimum": 0, "maximum": 100},
                "rollout_strategy": {
                    "type": "object",
                    "properties": {
                        "strategy_type": {"type": "string"},
                        "phases": {"type": "array"},
                        "success_criteria": {"type": "array", "items": {"type": "string"}},
                        "rollback_triggers": {"type": "array", "items": {"type": "string"}},
                        "estimated_duration_minutes": {"type": "integer"},
                    },
                },
                "validation_checks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "check_id": {"type": "string"},
                            "name": {"type": "string"},
                            "type": {"type": "string"},
                            "description": {"type": "string"},
                            "command": {"type": "string"},
                            "expected_result": {"type": "string"},
                            "priority": {"type": "string"},
                        },
                    },
                },
                "rollback_plan": {"type": "string"},
                "communication_plan": {"type": "array", "items": {"type": "string"}},
                "dependencies": {"type": "array", "items": {"type": "string"}},
                "team_assignments": {"type": "object"},
                "go_no_go_criteria": {"type": "array", "items": {"type": "string"}},
                "executive_summary": {"type": "string"},
            },
            "required": [
                "changes", "risks", "risk_score", "rollout_strategy",
                "rollback_plan", "executive_summary"
            ],
        }

        # Generate release plan
        system_prompt = """You are an expert release manager with experience in safe,
        successful software releases. Assess risks realistically, recommend appropriate
        rollout strategies, and ensure comprehensive rollback plans. Prioritize user
        experience and system stability."""

        response = await self._generate_structured_response(prompt, schema, system_prompt)

        # Create plan
        plan = ReleasePlan(
            release_id=f"REL-{version}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            version=version,
            release_date=release_date,
            environment=environment,
            changes=[ReleaseChange(**c) for c in response.get("changes", [])],
            risks=[ReleaseRisk(**r) for r in response.get("risks", [])],
            risk_score=response.get("risk_score", 0),
            rollout_strategy=RolloutStrategy(**response.get("rollout_strategy", {})),
            validation_checks=[ValidationCheck(**v) for v in response.get("validation_checks", [])],
            rollback_plan=response.get("rollback_plan", ""),
            communication_plan=response.get("communication_plan", []),
            dependencies=response.get("dependencies", []),
            team_assignments=response.get("team_assignments", {}),
            go_no_go_criteria=response.get("go_no_go_criteria", []),
            executive_summary=response.get("executive_summary", ""),
        )

        logger.info(
            f"Release plan created: {len(plan.changes)} changes, "
            f"risk score {plan.risk_score}, {plan.rollout_strategy.strategy_type} rollout"
        )

        return plan

    def _build_planning_prompt(
        self,
        version: str,
        release_date: str,
        environment: str,
        changes: List[Dict[str, Any]],
        previous_release_metrics: Optional[Dict[str, Any]],
        infrastructure_details: Optional[Dict[str, Any]],
        user_traffic_pattern: Optional[Dict[str, Any]],
    ) -> str:
        """Build release planning prompt"""
        prompt_parts = [
            f"# Release Planning Request\n\n",
            f"## Release Details\n",
            f"- Version: {version}\n",
            f"- Date: {release_date}\n",
            f"- Environment: {environment}\n\n",
            f"## Changes in This Release\n",
        ]

        for i, change in enumerate(changes, 1):
            prompt_parts.append(
                f"{i}. [{change.get('type', 'unknown')}] {change.get('description', '')}\n"
            )
        prompt_parts.append("\n")

        if previous_release_metrics:
            prompt_parts.append(f"## Previous Release Metrics\n```json\n{previous_release_metrics}\n```\n\n")

        if infrastructure_details:
            prompt_parts.append(f"## Infrastructure\n```yaml\n{infrastructure_details}\n```\n\n")

        if user_traffic_pattern:
            prompt_parts.append(f"## User Traffic Pattern\n```json\n{user_traffic_pattern}\n```\n\n")

        prompt_parts.append("""
## Planning Requirements

Create a comprehensive release plan including:

### 1. Change Analysis
- Classify each change (feature, bugfix, hotfix, refactor)
- Assess individual risk levels
- Identify breaking changes
- Note migration requirements
- Map impact areas

### 2. Risk Assessment
- Overall risk score (0-100)
- Specific risks (technical, operational, business)
- Risk probability and impact
- Mitigation strategies
- Monitoring approach

### 3. Rollout Strategy
Choose appropriate strategy:
- **Blue-Green**: Zero downtime, instant rollback, requires 2x resources
- **Canary**: Gradual rollout, progressive risk exposure, complex orchestration
- **Rolling**: Sequential updates, moderate risk, some downtime
- **Big-Bang**: All at once, highest risk, simplest (use only for low-risk releases)

Define:
- Rollout phases (percentage of traffic/instances per phase)
- Success criteria for each phase
- Rollback triggers
- Estimated duration

### 4. Validation Strategy
- Smoke tests (basic functionality)
- Functional tests (features work correctly)
- Performance tests (latency, throughput meet SLAs)
- Security tests (no new vulnerabilities)
- Data integrity tests (data not corrupted)

### 5. Rollback Plan
- Decision criteria for rollback
- Step-by-step rollback procedure
- Data handling during rollback
- Expected rollback duration
- Communication during rollback

### 6. Communication Plan
- Pre-release notifications (customers, stakeholders)
- During release updates
- Post-release announcement
- Escalation procedures

### 7. Go/No-Go Criteria
- Technical criteria (tests pass, metrics normal)
- Operational criteria (team ready, dependencies met)
- Business criteria (timing, customer impact)

Ensure the plan is:
- Risk-appropriate (higher risk = more gradual rollout)
- Well-tested (comprehensive validation)
- Safely reversible (clear rollback at any point)
- Well-communicated (stakeholders informed)
""")

        return "".join(prompt_parts)

    async def assess_go_no_go(
        self,
        release_plan: ReleasePlan,
        current_system_health: Dict[str, Any],
        pre_release_test_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Make a Go/No-Go recommendation for release.

        Args:
            release_plan: Release plan
            current_system_health: Current system metrics
            pre_release_test_results: Pre-release test results

        Returns:
            Go/No-Go recommendation with reasoning
        """
        prompt = f"""Assess whether to proceed with the following release:

# Release: {release_plan.version}
- Scheduled: {release_plan.release_date}
- Environment: {release_plan.environment}
- Risk Score: {release_plan.risk_score}/100
- Changes: {len(release_plan.changes)}
- Critical Risks: {sum(1 for r in release_plan.risks if r.impact == 'critical')}

# Go/No-Go Criteria
{chr(10).join(f'- {criterion}' for criterion in release_plan.go_no_go_criteria)}

# Current System Health
```json
{current_system_health}
```

# Pre-Release Test Results
```json
{pre_release_test_results}
```

Provide a Go/No-Go recommendation including:
1. **Decision**: GO or NO-GO
2. **Confidence**: Confidence level in the recommendation (0-100)
3. **Reasoning**: Detailed reasoning for the decision
4. **Concerns**: Any remaining concerns (even for GO decision)
5. **Conditions**: Conditions that must be met (for GO decision)
6. **Alternative**: Alternative plan if NO-GO

Be conservative. When in doubt, recommend NO-GO and suggest what needs to be addressed.
"""

        system_prompt = """You are a senior release manager making a Go/No-Go decision.
        Prioritize system stability and user experience. Be conservative with high-risk releases.
        Provide clear, actionable reasoning."""

        response = await self._generate_response(prompt, system_prompt)

        return {
            "recommendation": response,
            "assessed_at": datetime.now().isoformat(),
            "release_id": release_plan.release_id,
        }
