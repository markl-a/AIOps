"""Code Review Agent - Automated code review using LLM."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from aiops.agents.base_agent import BaseAgent
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class CodeIssue(BaseModel):
    """Represents a code issue found during review."""

    severity: str = Field(description="Severity level: critical, high, medium, low, info")
    category: str = Field(description="Issue category: security, performance, style, bug, maintainability")
    line_number: Optional[int] = Field(default=None, description="Line number where issue was found")
    description: str = Field(description="Description of the issue")
    suggestion: str = Field(description="Suggested fix or improvement")
    code_snippet: Optional[str] = Field(default=None, description="Relevant code snippet")


class CodeReviewResult(BaseModel):
    """Result of code review."""

    overall_score: float = Field(description="Overall code quality score (0-100)")
    summary: str = Field(description="Summary of the review")
    issues: List[CodeIssue] = Field(description="List of issues found")
    strengths: List[str] = Field(description="Code strengths and good practices")
    recommendations: List[str] = Field(description="General recommendations")


class CodeReviewAgent(BaseAgent):
    """Agent for automated code review."""

    def __init__(self, **kwargs):
        super().__init__(name="CodeReviewAgent", **kwargs)

    async def execute(
        self,
        code: str,
        language: str = "python",
        context: Optional[str] = None,
        standards: Optional[List[str]] = None,
    ) -> CodeReviewResult:
        """
        Review code and provide feedback.

        Args:
            code: Code to review
            language: Programming language
            context: Additional context about the code
            standards: Specific coding standards to check against

        Returns:
            CodeReviewResult with issues and recommendations
        """
        logger.info(f"Starting code review for {language} code ({len(code)} chars)")

        system_prompt = self._create_system_prompt(language, standards)
        user_prompt = self._create_user_prompt(code, context)

        try:
            # Generate structured response
            result = await self._generate_structured_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                schema=CodeReviewResult,
            )

            logger.info(
                f"Code review completed: {len(result.issues)} issues found, "
                f"score: {result.overall_score}/100"
            )

            return result

        except Exception as e:
            logger.error(f"Code review failed: {e}")
            # Return a fallback result
            return CodeReviewResult(
                overall_score=0,
                summary=f"Review failed: {str(e)}",
                issues=[],
                strengths=[],
                recommendations=["Please retry the review"],
            )

    def _create_system_prompt(
        self, language: str, standards: Optional[List[str]] = None
    ) -> str:
        """Create system prompt for code review."""
        prompt = f"""You are an expert code reviewer specializing in {language}.

Your task is to review code and provide constructive feedback focusing on:

1. **Security Issues**: Identify vulnerabilities like SQL injection, XSS, command injection, etc.
2. **Performance**: Spot inefficient algorithms, memory leaks, unnecessary computations
3. **Code Quality**: Check for maintainability, readability, and adherence to best practices
4. **Bugs**: Identify potential runtime errors, edge cases, and logical errors
5. **Design Patterns**: Suggest better architectural patterns when applicable

Severity Levels:
- critical: Security vulnerabilities, data loss risks, critical bugs
- high: Major bugs, significant performance issues, poor design
- medium: Code smells, minor bugs, style inconsistencies
- low: Minor improvements, style suggestions
- info: Informational notes, educational tips

"""
        if standards:
            prompt += f"\nAdditional Standards to Check:\n"
            for standard in standards:
                prompt += f"- {standard}\n"

        prompt += """
Provide honest, objective feedback. Be constructive and specific.
For each issue, provide a clear suggestion for improvement.
Also highlight what the code does well.
"""

        return prompt

    def _create_user_prompt(self, code: str, context: Optional[str] = None) -> str:
        """Create user prompt for code review."""
        prompt = "Please review the following code:\n\n"

        if context:
            prompt += f"**Context**: {context}\n\n"

        prompt += f"```\n{code}\n```\n\n"
        prompt += "Provide a comprehensive code review with issues, strengths, and recommendations."

        return prompt

    async def review_diff(
        self,
        diff: str,
        base_context: Optional[str] = None,
    ) -> CodeReviewResult:
        """
        Review code changes in a diff.

        Args:
            diff: Git diff or code changes
            base_context: Context about the codebase

        Returns:
            CodeReviewResult for the changes
        """
        logger.info(f"Reviewing code diff ({len(diff)} chars)")

        system_prompt = """You are an expert code reviewer analyzing code changes (diffs).

Focus on:
1. Impact of changes on existing functionality
2. Potential breaking changes
3. New bugs or security issues introduced
4. Code quality of the changes
5. Test coverage for new/modified code

Provide specific feedback on the changes, not the entire codebase.
"""

        user_prompt = f"""Review the following code changes:

{f"**Base Context**: {base_context}" if base_context else ""}

**Diff**:
```
{diff}
```

Analyze the changes and provide feedback.
"""

        try:
            result = await self._generate_structured_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                schema=CodeReviewResult,
            )

            logger.info(f"Diff review completed: {len(result.issues)} issues found")
            return result

        except Exception as e:
            logger.error(f"Diff review failed: {e}")
            return CodeReviewResult(
                overall_score=0,
                summary=f"Review failed: {str(e)}",
                issues=[],
                strengths=[],
                recommendations=[],
            )
