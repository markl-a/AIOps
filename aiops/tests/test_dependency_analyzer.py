"""
Unit tests for Dependency Analyzer Agent
"""

import pytest
from unittest.mock import AsyncMock, patch
from aiops.agents.dependency_analyzer import (
    DependencyAnalyzerAgent,
    DependencyInfo,
    DependencyIssue,
    DependencyAnalysisResult
)


class TestDependencyInfo:
    """Tests for DependencyInfo model"""

    def test_create_dependency_info(self):
        """Test creating dependency info"""
        info = DependencyInfo(
            name="requests",
            current_version="2.28.0",
            latest_version="2.31.0",
            is_outdated=True,
            license="Apache-2.0",
            description="HTTP library",
            dependencies_count=5
        )
        assert info.name == "requests"
        assert info.is_outdated is True
        assert info.dependencies_count == 5

    def test_dependency_info_optional_fields(self):
        """Test dependency info with optional fields"""
        info = DependencyInfo(
            name="mypackage",
            current_version="1.0.0",
            latest_version="1.0.0",
            is_outdated=False
        )
        assert info.license is None
        assert info.description is None
        assert info.dependencies_count == 0


class TestDependencyIssue:
    """Tests for DependencyIssue model"""

    def test_create_dependency_issue(self):
        """Test creating dependency issue"""
        issue = DependencyIssue(
            severity="high",
            package_name="vulnerable-pkg",
            issue_type="security",
            description="Known CVE detected",
            recommendation="Upgrade to 2.0.0"
        )
        assert issue.severity == "high"
        assert issue.issue_type == "security"

    def test_issue_types(self):
        """Test different issue types"""
        for issue_type in ["outdated", "license", "security", "deprecated"]:
            issue = DependencyIssue(
                severity="medium",
                package_name="test",
                issue_type=issue_type,
                description="Test",
                recommendation="Fix it"
            )
            assert issue.issue_type == issue_type

    def test_issue_severities(self):
        """Test different severities"""
        for severity in ["high", "medium", "low"]:
            issue = DependencyIssue(
                severity=severity,
                package_name="test",
                issue_type="outdated",
                description="Test",
                recommendation="Update"
            )
            assert issue.severity == severity


class TestDependencyAnalysisResult:
    """Tests for DependencyAnalysisResult model"""

    def test_create_analysis_result(self):
        """Test creating analysis result"""
        result = DependencyAnalysisResult(
            total_dependencies=10,
            outdated_count=3,
            summary="3 packages need updates",
            dependencies=[],
            issues=[],
            recommendations=["Update outdated packages"],
            license_summary={"MIT": 5, "Apache-2.0": 3},
            dependency_tree_insights=["No circular dependencies"]
        )
        assert result.total_dependencies == 10
        assert result.outdated_count == 3
        assert len(result.license_summary) == 2

    def test_analysis_result_with_dependencies(self):
        """Test analysis result with dependencies and issues"""
        deps = [
            DependencyInfo(
                name="pkg1",
                current_version="1.0.0",
                latest_version="2.0.0",
                is_outdated=True
            )
        ]
        issues = [
            DependencyIssue(
                severity="high",
                package_name="pkg1",
                issue_type="outdated",
                description="Major update available",
                recommendation="Update carefully"
            )
        ]
        result = DependencyAnalysisResult(
            total_dependencies=1,
            outdated_count=1,
            summary="1 outdated",
            dependencies=deps,
            issues=issues,
            recommendations=[],
            license_summary={},
            dependency_tree_insights=[]
        )
        assert len(result.dependencies) == 1
        assert len(result.issues) == 1


class TestDependencyAnalyzerAgent:
    """Tests for DependencyAnalyzerAgent"""

    @pytest.fixture
    def agent(self):
        """Create agent instance"""
        agent = DependencyAnalyzerAgent()
        return agent

    @pytest.fixture
    def mock_analysis_result(self):
        """Mock analysis result"""
        return DependencyAnalysisResult(
            total_dependencies=5,
            outdated_count=2,
            summary="Analysis complete",
            dependencies=[
                DependencyInfo(
                    name="requests",
                    current_version="2.28.0",
                    latest_version="2.31.0",
                    is_outdated=True,
                    license="Apache-2.0"
                )
            ],
            issues=[
                DependencyIssue(
                    severity="medium",
                    package_name="requests",
                    issue_type="outdated",
                    description="Update available",
                    recommendation="Run pip install --upgrade requests"
                )
            ],
            recommendations=["Keep dependencies updated"],
            license_summary={"Apache-2.0": 3, "MIT": 2},
            dependency_tree_insights=["Clean dependency tree"]
        )

    @pytest.mark.asyncio
    async def test_execute_basic(self, agent, mock_analysis_result):
        """Test basic execution"""
        agent._generate_structured_response = AsyncMock(return_value=mock_analysis_result)

        dependencies = """
requests==2.28.0
flask==2.0.0
pytest==7.0.0
"""
        result = await agent.execute(dependencies, dependency_type="python")

        assert isinstance(result, DependencyAnalysisResult)
        assert result.total_dependencies == 5

    @pytest.mark.asyncio
    async def test_execute_with_lock_file(self, agent, mock_analysis_result):
        """Test execution with lock file"""
        agent._generate_structured_response = AsyncMock(return_value=mock_analysis_result)

        dependencies = "requests>=2.28.0"
        lock_file = "requests==2.28.1"

        await agent.execute(dependencies, lock_file=lock_file)

        call_args = agent._generate_structured_response.call_args
        prompt = call_args[1]["prompt"]
        assert "Lock File" in prompt

    @pytest.mark.asyncio
    async def test_execute_different_types(self, agent, mock_analysis_result):
        """Test execution for different dependency types"""
        agent._generate_structured_response = AsyncMock(return_value=mock_analysis_result)

        for dep_type in ["python", "node", "java", "go"]:
            await agent.execute("dependencies", dependency_type=dep_type)

        assert agent._generate_structured_response.call_count == 4

    @pytest.mark.asyncio
    async def test_execute_error_handling(self, agent):
        """Test error handling"""
        agent._generate_structured_response = AsyncMock(
            side_effect=Exception("API error")
        )

        result = await agent.execute("dependencies")

        assert result.total_dependencies == 0
        assert "failed" in result.summary.lower()

    def test_create_system_prompt(self, agent):
        """Test system prompt creation"""
        prompt = agent._create_system_prompt("python")

        assert "python" in prompt.lower()
        assert "version" in prompt.lower()
        assert "license" in prompt.lower()
        assert "security" in prompt.lower()

    def test_create_user_prompt_basic(self, agent):
        """Test user prompt creation"""
        deps = "requests==2.28.0"
        prompt = agent._create_user_prompt(deps)

        assert "requests" in prompt
        assert "Dependencies" in prompt

    def test_create_user_prompt_with_lock_file(self, agent):
        """Test user prompt with lock file"""
        deps = "requests>=2.28.0"
        lock = "requests==2.28.1"
        prompt = agent._create_user_prompt(deps, lock_file=lock)

        assert "Lock File" in prompt
        assert "2.28.1" in prompt

    @pytest.mark.asyncio
    async def test_find_unused_dependencies(self, agent):
        """Test finding unused dependencies"""
        agent._generate_response = AsyncMock(return_value="""
Unused dependencies:
- unused-pkg1
- unused-pkg2
""")

        dependencies = "pkg1\npkg2\nunused-pkg1\nunused-pkg2"
        source_code = "import pkg1\nimport pkg2"

        result = await agent.find_unused_dependencies(dependencies, source_code)

        assert len(result) >= 2
        assert "unused-pkg1" in result

    @pytest.mark.asyncio
    async def test_find_unused_dependencies_error(self, agent):
        """Test unused dependencies error handling"""
        agent._generate_response = AsyncMock(side_effect=Exception("Error"))

        result = await agent.find_unused_dependencies("deps", "code")

        assert result == []

    @pytest.mark.asyncio
    async def test_find_unused_dependencies_parses_bullets(self, agent):
        """Test parsing bullet points in response"""
        agent._generate_response = AsyncMock(return_value="""
* package-a
* package-b
- package-c
""")

        result = await agent.find_unused_dependencies("deps", "code")

        assert "package-a" in result
        assert "package-b" in result
        assert "package-c" in result

    @pytest.mark.asyncio
    async def test_suggest_alternatives(self, agent):
        """Test suggesting alternative packages"""
        agent._generate_response = AsyncMock(return_value="""
Alternatives for requests:
1. httpx - Modern async HTTP client
2. aiohttp - Async HTTP
""")

        result = await agent.suggest_alternatives("requests", "HTTP requests")

        assert len(result) >= 1
        assert "comparison" in result[0]

    @pytest.mark.asyncio
    async def test_suggest_alternatives_error(self, agent):
        """Test alternatives suggestion error handling"""
        agent._generate_response = AsyncMock(side_effect=Exception("Error"))

        result = await agent.suggest_alternatives("pkg", "use case")

        assert result == []

    @pytest.mark.asyncio
    async def test_analyze_dependency_tree(self, agent):
        """Test dependency tree analysis"""
        agent._generate_response = AsyncMock(return_value="""
Dependency tree analysis:
- No circular dependencies detected
- Maximum depth: 3 levels
- Total transitive dependencies: 25
""")

        result = await agent.analyze_dependency_tree("deps", "python")

        assert "summary" in result
        assert "health_score" in result
        assert result["health_score"] == 75

    @pytest.mark.asyncio
    async def test_analyze_dependency_tree_error(self, agent):
        """Test tree analysis error handling"""
        agent._generate_response = AsyncMock(side_effect=Exception("Error"))

        result = await agent.analyze_dependency_tree("deps")

        assert "failed" in result["summary"].lower()
        assert result["health_score"] == 0

    @pytest.mark.asyncio
    async def test_check_license_compatibility(self, agent):
        """Test license compatibility check"""
        agent._generate_response = AsyncMock(return_value="""
License Analysis:
All dependencies are compatible with MIT license.
No copyleft obligations detected.
""")

        result = await agent.check_license_compatibility("deps", "MIT")

        assert result["status"] == "compatible"
        assert "recommendations" in result

    @pytest.mark.asyncio
    async def test_check_license_compatibility_error(self, agent):
        """Test license check error handling"""
        agent._generate_response = AsyncMock(side_effect=Exception("Error"))

        result = await agent.check_license_compatibility("deps", "MIT")

        assert result["status"] == "error"

    def test_agent_initialization(self):
        """Test agent initialization"""
        agent = DependencyAnalyzerAgent()
        assert agent.name == "DependencyAnalyzerAgent"

    def test_agent_inherits_from_base(self):
        """Test agent inherits from BaseAgent"""
        from aiops.agents.base_agent import BaseAgent
        agent = DependencyAnalyzerAgent()
        assert isinstance(agent, BaseAgent)


class TestDependencyAnalyzerEdgeCases:
    """Edge case tests"""

    @pytest.fixture
    def agent(self):
        return DependencyAnalyzerAgent()

    @pytest.mark.asyncio
    async def test_empty_dependencies(self, agent):
        """Test with empty dependencies"""
        agent._generate_structured_response = AsyncMock(
            return_value=DependencyAnalysisResult(
                total_dependencies=0,
                outdated_count=0,
                summary="No dependencies",
                dependencies=[],
                issues=[],
                recommendations=[],
                license_summary={},
                dependency_tree_insights=[]
            )
        )

        result = await agent.execute("")
        assert result.total_dependencies == 0

    @pytest.mark.asyncio
    async def test_very_long_dependencies(self, agent):
        """Test with very long dependency list"""
        agent._generate_structured_response = AsyncMock(
            return_value=DependencyAnalysisResult(
                total_dependencies=100,
                outdated_count=10,
                summary="Large project",
                dependencies=[],
                issues=[],
                recommendations=[],
                license_summary={},
                dependency_tree_insights=[]
            )
        )

        deps = "\n".join([f"package-{i}==1.0.0" for i in range(100)])
        result = await agent.execute(deps)
        assert result is not None

    @pytest.mark.asyncio
    async def test_special_characters_in_deps(self, agent):
        """Test with special characters in dependency names"""
        agent._generate_structured_response = AsyncMock(
            return_value=DependencyAnalysisResult(
                total_dependencies=1,
                outdated_count=0,
                summary="OK",
                dependencies=[],
                issues=[],
                recommendations=[],
                license_summary={},
                dependency_tree_insights=[]
            )
        )

        deps = "my-package[extra]>=1.0.0,<2.0.0"
        result = await agent.execute(deps)
        assert result is not None

    @pytest.mark.asyncio
    async def test_truncates_long_source_code(self, agent):
        """Test that long source code is truncated"""
        agent._generate_response = AsyncMock(return_value="- unused")

        long_code = "import x\n" * 10000

        await agent.find_unused_dependencies("deps", long_code)

        call_args = agent._generate_response.call_args
        prompt = call_args[0][0]
        # Source code should be truncated to 2000 chars
        assert len(prompt) < len(long_code)
