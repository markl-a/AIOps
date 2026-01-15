"""
Unit tests for Code Quality Agent
"""

import pytest
from unittest.mock import AsyncMock
from aiops.agents.code_quality import (
    CodeQualityAgent,
    QualityMetric,
    CodeSmell,
    CodeQualityResult
)


class TestQualityMetric:
    """Tests for QualityMetric model"""

    def test_create_metric(self):
        """Test creating a quality metric"""
        metric = QualityMetric(
            name="Maintainability",
            score=85.0,
            status="good",
            details="Code is well-structured",
            recommendations=["Add more comments", "Reduce nesting"]
        )
        assert metric.name == "Maintainability"
        assert metric.score == 85.0
        assert len(metric.recommendations) == 2

    def test_metric_statuses(self):
        """Test different metric statuses"""
        for status in ["excellent", "good", "fair", "poor"]:
            metric = QualityMetric(
                name="Test",
                score=50.0,
                status=status,
                details="Test",
                recommendations=[]
            )
            assert metric.status == status


class TestCodeSmell:
    """Tests for CodeSmell model"""

    def test_create_code_smell(self):
        """Test creating a code smell"""
        smell = CodeSmell(
            type="long_method",
            severity="high",
            location="src/main.py:50",
            description="Method is too long (120 lines)",
            refactoring_suggestion="Extract smaller methods",
            impact="Reduced maintainability"
        )
        assert smell.type == "long_method"
        assert smell.severity == "high"

    def test_smell_types(self):
        """Test different smell types"""
        for smell_type in ["long_method", "god_class", "duplicate_code", "feature_envy"]:
            smell = CodeSmell(
                type=smell_type,
                severity="medium",
                location="file:10",
                description="Test",
                refactoring_suggestion="Fix it",
                impact="Impact"
            )
            assert smell.type == smell_type

    def test_smell_severities(self):
        """Test different severities"""
        for severity in ["high", "medium", "low"]:
            smell = CodeSmell(
                type="test",
                severity=severity,
                location="file:1",
                description="Test",
                refactoring_suggestion="Fix",
                impact="Impact"
            )
            assert smell.severity == severity


class TestCodeQualityResult:
    """Tests for CodeQualityResult model"""

    def test_create_result(self):
        """Test creating quality result"""
        result = CodeQualityResult(
            overall_quality_score=85.0,
            grade="B",
            summary="Good code quality",
            metrics=[],
            code_smells=[],
            maintainability_index=80.0,
            technical_debt={"hours": 4},
            best_practices={"naming": "good"},
            recommendations=["Add tests"]
        )
        assert result.overall_quality_score == 85.0
        assert result.grade == "B"

    def test_result_grades(self):
        """Test different grade values"""
        for grade in ["A", "B", "C", "D", "F"]:
            result = CodeQualityResult(
                overall_quality_score=50.0,
                grade=grade,
                summary="Test",
                metrics=[],
                code_smells=[],
                maintainability_index=50.0,
                technical_debt={},
                best_practices={},
                recommendations=[]
            )
            assert result.grade == grade


class TestCodeQualityAgent:
    """Tests for CodeQualityAgent"""

    @pytest.fixture
    def agent(self):
        """Create agent instance"""
        return CodeQualityAgent()

    @pytest.fixture
    def mock_quality_result(self):
        """Mock quality result"""
        return CodeQualityResult(
            overall_quality_score=75.0,
            grade="C",
            summary="Acceptable quality with room for improvement",
            metrics=[
                QualityMetric(
                    name="Maintainability",
                    score=70.0,
                    status="fair",
                    details="Some complex methods",
                    recommendations=["Reduce complexity"]
                )
            ],
            code_smells=[
                CodeSmell(
                    type="long_method",
                    severity="medium",
                    location="main.py:50",
                    description="Method exceeds 50 lines",
                    refactoring_suggestion="Extract smaller methods",
                    impact="Harder to maintain"
                )
            ],
            maintainability_index=65.0,
            technical_debt={"refactoring_hours": 8},
            best_practices={"naming": "good", "documentation": "fair"},
            recommendations=["Add docstrings", "Reduce method length"]
        )

    @pytest.mark.asyncio
    async def test_execute_basic(self, agent, mock_quality_result):
        """Test basic execution"""
        agent._generate_structured_response = AsyncMock(return_value=mock_quality_result)

        code = """
def calculate_sum(numbers):
    total = 0
    for n in numbers:
        total += n
    return total
"""
        result = await agent.execute(code)

        assert isinstance(result, CodeQualityResult)
        assert result.overall_quality_score == 75.0
        assert result.grade == "C"

    @pytest.mark.asyncio
    async def test_execute_with_language(self, agent, mock_quality_result):
        """Test execution with specific language"""
        agent._generate_structured_response = AsyncMock(return_value=mock_quality_result)

        await agent.execute("code", language="javascript")

        call_args = agent._generate_structured_response.call_args
        system_prompt = call_args[1]["system_prompt"]
        assert "javascript" in system_prompt.lower()

    @pytest.mark.asyncio
    async def test_execute_with_project_type(self, agent, mock_quality_result):
        """Test execution with project type"""
        agent._generate_structured_response = AsyncMock(return_value=mock_quality_result)

        await agent.execute("code", project_type="web api")

        call_args = agent._generate_structured_response.call_args
        system_prompt = call_args[1]["system_prompt"]
        assert "web api" in system_prompt.lower()

    @pytest.mark.asyncio
    async def test_execute_error_handling(self, agent):
        """Test error handling"""
        agent._generate_structured_response = AsyncMock(
            side_effect=Exception("API error")
        )

        result = await agent.execute("code")

        assert result.overall_quality_score == 0
        assert result.grade == "F"
        assert "failed" in result.summary.lower()

    def test_create_system_prompt_python(self, agent):
        """Test system prompt for Python"""
        prompt = agent._create_system_prompt("python")

        assert "python" in prompt.lower()
        assert "maintainability" in prompt.lower()
        assert "code smell" in prompt.lower()

    def test_create_system_prompt_with_project_type(self, agent):
        """Test system prompt with project type"""
        prompt = agent._create_system_prompt("python", project_type="api")

        assert "api" in prompt.lower()
        assert "domain-specific" in prompt.lower()

    def test_create_user_prompt(self, agent):
        """Test user prompt creation"""
        code = "def test(): pass"
        prompt = agent._create_user_prompt(code)

        assert code in prompt
        assert "quality" in prompt.lower()

    @pytest.mark.asyncio
    async def test_calculate_complexity(self, agent):
        """Test complexity calculation"""
        agent._generate_response = AsyncMock(return_value="Complexity analysis...")

        result = await agent.calculate_complexity("def f(): pass")

        assert "cyclomatic_complexity" in result
        assert "cognitive_complexity" in result

    @pytest.mark.asyncio
    async def test_calculate_complexity_error(self, agent):
        """Test complexity calculation error handling"""
        agent._generate_response = AsyncMock(side_effect=Exception("Error"))

        result = await agent.calculate_complexity("code")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_detect_duplicates(self, agent):
        """Test duplicate detection"""
        agent._generate_response = AsyncMock(
            return_value="Found duplicate code in lines 10-15 and 30-35"
        )

        result = await agent.detect_duplicates("code with duplicates")

        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_detect_duplicates_no_duplicates(self, agent):
        """Test when no duplicates found"""
        agent._generate_response = AsyncMock(
            return_value="No significant duplication found"
        )

        result = await agent.detect_duplicates("clean code")

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_detect_duplicates_error(self, agent):
        """Test duplicate detection error handling"""
        agent._generate_response = AsyncMock(side_effect=Exception("Error"))

        result = await agent.detect_duplicates("code")

        assert result == []

    @pytest.mark.asyncio
    async def test_suggest_refactoring(self, agent):
        """Test refactoring suggestions"""
        agent._generate_response = AsyncMock(
            return_value="1. Extract method for repeated logic\n2. Use constants"
        )

        result = await agent.suggest_refactoring("messy code")

        assert "summary" in result
        assert "detailed_suggestions" in result

    @pytest.mark.asyncio
    async def test_suggest_refactoring_with_focus(self, agent):
        """Test refactoring with specific focus"""
        agent._generate_response = AsyncMock(return_value="Focus on complexity")

        await agent.suggest_refactoring("code", focus="complexity")

        call_args = agent._generate_response.call_args
        prompt = call_args[0][0]
        assert "complexity" in prompt

    @pytest.mark.asyncio
    async def test_suggest_refactoring_error(self, agent):
        """Test refactoring suggestion error handling"""
        agent._generate_response = AsyncMock(side_effect=Exception("Error"))

        result = await agent.suggest_refactoring("code")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_generate_quality_report_markdown(self, agent):
        """Test markdown report generation"""
        result = CodeQualityResult(
            overall_quality_score=80.0,
            grade="B",
            summary="Good quality",
            metrics=[
                QualityMetric(
                    name="Maintainability",
                    score=85.0,
                    status="good",
                    details="Well structured",
                    recommendations=["Add comments"]
                )
            ],
            code_smells=[
                CodeSmell(
                    type="long_method",
                    severity="medium",
                    location="main.py:50",
                    description="Too long",
                    refactoring_suggestion="Extract",
                    impact="Hard to maintain"
                )
            ],
            maintainability_index=75.0,
            technical_debt={"hours": 4},
            best_practices={},
            recommendations=["Improve tests"]
        )

        report = await agent.generate_quality_report(result, format="markdown")

        assert "# Code Quality Report" in report
        assert "80.0/100" in report
        assert "Grade: B" in report
        assert "Maintainability" in report
        assert "long_method" in report

    @pytest.mark.asyncio
    async def test_generate_quality_report_unsupported_format(self, agent):
        """Test unsupported report format"""
        result = CodeQualityResult(
            overall_quality_score=80.0,
            grade="B",
            summary="Good",
            metrics=[],
            code_smells=[],
            maintainability_index=75.0,
            technical_debt={},
            best_practices={},
            recommendations=[]
        )

        report = await agent.generate_quality_report(result, format="pdf")

        assert "not yet implemented" in report.lower()

    def test_agent_initialization(self):
        """Test agent initialization"""
        agent = CodeQualityAgent()
        assert agent.name == "CodeQualityAgent"

    def test_agent_inherits_from_base(self):
        """Test agent inherits from BaseAgent"""
        from aiops.agents.base_agent import BaseAgent
        agent = CodeQualityAgent()
        assert isinstance(agent, BaseAgent)


class TestCodeQualityEdgeCases:
    """Edge case tests"""

    @pytest.fixture
    def agent(self):
        return CodeQualityAgent()

    @pytest.mark.asyncio
    async def test_empty_code(self, agent):
        """Test with empty code"""
        agent._generate_structured_response = AsyncMock(
            return_value=CodeQualityResult(
                overall_quality_score=0,
                grade="F",
                summary="No code to analyze",
                metrics=[],
                code_smells=[],
                maintainability_index=0,
                technical_debt={},
                best_practices={},
                recommendations=[]
            )
        )

        result = await agent.execute("")
        assert result is not None

    @pytest.mark.asyncio
    async def test_very_long_code(self, agent):
        """Test with very long code"""
        agent._generate_structured_response = AsyncMock(
            return_value=CodeQualityResult(
                overall_quality_score=50.0,
                grade="C",
                summary="Large codebase",
                metrics=[],
                code_smells=[],
                maintainability_index=50.0,
                technical_debt={"hours": 100},
                best_practices={},
                recommendations=[]
            )
        )

        long_code = "def f(): pass\n" * 1000
        result = await agent.execute(long_code)
        assert result is not None

    @pytest.mark.asyncio
    async def test_code_with_special_characters(self, agent):
        """Test code with special characters"""
        agent._generate_structured_response = AsyncMock(
            return_value=CodeQualityResult(
                overall_quality_score=70.0,
                grade="C",
                summary="OK",
                metrics=[],
                code_smells=[],
                maintainability_index=70.0,
                technical_debt={},
                best_practices={},
                recommendations=[]
            )
        )

        code = '''
def test():
    """Test with 'quotes' and "double quotes"."""
    return "Hello\\nWorld"
'''
        result = await agent.execute(code)
        assert result is not None

    @pytest.mark.asyncio
    async def test_report_with_empty_metrics(self, agent):
        """Test report generation with empty metrics"""
        result = CodeQualityResult(
            overall_quality_score=80.0,
            grade="B",
            summary="Good",
            metrics=[],
            code_smells=[],
            maintainability_index=75.0,
            technical_debt={},
            best_practices={},
            recommendations=[]
        )

        report = await agent.generate_quality_report(result)

        assert "# Code Quality Report" in report
        assert "80.0/100" in report

    @pytest.mark.asyncio
    async def test_report_with_many_smells(self, agent):
        """Test report with many code smells"""
        smells = [
            CodeSmell(
                type=f"smell_{i}",
                severity="medium",
                location=f"file:{i}",
                description=f"Issue {i}",
                refactoring_suggestion="Fix",
                impact="Impact"
            )
            for i in range(10)
        ]
        result = CodeQualityResult(
            overall_quality_score=40.0,
            grade="D",
            summary="Poor quality",
            metrics=[],
            code_smells=smells,
            maintainability_index=30.0,
            technical_debt={"hours": 40},
            best_practices={},
            recommendations=["Major refactoring needed"]
        )

        report = await agent.generate_quality_report(result)

        assert "10 detected" in report
        for i in range(10):
            assert f"smell_{i}" in report
