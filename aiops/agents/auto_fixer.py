"""Auto Fixer Agent - Automated issue resolution and self-healing."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from aiops.agents.base_agent import BaseAgent
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class Fix(BaseModel):
    """Represents an automated fix."""

    fix_type: str = Field(description="Type: code, configuration, infrastructure, rollback")
    description: str = Field(description="What the fix does")
    confidence: float = Field(description="Confidence level (0-100)")
    risk_level: str = Field(description="Risk: low, medium, high")
    commands: List[str] = Field(description="Commands or steps to execute")
    validation: List[str] = Field(description="How to validate the fix worked")
    rollback_plan: str = Field(description="How to rollback if fix fails")


class AutoFixResult(BaseModel):
    """Result of auto-fix analysis."""

    issue_summary: str = Field(description="Summary of the issue")
    root_cause: str = Field(description="Identified root cause")
    recommended_fix: Fix = Field(description="Primary recommended fix")
    alternative_fixes: List[Fix] = Field(description="Alternative fix options")
    requires_approval: bool = Field(description="Whether fix requires human approval")
    estimated_downtime: Optional[str] = Field(default=None, description="Estimated downtime")


class AutoFixerAgent(BaseAgent):
    """Agent for automated issue resolution."""

    def __init__(self, **kwargs):
        super().__init__(name="AutoFixerAgent", temperature=0.3, **kwargs)

    async def execute(
        self,
        issue_description: str,
        logs: Optional[str] = None,
        system_state: Optional[Dict[str, Any]] = None,
        auto_apply: bool = False,
    ) -> AutoFixResult:
        """
        Analyze issue and generate automated fixes.

        Args:
            issue_description: Description of the issue
            logs: Relevant logs
            system_state: Current system state
            auto_apply: Whether to auto-apply low-risk fixes

        Returns:
            AutoFixResult with fix recommendations
        """
        logger.info(f"Analyzing issue for auto-fix: {issue_description[:100]}")

        system_prompt = self._create_system_prompt(auto_apply)
        user_prompt = self._create_user_prompt(issue_description, logs, system_state)

        try:
            result = await self._generate_structured_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                schema=AutoFixResult,
            )

            logger.info(
                f"Auto-fix analysis completed: {result.recommended_fix.fix_type}, "
                f"risk: {result.recommended_fix.risk_level}, "
                f"confidence: {result.recommended_fix.confidence}%"
            )

            return result

        except Exception as e:
            logger.error(f"Auto-fix analysis failed: {e}")
            raise

    def _create_system_prompt(self, auto_apply: bool) -> str:
        """Create system prompt for auto-fix."""
        prompt = """You are an expert SRE with deep knowledge of automated remediation and self-healing systems.

Your task is to analyze issues and provide automated fix solutions.

Fix Categories:
1. **Code Fixes**: Bug fixes, patches, hotfixes
2. **Configuration Fixes**: Config changes, feature flags, parameter tuning
3. **Infrastructure Fixes**: Service restarts, resource scaling, health checks
4. **Rollback Fixes**: Revert to previous version or state

Risk Assessment:
- **Low Risk**: Reversible, no data impact, tested fixes (e.g., service restart, cache clear)
- **Medium Risk**: Some impact, requires testing (e.g., config changes, scaling)
- **High Risk**: Potential data impact, significant changes (e.g., code changes, migrations)

Safety Guidelines:
- NEVER suggest destructive operations without rollback plan
- ALWAYS provide validation steps
- ALWAYS include rollback procedures
- Prefer low-risk, reversible fixes
- Be conservative with auto-apply recommendations

"""

        if auto_apply:
            prompt += """
Auto-Apply Mode:
Only recommend auto-apply for LOW RISK fixes that:
- Are fully reversible
- Have no data impact
- Are well-tested patterns
- Have clear validation criteria
"""

        prompt += """
Provide:
- Clear root cause analysis
- Step-by-step fix procedures
- Validation methods
- Comprehensive rollback plan
- Risk and confidence assessment
"""

        return prompt

    def _create_user_prompt(
        self,
        issue_description: str,
        logs: Optional[str] = None,
        system_state: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create user prompt for auto-fix."""
        prompt = f"""Analyze and provide automated fix for this issue:

**Issue Description**:
{issue_description}

"""

        if logs:
            prompt += f"**Relevant Logs**:\n```\n{logs[:2000]}\n```\n\n"

        if system_state:
            prompt += "**System State**:\n"
            for key, value in system_state.items():
                prompt += f"- {key}: {value}\n"
            prompt += "\n"

        prompt += """Provide:
1. Root cause analysis
2. Recommended fix with exact commands/steps
3. Alternative fix options
4. Risk assessment
5. Validation procedure
6. Rollback plan
"""

        return prompt

    async def generate_rollback_plan(
        self,
        deployment_info: Dict[str, Any],
        issue: str,
    ) -> Dict[str, Any]:
        """
        Generate rollback plan for a deployment.

        Args:
            deployment_info: Information about the deployment
            issue: Issue that triggered rollback consideration

        Returns:
            Rollback plan with steps
        """
        logger.info("Generating rollback plan")

        system_prompt = """You are an expert at deployment rollback procedures.

Create safe, comprehensive rollback plans:
- Identify rollback method (redeploy, revert, feature flag)
- Provide step-by-step instructions
- Include data migration rollback if needed
- Specify validation at each step
- Consider dependencies and order of operations
"""

        user_prompt = f"""Generate rollback plan for this situation:

**Deployment Info**:
{deployment_info}

**Issue**:
{issue}

Provide complete rollback procedure with commands and validation.
"""

        try:
            response = await self._generate_response(user_prompt, system_prompt)

            return {
                "rollback_steps": response,
                "estimated_time": "5-15 minutes",  # Can be parsed from response
            }

        except Exception as e:
            logger.error(f"Rollback plan generation failed: {e}")
            return {
                "rollback_steps": f"Generation failed: {str(e)}",
                "estimated_time": "unknown",
            }

    async def fix_common_issues(
        self,
        issue_type: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Fix:
        """
        Get fix for common issues using known patterns.

        Args:
            issue_type: Type of issue (out_of_memory, high_cpu, disk_full, etc.)
            context: Additional context

        Returns:
            Fix for the common issue
        """
        logger.info(f"Getting fix for common issue: {issue_type}")

        # Map of common issues to standard fixes
        common_fixes = {
            "out_of_memory": {
                "description": "Restart service and increase memory limits",
                "commands": [
                    "kubectl rollout restart deployment/{service}",
                    "kubectl set resources deployment/{service} --limits=memory=4Gi",
                ],
                "risk": "medium",
            },
            "high_cpu": {
                "description": "Scale up replicas and investigate CPU hotspots",
                "commands": [
                    "kubectl scale deployment/{service} --replicas=5",
                    "kubectl top pods -l app={service}",
                ],
                "risk": "low",
            },
            "disk_full": {
                "description": "Clean up logs and temporary files",
                "commands": [
                    "find /var/log -name '*.log' -mtime +7 -delete",
                    "docker system prune -af --volumes",
                ],
                "risk": "low",
            },
            "connection_timeout": {
                "description": "Increase timeout and connection pool settings",
                "commands": [
                    "Update config: connection_timeout=60",
                    "Update config: pool_size=20",
                ],
                "risk": "low",
            },
        }

        if issue_type in common_fixes:
            fix_data = common_fixes[issue_type]
            return Fix(
                fix_type="infrastructure",
                description=fix_data["description"],
                confidence=85.0,
                risk_level=fix_data["risk"],
                commands=fix_data["commands"],
                validation=["Check service health", "Monitor metrics for 5 minutes"],
                rollback_plan="Revert configuration changes",
            )

        # Generate custom fix for unknown issues
        system_prompt = f"""Generate automated fix for common DevOps issue: {issue_type}

Provide standard, well-tested fix procedures.
"""

        user_prompt = f"""Provide fix for: {issue_type}

Context: {context or 'None'}

Give specific commands and validation steps.
"""

        try:
            result = await self._generate_structured_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                schema=Fix,
            )

            logger.info(f"Generated fix for {issue_type}")
            return result

        except Exception as e:
            logger.error(f"Fix generation failed: {e}")
            return Fix(
                fix_type="manual",
                description=f"Automated fix generation failed: {str(e)}",
                confidence=0,
                risk_level="high",
                commands=["Manual intervention required"],
                validation=["Verify manually"],
                rollback_plan="Not applicable",
            )
