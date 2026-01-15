"""
Unit tests for CI/CD Optimizer Agent
"""

import pytest
from unittest.mock import AsyncMock
from aiops.agents.cicd_optimizer import (
    CICDOptimizerAgent,
    PipelineIssue,
    PipelineOptimization,
    BuildFailureAnalysis
)


class TestPipelineIssue:
    """Tests for PipelineIssue model"""

    def test_create_issue(self):
        """Test creating a pipeline issue"""
        issue = PipelineIssue(
            stage="build",
            issue_type="performance",
            severity="high",
            description="Build stage takes too long",
            impact="Increases overall pipeline duration",
            solution="Implement caching for dependencies"
        )
        assert issue.stage == "build"
        assert issue.issue_type == "performance"
        assert issue.severity == "high"

    def test_issue_types(self):
        """Test different issue types"""
        for issue_type in ["performance", "reliability", "configuration", "security"]:
            issue = PipelineIssue(
                stage="test",
                issue_type=issue_type,
                severity="medium",
                description="Test issue",
                impact="Test impact",
                solution="Test solution"
            )
            assert issue.issue_type == issue_type

    def test_issue_severities(self):
        """Test different severity levels"""
        for severity in ["critical", "high", "medium", "low"]:
            issue = PipelineIssue(
                stage="deploy",
                issue_type="performance",
                severity=severity,
                description="Test",
                impact="Test",
                solution="Test"
            )
            assert issue.severity == severity


class TestPipelineOptimization:
    """Tests for PipelineOptimization model"""

    def test_create_optimization(self):
        """Test creating pipeline optimization"""
        optimization = PipelineOptimization(
            current_duration=30.0,
            estimated_duration=20.0,
            issues=[],
            optimizations=["Enable caching"],
            parallel_opportunities=["test and lint"],
            caching_opportunities=["node_modules"],
            resource_recommendations={"cpu": "2 cores"}
        )
        assert optimization.current_duration == 30.0
        assert optimization.estimated_duration == 20.0
        assert len(optimization.optimizations) == 1

    def test_optimization_optional_durations(self):
        """Test optimization with optional durations"""
        optimization = PipelineOptimization(
            issues=[],
            optimizations=[],
            parallel_opportunities=[],
            caching_opportunities=[],
            resource_recommendations={}
        )
        assert optimization.current_duration is None
        assert optimization.estimated_duration is None


class TestBuildFailureAnalysis:
    """Tests for BuildFailureAnalysis model"""

    def test_create_analysis(self):
        """Test creating build failure analysis"""
        analysis = BuildFailureAnalysis(
            failure_category="test",
            root_cause="Flaky test in authentication module",
            failed_step="unit-tests",
            error_summary="AssertionError in test_login",
            quick_fix="Retry the test",
            detailed_solution="Fix the race condition",
            prevention=["Add test isolation", "Use mocks"]
        )
        assert analysis.failure_category == "test"
        assert analysis.quick_fix == "Retry the test"

    def test_analysis_categories(self):
        """Test different failure categories"""
        for category in ["test", "compilation", "deployment", "infrastructure"]:
            analysis = BuildFailureAnalysis(
                failure_category=category,
                root_cause="Test",
                failed_step="step",
                error_summary="Error",
                detailed_solution="Solution",
                prevention=[]
            )
            assert analysis.failure_category == category

    def test_analysis_optional_quick_fix(self):
        """Test analysis without quick fix"""
        analysis = BuildFailureAnalysis(
            failure_category="compilation",
            root_cause="Syntax error",
            failed_step="build",
            error_summary="SyntaxError",
            detailed_solution="Fix syntax",
            prevention=[]
        )
        assert analysis.quick_fix is None


class TestCICDOptimizerAgent:
    """Tests for CICDOptimizerAgent"""

    @pytest.fixture
    def agent(self):
        """Create agent instance"""
        return CICDOptimizerAgent()

    @pytest.fixture
    def mock_optimization(self):
        """Mock optimization result"""
        return PipelineOptimization(
            current_duration=45.0,
            estimated_duration=25.0,
            issues=[
                PipelineIssue(
                    stage="test",
                    issue_type="performance",
                    severity="high",
                    description="Tests run sequentially",
                    impact="Long pipeline duration",
                    solution="Parallelize tests"
                )
            ],
            optimizations=[
                "Enable parallel test execution",
                "Add dependency caching"
            ],
            parallel_opportunities=["lint and type-check", "unit and integration tests"],
            caching_opportunities=["node_modules", "pip cache", "docker layers"],
            resource_recommendations={"runners": 2, "memory": "4GB"}
        )

    @pytest.mark.asyncio
    async def test_execute_basic(self, agent, mock_optimization):
        """Test basic execution"""
        agent._generate_structured_response = AsyncMock(return_value=mock_optimization)

        pipeline_config = """
stages:
  - build
  - test
  - deploy
"""
        result = await agent.execute(pipeline_config)

        assert isinstance(result, PipelineOptimization)
        assert result.current_duration == 45.0
        assert len(result.issues) == 1

    @pytest.mark.asyncio
    async def test_execute_with_logs(self, agent, mock_optimization):
        """Test execution with pipeline logs"""
        agent._generate_structured_response = AsyncMock(return_value=mock_optimization)

        await agent.execute("config", pipeline_logs="Build started...\nBuild completed")

        call_args = agent._generate_structured_response.call_args
        prompt = call_args[1]["prompt"]
        assert "Execution Logs" in prompt

    @pytest.mark.asyncio
    async def test_execute_with_metrics(self, agent, mock_optimization):
        """Test execution with pipeline metrics"""
        agent._generate_structured_response = AsyncMock(return_value=mock_optimization)

        metrics = {"avg_duration": "30m", "success_rate": "95%"}
        await agent.execute("config", metrics=metrics)

        call_args = agent._generate_structured_response.call_args
        prompt = call_args[1]["prompt"]
        assert "Metrics" in prompt
        assert "avg_duration" in prompt

    @pytest.mark.asyncio
    async def test_execute_error_handling(self, agent):
        """Test error handling"""
        agent._generate_structured_response = AsyncMock(
            side_effect=Exception("API error")
        )

        result = await agent.execute("config")

        assert len(result.issues) == 0
        assert "failed" in result.optimizations[0].lower()

    def test_create_system_prompt(self, agent):
        """Test system prompt creation"""
        prompt = agent._create_system_prompt()

        assert "DevOps" in prompt
        assert "pipeline" in prompt.lower()
        assert "caching" in prompt.lower()
        assert "parallel" in prompt.lower()

    def test_create_user_prompt_basic(self, agent):
        """Test user prompt creation"""
        prompt = agent._create_user_prompt("config: test")

        assert "config: test" in prompt
        assert "Pipeline Configuration" in prompt

    def test_create_user_prompt_with_logs(self, agent):
        """Test user prompt with logs"""
        prompt = agent._create_user_prompt("config", pipeline_logs="log output")

        assert "Execution Logs" in prompt
        assert "log output" in prompt

    def test_create_user_prompt_with_metrics(self, agent):
        """Test user prompt with metrics"""
        metrics = {"duration": "25m", "failures": 5}
        prompt = agent._create_user_prompt("config", metrics=metrics)

        assert "Metrics" in prompt
        assert "duration" in prompt

    def test_create_user_prompt_truncates_logs(self, agent):
        """Test that long logs are truncated"""
        long_logs = "x" * 5000
        prompt = agent._create_user_prompt("config", pipeline_logs=long_logs)

        assert len(prompt) < 5000

    @pytest.mark.asyncio
    async def test_analyze_build_failure(self, agent):
        """Test build failure analysis"""
        agent._generate_structured_response = AsyncMock(
            return_value=BuildFailureAnalysis(
                failure_category="test",
                root_cause="Test timeout",
                failed_step="unit-tests",
                error_summary="Timeout after 30s",
                quick_fix="Increase timeout",
                detailed_solution="Fix slow test",
                prevention=["Add timeout limits"]
            )
        )

        result = await agent.analyze_build_failure("ERROR: Test timeout")

        assert result.failure_category == "test"
        assert result.root_cause == "Test timeout"

    @pytest.mark.asyncio
    async def test_analyze_build_failure_with_config(self, agent):
        """Test build failure analysis with pipeline config"""
        agent._generate_structured_response = AsyncMock(
            return_value=BuildFailureAnalysis(
                failure_category="configuration",
                root_cause="Missing env var",
                failed_step="deploy",
                error_summary="EnvError",
                detailed_solution="Add env var",
                prevention=[]
            )
        )

        await agent.analyze_build_failure(
            "ERROR: Missing env",
            pipeline_config="deploy:\n  script: deploy.sh"
        )

        call_args = agent._generate_structured_response.call_args
        prompt = call_args[1]["prompt"]
        assert "Pipeline Config" in prompt

    @pytest.mark.asyncio
    async def test_analyze_build_failure_with_previous_build(self, agent):
        """Test build failure analysis with previous successful build"""
        agent._generate_structured_response = AsyncMock(
            return_value=BuildFailureAnalysis(
                failure_category="compilation",
                root_cause="New dependency conflict",
                failed_step="build",
                error_summary="ImportError",
                detailed_solution="Fix imports",
                prevention=[]
            )
        )

        await agent.analyze_build_failure(
            "ERROR: Import failed",
            previous_successful_build="Build successful"
        )

        call_args = agent._generate_structured_response.call_args
        prompt = call_args[1]["prompt"]
        assert "Previous Successful Build" in prompt

    @pytest.mark.asyncio
    async def test_analyze_build_failure_error(self, agent):
        """Test build failure analysis error handling"""
        agent._generate_structured_response = AsyncMock(
            side_effect=Exception("Error")
        )

        result = await agent.analyze_build_failure("logs")

        assert result.failure_category == "unknown"
        assert "failed" in result.root_cause.lower()

    @pytest.mark.asyncio
    async def test_suggest_test_optimization(self, agent):
        """Test test optimization suggestions"""
        agent._generate_response = AsyncMock(return_value="Parallelize tests")

        result = await agent.suggest_test_optimization("10 tests passed")

        assert "recommendations" in result
        assert "slow_tests" in result

    @pytest.mark.asyncio
    async def test_suggest_test_optimization_with_durations(self, agent):
        """Test test optimization with duration data"""
        agent._generate_response = AsyncMock(return_value="Optimize slow tests")

        durations = {
            "test_slow": 30.0,
            "test_fast": 1.0,
            "test_medium": 5.0
        }

        result = await agent.suggest_test_optimization("results", durations)

        # Slow tests should be identified (>10s)
        assert "test_slow" in result["slow_tests"]
        assert "test_fast" not in result["slow_tests"]

    @pytest.mark.asyncio
    async def test_suggest_test_optimization_sorts_by_duration(self, agent):
        """Test that durations are sorted in prompt"""
        agent._generate_response = AsyncMock(return_value="recommendations")

        durations = {
            "fast": 1.0,
            "slow": 100.0,
            "medium": 10.0
        }

        await agent.suggest_test_optimization("results", durations)

        call_args = agent._generate_response.call_args
        prompt = call_args[0][0]
        # slow should appear before medium in the prompt
        slow_pos = prompt.find("slow")
        medium_pos = prompt.find("medium")
        assert slow_pos < medium_pos

    @pytest.mark.asyncio
    async def test_suggest_test_optimization_error(self, agent):
        """Test test optimization error handling"""
        agent._generate_response = AsyncMock(side_effect=Exception("Error"))

        result = await agent.suggest_test_optimization("results")

        assert "failed" in result["recommendations"].lower()
        assert result["slow_tests"] == []

    def test_agent_initialization(self):
        """Test agent initialization"""
        agent = CICDOptimizerAgent()
        assert agent.name == "CICDOptimizerAgent"

    def test_agent_inherits_from_base(self):
        """Test agent inherits from BaseAgent"""
        from aiops.agents.base_agent import BaseAgent
        agent = CICDOptimizerAgent()
        assert isinstance(agent, BaseAgent)


class TestCICDOptimizerEdgeCases:
    """Edge case tests"""

    @pytest.fixture
    def agent(self):
        return CICDOptimizerAgent()

    @pytest.mark.asyncio
    async def test_empty_pipeline_config(self, agent):
        """Test with empty pipeline config"""
        agent._generate_structured_response = AsyncMock(
            return_value=PipelineOptimization(
                issues=[],
                optimizations=["Add pipeline stages"],
                parallel_opportunities=[],
                caching_opportunities=[],
                resource_recommendations={}
            )
        )

        result = await agent.execute("")
        assert result is not None

    @pytest.mark.asyncio
    async def test_complex_yaml_config(self, agent):
        """Test with complex YAML config"""
        agent._generate_structured_response = AsyncMock(
            return_value=PipelineOptimization(
                issues=[],
                optimizations=[],
                parallel_opportunities=[],
                caching_opportunities=[],
                resource_recommendations={}
            )
        )

        complex_config = """
stages:
  - name: build
    jobs:
      - compile
      - lint
  - name: test
    parallel:
      matrix:
        - node: [14, 16, 18]
"""
        result = await agent.execute(complex_config)
        assert result is not None

    @pytest.mark.asyncio
    async def test_improvement_calculation(self, agent):
        """Test improvement percentage calculation"""
        optimization = PipelineOptimization(
            current_duration=100.0,
            estimated_duration=50.0,
            issues=[],
            optimizations=[],
            parallel_opportunities=[],
            caching_opportunities=[],
            resource_recommendations={}
        )
        agent._generate_structured_response = AsyncMock(return_value=optimization)

        result = await agent.execute("config")

        # 50% improvement from 100 to 50
        improvement = (result.current_duration - result.estimated_duration) / result.current_duration * 100
        assert improvement == 50.0

    @pytest.mark.asyncio
    async def test_many_slow_tests(self, agent):
        """Test with many slow tests"""
        agent._generate_response = AsyncMock(return_value="recommendations")

        durations = {f"test_{i}": 20.0 + i for i in range(50)}

        result = await agent.suggest_test_optimization("results", durations)

        # All tests are slow
        assert len(result["slow_tests"]) == 50
