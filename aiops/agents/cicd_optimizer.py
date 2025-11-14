"""CI/CD Optimizer Agent - Intelligent CI/CD pipeline optimization."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from aiops.agents.base_agent import BaseAgent
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class PipelineIssue(BaseModel):
    """Represents a CI/CD pipeline issue."""

    stage: str = Field(description="Pipeline stage where issue occurs")
    issue_type: str = Field(description="Type: performance, reliability, configuration, security")
    severity: str = Field(description="Severity: critical, high, medium, low")
    description: str = Field(description="Issue description")
    impact: str = Field(description="Impact on pipeline/deployment")
    solution: str = Field(description="Recommended solution")


class PipelineOptimization(BaseModel):
    """CI/CD pipeline optimization recommendations."""

    current_duration: Optional[float] = Field(default=None, description="Current pipeline duration (minutes)")
    estimated_duration: Optional[float] = Field(default=None, description="Estimated duration after optimization (minutes)")
    issues: List[PipelineIssue] = Field(description="Identified issues")
    optimizations: List[str] = Field(description="Recommended optimizations")
    parallel_opportunities: List[str] = Field(description="Stages that can be parallelized")
    caching_opportunities: List[str] = Field(description="Caching opportunities")
    resource_recommendations: Dict[str, Any] = Field(description="Resource allocation recommendations")


class BuildFailureAnalysis(BaseModel):
    """Analysis of build failures."""

    failure_category: str = Field(description="Category: test, compilation, deployment, infrastructure")
    root_cause: str = Field(description="Root cause of failure")
    failed_step: str = Field(description="Step/stage that failed")
    error_summary: str = Field(description="Summary of errors")
    quick_fix: Optional[str] = Field(default=None, description="Quick fix if available")
    detailed_solution: str = Field(description="Detailed solution steps")
    prevention: List[str] = Field(description="How to prevent this in future")


class CICDOptimizerAgent(BaseAgent):
    """Agent for CI/CD pipeline optimization."""

    def __init__(self, **kwargs):
        super().__init__(name="CICDOptimizerAgent", **kwargs)

    async def execute(
        self,
        pipeline_config: str,
        pipeline_logs: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> PipelineOptimization:
        """
        Analyze and optimize CI/CD pipeline.

        Args:
            pipeline_config: Pipeline configuration (YAML, JSON, etc.)
            pipeline_logs: Recent pipeline execution logs
            metrics: Pipeline metrics (duration, success rate, etc.)

        Returns:
            PipelineOptimization with recommendations
        """
        logger.info("Analyzing CI/CD pipeline for optimization")

        system_prompt = self._create_system_prompt()
        user_prompt = self._create_user_prompt(pipeline_config, pipeline_logs, metrics)

        try:
            result = await self._generate_structured_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                schema=PipelineOptimization,
            )

            if result.current_duration and result.estimated_duration:
                improvement = (
                    (result.current_duration - result.estimated_duration)
                    / result.current_duration
                    * 100
                )
                logger.info(
                    f"Pipeline optimization completed: {len(result.issues)} issues, "
                    f"estimated {improvement:.1f}% improvement"
                )
            else:
                logger.info(f"Pipeline optimization completed: {len(result.issues)} issues")

            return result

        except Exception as e:
            logger.error(f"Pipeline optimization failed: {e}")
            return PipelineOptimization(
                issues=[],
                optimizations=[f"Analysis failed: {str(e)}"],
                parallel_opportunities=[],
                caching_opportunities=[],
                resource_recommendations={},
            )

    def _create_system_prompt(self) -> str:
        """Create system prompt for CI/CD optimization."""
        return """You are an expert DevOps engineer specializing in CI/CD optimization.

Your expertise includes:
1. **Pipeline Performance**: Reducing build times, parallel execution
2. **Reliability**: Improving success rates, handling flaky tests
3. **Resource Optimization**: Right-sizing compute resources, caching
4. **Security**: Secrets management, security scanning, compliance
5. **Cost Optimization**: Reducing CI/CD costs while maintaining quality

Optimization Strategies:
- Parallelize independent stages
- Implement smart caching (dependencies, build artifacts, Docker layers)
- Optimize test execution (test splitting, fail-fast strategies)
- Use appropriate resource sizing
- Implement conditional execution
- Reduce redundant steps

Focus on:
- Actionable recommendations
- Measurable improvements
- Quick wins and long-term optimizations
- Trade-offs between speed, reliability, and cost
"""

    def _create_user_prompt(
        self,
        pipeline_config: str,
        pipeline_logs: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create user prompt for pipeline optimization."""
        prompt = "Analyze and optimize the following CI/CD pipeline:\n\n"

        prompt += f"**Pipeline Configuration**:\n```\n{pipeline_config}\n```\n\n"

        if pipeline_logs:
            prompt += f"**Recent Execution Logs**:\n```\n{pipeline_logs[:2000]}\n```\n\n"

        if metrics:
            prompt += f"**Pipeline Metrics**:\n"
            for key, value in metrics.items():
                prompt += f"- {key}: {value}\n"
            prompt += "\n"

        prompt += """Provide:
1. Identified issues and bottlenecks
2. Specific optimization recommendations
3. Parallelization opportunities
4. Caching strategies
5. Resource allocation recommendations
6. Estimated improvement in pipeline duration
"""

        return prompt

    async def analyze_build_failure(
        self,
        build_logs: str,
        pipeline_config: Optional[str] = None,
        previous_successful_build: Optional[str] = None,
    ) -> BuildFailureAnalysis:
        """
        Analyze build failure and provide fix recommendations.

        Args:
            build_logs: Build failure logs
            pipeline_config: Pipeline configuration
            previous_successful_build: Logs from last successful build

        Returns:
            BuildFailureAnalysis with root cause and solutions
        """
        logger.info(f"Analyzing build failure ({len(build_logs)} chars of logs)")

        system_prompt = """You are an expert at diagnosing and fixing CI/CD build failures.

Analyze failures systematically:
1. Identify the exact failing step
2. Determine root cause (not just symptoms)
3. Provide quick fixes when possible
4. Give detailed solution steps
5. Suggest prevention strategies

Common failure categories:
- Test failures (unit, integration, e2e)
- Compilation/build errors
- Dependency issues
- Infrastructure problems
- Deployment failures
- Configuration errors
- Resource constraints
"""

        user_prompt = f"""Analyze this build failure:

**Build Logs**:
```
{build_logs}
```
"""

        if pipeline_config:
            user_prompt += f"\n**Pipeline Config**:\n```\n{pipeline_config}\n```\n"

        if previous_successful_build:
            user_prompt += f"\n**Previous Successful Build Logs** (for comparison):\n```\n{previous_successful_build[:1000]}\n```\n"

        user_prompt += "\nProvide root cause analysis and step-by-step fix instructions."

        try:
            result = await self._generate_structured_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                schema=BuildFailureAnalysis,
            )

            logger.info(f"Build failure analysis completed: {result.failure_category}")
            return result

        except Exception as e:
            logger.error(f"Build failure analysis failed: {e}")
            return BuildFailureAnalysis(
                failure_category="unknown",
                root_cause=f"Analysis failed: {str(e)}",
                failed_step="unknown",
                error_summary="",
                detailed_solution="Please retry the analysis",
                prevention=[],
            )

    async def suggest_test_optimization(
        self,
        test_results: str,
        test_duration_data: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Suggest test suite optimizations.

        Args:
            test_results: Test execution results
            test_duration_data: Duration of individual tests

        Returns:
            Test optimization recommendations
        """
        logger.info("Analyzing test suite for optimization")

        system_prompt = """You are an expert in test optimization and test-driven development.

Optimize test suites by:
1. Identifying slow tests
2. Suggesting test parallelization
3. Recommending test splitting strategies
4. Finding redundant tests
5. Suggesting fail-fast approaches

Focus on reducing CI time while maintaining coverage.
"""

        user_prompt = f"""Optimize the following test suite:

**Test Results**:
```
{test_results}
```
"""

        if test_duration_data:
            user_prompt += "\n**Test Durations**:\n"
            for test, duration in sorted(
                test_duration_data.items(), key=lambda x: x[1], reverse=True
            )[:20]:
                user_prompt += f"- {test}: {duration}s\n"

        user_prompt += "\nProvide specific test optimization recommendations."

        try:
            response = await self._generate_response(user_prompt, system_prompt)

            return {
                "recommendations": response,
                "slow_tests": [
                    test
                    for test, duration in (test_duration_data or {}).items()
                    if duration > 10
                ],
            }

        except Exception as e:
            logger.error(f"Test optimization failed: {e}")
            return {"recommendations": f"Analysis failed: {str(e)}", "slow_tests": []}
