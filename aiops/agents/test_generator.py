"""Test Generator Agent - Automated test generation using LLM."""

from typing import List, Optional
from pydantic import BaseModel, Field
from aiops.agents.base_agent import BaseAgent
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class TestCase(BaseModel):
    """Represents a generated test case."""

    name: str = Field(description="Test case name")
    description: str = Field(description="What the test verifies")
    test_code: str = Field(description="Test code implementation")
    test_type: str = Field(description="Type: unit, integration, or e2e")
    priority: str = Field(description="Priority: high, medium, low")


class TestSuite(BaseModel):
    """Collection of generated test cases."""

    framework: str = Field(description="Testing framework used (pytest, jest, etc.)")
    test_cases: List[TestCase] = Field(description="List of test cases")
    setup_code: Optional[str] = Field(default=None, description="Setup/fixture code if needed")
    coverage_notes: str = Field(description="Notes on test coverage")
    edge_cases: List[str] = Field(description="Edge cases covered by tests")


class TestGeneratorAgent(BaseAgent):
    """Agent for automated test generation."""

    def __init__(self, **kwargs):
        super().__init__(name="TestGeneratorAgent", **kwargs)

    async def execute(
        self,
        code: str,
        language: str = "python",
        test_framework: Optional[str] = None,
        context: Optional[str] = None,
    ) -> TestSuite:
        """
        Generate tests for given code.

        Args:
            code: Code to generate tests for
            language: Programming language
            test_framework: Testing framework to use (auto-detected if not provided)
            context: Additional context about the code

        Returns:
            TestSuite with generated test cases
        """
        logger.info(f"Generating tests for {language} code ({len(code)} chars)")

        # Auto-detect framework if not provided
        if not test_framework:
            test_framework = self._detect_framework(language)

        system_prompt = self._create_system_prompt(language, test_framework)
        user_prompt = self._create_user_prompt(code, context)

        try:
            result = await self._generate_structured_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                schema=TestSuite,
            )

            logger.info(
                f"Generated {len(result.test_cases)} test cases using {result.framework}"
            )

            return result

        except Exception as e:
            logger.error(f"Test generation failed: {e}")
            return TestSuite(
                framework=test_framework,
                test_cases=[],
                coverage_notes=f"Generation failed: {str(e)}",
                edge_cases=[],
            )

    def _detect_framework(self, language: str) -> str:
        """Auto-detect testing framework based on language."""
        frameworks = {
            "python": "pytest",
            "javascript": "jest",
            "typescript": "jest",
            "java": "junit",
            "go": "testing",
            "rust": "rust-test",
            "ruby": "rspec",
            "php": "phpunit",
        }
        return frameworks.get(language.lower(), "unittest")

    def _create_system_prompt(self, language: str, framework: str) -> str:
        """Create system prompt for test generation."""
        return f"""You are an expert test engineer specializing in {language} and {framework}.

Your task is to generate comprehensive, production-ready tests that:

1. **Cover Edge Cases**: Test boundary conditions, null/undefined, empty inputs, etc.
2. **Test Happy Paths**: Verify normal, expected behavior
3. **Test Error Cases**: Check error handling and validation
4. **Follow Best Practices**: Use proper assertions, mocks, fixtures
5. **Are Maintainable**: Clear names, good documentation, DRY principle
6. **Are Fast**: Unit tests should be fast and isolated

Test Types:
- **unit**: Test individual functions/methods in isolation
- **integration**: Test interaction between components
- **e2e**: Test complete user flows (when applicable)

Generate realistic, runnable test code following {framework} conventions.
Include setup/teardown code if needed.
Make tests deterministic and reliable.
"""

    def _create_user_prompt(self, code: str, context: Optional[str] = None) -> str:
        """Create user prompt for test generation."""
        prompt = "Generate comprehensive tests for the following code:\n\n"

        if context:
            prompt += f"**Context**: {context}\n\n"

        prompt += f"```\n{code}\n```\n\n"
        prompt += """Generate tests that:
- Cover all major functionality
- Test edge cases and error conditions
- Follow testing best practices
- Are production-ready and runnable

Include notes on what edge cases are covered.
"""

        return prompt

    async def generate_from_requirements(
        self,
        requirements: str,
        language: str = "python",
        test_framework: Optional[str] = None,
    ) -> TestSuite:
        """
        Generate tests from requirements/specifications.

        Args:
            requirements: Requirements or user stories
            language: Target programming language
            test_framework: Testing framework to use

        Returns:
            TestSuite with generated test cases
        """
        logger.info(f"Generating tests from requirements ({len(requirements)} chars)")

        if not test_framework:
            test_framework = self._detect_framework(language)

        system_prompt = f"""You are an expert in Test-Driven Development (TDD) and {language}.

Generate test cases based on requirements/specifications.
Focus on:
1. Acceptance criteria
2. User stories
3. Business logic validation
4. API contracts
5. Data validation

Write tests that would drive the implementation of the feature.
"""

        user_prompt = f"""Generate test cases for the following requirements:

{requirements}

Target language: {language}
Test framework: {test_framework}

Create comprehensive tests that validate all requirements.
"""

        try:
            result = await self._generate_structured_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                schema=TestSuite,
            )

            logger.info(f"Generated {len(result.test_cases)} test cases from requirements")
            return result

        except Exception as e:
            logger.error(f"Requirements-based test generation failed: {e}")
            return TestSuite(
                framework=test_framework,
                test_cases=[],
                coverage_notes=f"Generation failed: {str(e)}",
                edge_cases=[],
            )
