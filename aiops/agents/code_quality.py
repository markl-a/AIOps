"""Code Quality Agent - Comprehensive code quality analysis."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from aiops.agents.base_agent import BaseAgent
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class QualityMetric(BaseModel):
    """Code quality metric."""

    name: str = Field(description="Metric name")
    score: float = Field(description="Score (0-100)")
    status: str = Field(description="Status: excellent, good, fair, poor")
    details: str = Field(description="Metric details")
    recommendations: List[str] = Field(description="Improvement recommendations")


class CodeSmell(BaseModel):
    """Code smell detection."""

    type: str = Field(description="Smell type: long_method, god_class, duplicate_code, etc.")
    severity: str = Field(description="Severity: high, medium, low")
    location: str = Field(description="Location (file:line or class/method)")
    description: str = Field(description="Description of the smell")
    refactoring_suggestion: str = Field(description="How to refactor")
    impact: str = Field(description="Impact on maintainability")


class CodeQualityResult(BaseModel):
    """Comprehensive code quality result."""

    overall_quality_score: float = Field(description="Overall quality score (0-100)")
    grade: str = Field(description="Quality grade: A, B, C, D, F")
    summary: str = Field(description="Quality summary")
    metrics: List[QualityMetric] = Field(description="Individual quality metrics")
    code_smells: List[CodeSmell] = Field(description="Detected code smells")
    maintainability_index: float = Field(description="Maintainability index (0-100)")
    technical_debt: Dict[str, Any] = Field(description="Technical debt estimate")
    best_practices: Dict[str, str] = Field(description="Best practices compliance")
    recommendations: List[str] = Field(description="Priority recommendations")


class CodeQualityAgent(BaseAgent):
    """Agent for comprehensive code quality analysis."""

    def __init__(self, **kwargs):
        super().__init__(name="CodeQualityAgent", **kwargs)

    async def execute(
        self,
        code: str,
        language: str = "python",
        project_type: Optional[str] = None,
    ) -> CodeQualityResult:
        """
        Perform comprehensive code quality analysis.

        Args:
            code: Code to analyze
            language: Programming language
            project_type: Project type (web, api, library, etc.)

        Returns:
            CodeQualityResult with detailed analysis
        """
        logger.info(f"Analyzing code quality for {language} code")

        system_prompt = self._create_system_prompt(language, project_type)
        user_prompt = self._create_user_prompt(code)

        try:
            result = await self._generate_structured_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                schema=CodeQualityResult,
            )

            logger.info(
                f"Quality analysis completed: score {result.overall_quality_score}/100, "
                f"grade {result.grade}, {len(result.code_smells)} smells detected"
            )

            return result

        except Exception as e:
            logger.error(f"Code quality analysis failed: {e}")
            return CodeQualityResult(
                overall_quality_score=0,
                grade="F",
                summary=f"Analysis failed: {str(e)}",
                metrics=[],
                code_smells=[],
                maintainability_index=0,
                technical_debt={},
                best_practices={},
                recommendations=[],
            )

    def _create_system_prompt(
        self, language: str, project_type: Optional[str] = None
    ) -> str:
        """Create system prompt for quality analysis."""
        prompt = f"""You are an expert code quality analyst specializing in {language}.

Analyze code quality across multiple dimensions:

1. **Maintainability** (0-100):
   - Code complexity
   - Modularity
   - Clear naming
   - Documentation
   - Code organization

2. **Readability** (0-100):
   - Clear logic flow
   - Consistent style
   - Meaningful names
   - Appropriate comments
   - Code structure

3. **Reliability** (0-100):
   - Error handling
   - Edge cases
   - Input validation
   - Defensive programming
   - Null safety

4. **Testability** (0-100):
   - Testable design
   - Dependency injection
   - Pure functions
   - Mocking capability
   - Test coverage potential

5. **Reusability** (0-100):
   - Generic implementations
   - Modularity
   - Loose coupling
   - Interface design
   - DRY principle

6. **Efficiency** (0-100):
   - Algorithm efficiency
   - Resource usage
   - Time complexity
   - Space complexity
   - Optimization opportunities

**Code Smells to Detect**:
- Long Method (>50 lines)
- Long Parameter List (>5 parameters)
- God Class (>500 lines or >20 methods)
- Duplicate Code
- Large Class
- Long Method
- Feature Envy
- Data Clumps
- Primitive Obsession
- Switch Statements (could be polymorphism)
- Lazy Class
- Speculative Generality
- Temporary Field
- Message Chains
- Middle Man
- Inappropriate Intimacy
- Incomplete Library Class
- Data Class
- Refused Bequest
- Comments (excessive comments masking bad code)

**Maintainability Index**: Calculate based on:
- Cyclomatic complexity
- Lines of code
- Halstead volume
- Comment percentage

**Technical Debt**: Estimate refactoring effort in hours.

"""

        if project_type:
            prompt += f"\n**Project Type**: {project_type}\nApply domain-specific quality standards.\n"

        prompt += """
Provide honest, actionable feedback.
Focus on highest-impact improvements.
"""

        return prompt

    def _create_user_prompt(self, code: str) -> str:
        """Create user prompt for quality analysis."""
        prompt = "Perform comprehensive code quality analysis:\n\n"

        prompt += f"**Code**:\n```\n{code}\n```\n\n"

        prompt += """Analyze:
1. All quality metrics (maintainability, readability, reliability, etc.)
2. Code smells and anti-patterns
3. Maintainability index
4. Technical debt estimate
5. Best practices compliance
6. Priority improvement recommendations

Provide specific, actionable feedback.
"""

        return prompt

    async def calculate_complexity(
        self,
        code: str,
        language: str = "python",
    ) -> Dict[str, Any]:
        """
        Calculate code complexity metrics.

        Args:
            code: Code to analyze
            language: Programming language

        Returns:
            Complexity metrics
        """
        logger.info("Calculating code complexity")

        system_prompt = f"""You are an expert in code complexity analysis for {language}.

Calculate:
- Cyclomatic Complexity (McCabe)
- Cognitive Complexity
- Nesting Depth
- Lines of Code (LOC)
- Maintainability Index

Provide per-function and overall metrics.
"""

        user_prompt = f"""Calculate complexity metrics:

```{language}
{code}
```

Provide:
1. Cyclomatic complexity per function
2. Overall complexity score
3. Most complex functions
4. Recommendations for simplification
"""

        try:
            response = await self._generate_response(user_prompt, system_prompt)

            # In production, calculate actual metrics
            complexity = {
                "cyclomatic_complexity": 10,  # Placeholder
                "cognitive_complexity": 15,  # Placeholder
                "average_nesting": 2,
                "analysis": response,
            }

            logger.info("Complexity calculation completed")
            return complexity

        except Exception as e:
            logger.error(f"Complexity calculation failed: {e}")
            return {"error": str(e)}

    async def detect_duplicates(
        self,
        code: str,
        threshold: int = 6,  # Minimum lines to consider as duplicate
    ) -> List[Dict[str, Any]]:
        """
        Detect duplicate code blocks.

        Args:
            code: Code to analyze
            threshold: Minimum lines to consider duplicate

        Returns:
            List of duplicate code blocks
        """
        logger.info(f"Detecting duplicate code (threshold: {threshold} lines)")

        system_prompt = """You are an expert at detecting code duplication.

Identify:
- Exact duplicates
- Similar code blocks (>80% similarity)
- Copy-paste patterns
- Refactoring opportunities

Suggest DRY refactoring approaches.
"""

        user_prompt = f"""Detect duplicate code:

```
{code}
```

Find code blocks that are duplicated or very similar.
Suggest refactoring to eliminate duplication.
"""

        try:
            response = await self._generate_response(user_prompt, system_prompt)

            # Parse duplicates from response
            duplicates = []
            if "duplicate" in response.lower():
                duplicates.append({
                    "description": "Potential duplicates found",
                    "details": response[:200],
                })

            logger.info(f"Detected {len(duplicates)} duplicate blocks")
            return duplicates

        except Exception as e:
            logger.error(f"Duplicate detection failed: {e}")
            return []

    async def suggest_refactoring(
        self,
        code: str,
        focus: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Suggest refactoring improvements.

        Args:
            code: Code to refactor
            focus: Specific focus area (complexity, duplication, naming, etc.)

        Returns:
            Refactoring suggestions
        """
        logger.info(f"Generating refactoring suggestions (focus: {focus or 'general'})")

        system_prompt = """You are an expert in code refactoring and clean code principles.

Suggest refactorings following:
- SOLID principles
- DRY (Don't Repeat Yourself)
- KISS (Keep It Simple, Stupid)
- YAGNI (You Aren't Gonna Need It)
- Clean Code principles

Provide before/after examples when possible.
"""

        focus_text = f"Focus on: {focus}" if focus else "General refactoring"

        user_prompt = f"""Suggest refactoring for this code:

{focus_text}

```
{code}
```

Provide:
1. Specific refactoring recommendations
2. Priority order
3. Expected benefits
4. Code examples where helpful
"""

        try:
            response = await self._generate_response(user_prompt, system_prompt)

            suggestions = {
                "summary": response[:200],
                "detailed_suggestions": response,
                "priority": "medium",
            }

            logger.info("Refactoring suggestions generated")
            return suggestions

        except Exception as e:
            logger.error(f"Refactoring suggestion failed: {e}")
            return {"error": str(e)}

    async def generate_quality_report(
        self,
        result: CodeQualityResult,
        format: str = "markdown",
    ) -> str:
        """
        Generate formatted quality report.

        Args:
            result: Quality analysis result
            format: Report format

        Returns:
            Formatted report
        """
        logger.info(f"Generating {format} quality report")

        if format == "markdown":
            report = f"""# Code Quality Report

## Overall Score: {result.overall_quality_score}/100 (Grade: {result.grade})

{result.summary}

## Quality Metrics

"""
            for metric in result.metrics:
                report += f"""
### {metric.name}: {metric.score}/100 ({metric.status})

{metric.details}

**Recommendations:**
"""
                for rec in metric.recommendations:
                    report += f"- {rec}\n"

            if result.code_smells:
                report += f"\n## Code Smells ({len(result.code_smells)} detected)\n\n"
                for smell in result.code_smells:
                    report += f"""
### [{smell.severity.upper()}] {smell.type}

**Location**: {smell.location}

**Description**: {smell.description}

**Refactoring**: {smell.refactoring_suggestion}

**Impact**: {smell.impact}

"""

            report += f"\n## Maintainability Index: {result.maintainability_index}/100\n\n"

            if result.technical_debt:
                report += "## Technical Debt\n\n"
                for key, value in result.technical_debt.items():
                    report += f"- **{key}**: {value}\n"

            report += "\n## Priority Recommendations\n\n"
            for i, rec in enumerate(result.recommendations, 1):
                report += f"{i}. {rec}\n"

            return report

        return f"Format {format} not yet implemented"
