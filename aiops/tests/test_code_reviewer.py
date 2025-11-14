"""Tests for Code Review Agent."""

import pytest
from unittest.mock import AsyncMock, patch
from aiops.agents.code_reviewer import CodeReviewAgent, CodeReviewResult, CodeIssue


@pytest.fixture
def mock_code_review_agent():
    """Create a mock code review agent."""
    agent = CodeReviewAgent()
    return agent


@pytest.mark.asyncio
async def test_code_review_basic(mock_code_review_agent, sample_code):
    """Test basic code review functionality."""
    # Mock the LLM response
    mock_result = CodeReviewResult(
        overall_score=75.0,
        summary="Code has some issues that should be addressed",
        issues=[
            CodeIssue(
                severity="medium",
                category="performance",
                line_number=3,
                description="Using range(len()) is not Pythonic",
                suggestion="Use enumerate() or iterate directly",
                code_snippet="for i in range(len(numbers)):",
            )
        ],
        strengths=["Function has a clear purpose", "Variable names are descriptive"],
        recommendations=["Use more Pythonic iteration", "Add type hints"],
    )

    with patch.object(
        mock_code_review_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await mock_code_review_agent.execute(code=sample_code, language="python")

        assert isinstance(result, CodeReviewResult)
        assert result.overall_score == 75.0
        assert len(result.issues) == 1
        assert result.issues[0].severity == "medium"
        assert len(result.strengths) == 2


@pytest.mark.asyncio
async def test_code_review_with_standards(mock_code_review_agent, sample_code):
    """Test code review with custom standards."""
    standards = ["PEP 8", "Type hints required", "Docstrings required"]

    mock_result = CodeReviewResult(
        overall_score=60.0,
        summary="Code violates several standards",
        issues=[
            CodeIssue(
                severity="low",
                category="style",
                description="Missing type hints",
                suggestion="Add type hints to function signature",
            )
        ],
        strengths=[],
        recommendations=["Add type hints", "Add docstring"],
    )

    with patch.object(
        mock_code_review_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await mock_code_review_agent.execute(
            code=sample_code, language="python", standards=standards
        )

        assert result.overall_score == 60.0
        assert any("type hints" in issue.description.lower() for issue in result.issues)


@pytest.mark.asyncio
async def test_review_diff(mock_code_review_agent):
    """Test diff review functionality."""
    diff = """
--- a/file.py
+++ b/file.py
@@ -1,3 +1,4 @@
 def calculate():
-    return 1 + 1
+    # TODO: implement
+    return 0
"""

    mock_result = CodeReviewResult(
        overall_score=50.0,
        summary="Changes introduce a TODO",
        issues=[
            CodeIssue(
                severity="high",
                category="bug",
                description="Function now returns incorrect value",
                suggestion="Implement the actual calculation",
            )
        ],
        strengths=[],
        recommendations=["Complete the implementation before merging"],
    )

    with patch.object(
        mock_code_review_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await mock_code_review_agent.review_diff(diff=diff)

        assert isinstance(result, CodeReviewResult)
        assert result.overall_score == 50.0
        assert len(result.issues) >= 1


@pytest.mark.asyncio
async def test_code_review_error_handling(mock_code_review_agent):
    """Test error handling in code review."""
    with patch.object(
        mock_code_review_agent,
        "_generate_structured_response",
        side_effect=Exception("API Error"),
    ):
        result = await mock_code_review_agent.execute(
            code="def test(): pass", language="python"
        )

        # Should return a fallback result
        assert isinstance(result, CodeReviewResult)
        assert result.overall_score == 0
        assert "failed" in result.summary.lower()


def test_create_system_prompt(mock_code_review_agent):
    """Test system prompt creation."""
    prompt = mock_code_review_agent._create_system_prompt("python", ["PEP 8"])

    assert "python" in prompt.lower()
    assert "security" in prompt.lower()
    assert "PEP 8" in prompt


def test_create_user_prompt(mock_code_review_agent, sample_code):
    """Test user prompt creation."""
    prompt = mock_code_review_agent._create_user_prompt(
        sample_code, context="This is a utility function"
    )

    assert "review" in prompt.lower()
    assert sample_code in prompt
    assert "utility function" in prompt
