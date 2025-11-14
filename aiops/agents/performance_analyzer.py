"""Performance Analyzer Agent - Analyze and optimize code performance."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from aiops.agents.base_agent import BaseAgent
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class PerformanceIssue(BaseModel):
    """Represents a performance issue."""

    severity: str = Field(description="Severity: critical, high, medium, low")
    category: str = Field(description="Category: algorithm, memory, io, database, network")
    location: str = Field(description="Where the issue occurs")
    description: str = Field(description="Issue description")
    impact: str = Field(description="Performance impact")
    optimization: str = Field(description="Recommended optimization")
    estimated_improvement: Optional[str] = Field(default=None, description="Estimated improvement")


class PerformanceAnalysisResult(BaseModel):
    """Performance analysis result."""

    overall_score: float = Field(description="Overall performance score (0-100)")
    summary: str = Field(description="Performance summary")
    issues: List[PerformanceIssue] = Field(description="Performance issues")
    bottlenecks: List[str] = Field(description="Identified bottlenecks")
    optimizations: List[str] = Field(description="Priority optimizations")
    metrics: Dict[str, Any] = Field(description="Performance metrics")


class PerformanceAnalyzerAgent(BaseAgent):
    """Agent for performance analysis and optimization."""

    def __init__(self, **kwargs):
        super().__init__(name="PerformanceAnalyzerAgent", **kwargs)

    async def execute(
        self,
        code: str,
        language: str = "python",
        profiling_data: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> PerformanceAnalysisResult:
        """
        Analyze code performance.

        Args:
            code: Code to analyze
            language: Programming language
            profiling_data: Profiling/benchmark data
            metrics: Performance metrics (latency, throughput, etc.)

        Returns:
            PerformanceAnalysisResult with optimization recommendations
        """
        logger.info(f"Analyzing performance for {language} code")

        system_prompt = self._create_system_prompt(language)
        user_prompt = self._create_user_prompt(code, profiling_data, metrics)

        try:
            result = await self._generate_structured_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                schema=PerformanceAnalysisResult,
            )

            logger.info(
                f"Performance analysis completed: score {result.overall_score}/100, "
                f"{len(result.issues)} issues found"
            )

            return result

        except Exception as e:
            logger.error(f"Performance analysis failed: {e}")
            return PerformanceAnalysisResult(
                overall_score=0,
                summary=f"Analysis failed: {str(e)}",
                issues=[],
                bottlenecks=[],
                optimizations=[],
                metrics={},
            )

    def _create_system_prompt(self, language: str) -> str:
        """Create system prompt for performance analysis."""
        return f"""You are an expert performance engineer specializing in {language}.

Analyze code for performance issues in these areas:

1. **Algorithmic Complexity**:
   - Time complexity (O(n), O(n²), etc.)
   - Space complexity
   - Better algorithm suggestions

2. **Memory Management**:
   - Memory leaks
   - Excessive allocations
   - Cache efficiency

3. **I/O Operations**:
   - Blocking I/O
   - Unnecessary reads/writes
   - Buffering issues

4. **Database Performance**:
   - N+1 queries
   - Missing indexes
   - Inefficient queries

5. **Concurrency**:
   - Parallelization opportunities
   - Lock contention
   - Race conditions

6. **Resource Usage**:
   - CPU utilization
   - Network calls
   - File operations

Provide:
- Specific performance issues with locations
- Quantified impact when possible
- Concrete optimization recommendations
- Estimated improvement for each fix

Focus on high-impact optimizations.
"""

    def _create_user_prompt(
        self,
        code: str,
        profiling_data: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create user prompt for performance analysis."""
        prompt = "Analyze the performance of this code:\n\n"

        prompt += f"```\n{code}\n```\n\n"

        if profiling_data:
            prompt += "**Profiling Data**:\n"
            for key, value in profiling_data.items():
                prompt += f"- {key}: {value}\n"
            prompt += "\n"

        if metrics:
            prompt += "**Performance Metrics**:\n"
            for key, value in metrics.items():
                prompt += f"- {key}: {value}\n"
            prompt += "\n"

        prompt += """Identify:
1. Performance bottlenecks
2. Algorithmic inefficiencies
3. Memory issues
4. I/O optimization opportunities
5. Specific optimization recommendations with estimated impact
"""

        return prompt

    async def analyze_database_queries(
        self,
        queries: List[str],
        schema: Optional[str] = None,
        execution_stats: Optional[Dict[str, Any]] = None,
    ) -> PerformanceAnalysisResult:
        """
        Analyze database query performance.

        Args:
            queries: SQL queries to analyze
            schema: Database schema
            execution_stats: Query execution statistics

        Returns:
            Performance analysis with optimization recommendations
        """
        logger.info(f"Analyzing {len(queries)} database queries")

        system_prompt = """You are a database performance expert.

Analyze queries for:
1. N+1 query problems
2. Missing indexes
3. Inefficient JOINs
4. Full table scans
5. Subquery optimization
6. Query plan issues

Provide specific index suggestions and query rewrites.
"""

        user_prompt = "Analyze these database queries:\n\n"

        if schema:
            user_prompt += f"**Database Schema**:\n```sql\n{schema}\n```\n\n"

        user_prompt += "**Queries**:\n"
        for i, query in enumerate(queries, 1):
            user_prompt += f"\nQuery {i}:\n```sql\n{query}\n```\n"

        if execution_stats:
            user_prompt += f"\n**Execution Stats**: {execution_stats}\n"

        user_prompt += "\nProvide optimization recommendations for each query."

        try:
            result = await self._generate_structured_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                schema=PerformanceAnalysisResult,
            )

            logger.info(f"Database analysis completed: {len(result.issues)} issues")
            return result

        except Exception as e:
            logger.error(f"Database analysis failed: {e}")
            return PerformanceAnalysisResult(
                overall_score=0,
                summary=f"Analysis failed: {str(e)}",
                issues=[],
                bottlenecks=[],
                optimizations=[],
                metrics={},
            )

    async def suggest_caching_strategy(
        self,
        code: str,
        access_patterns: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Suggest caching strategies for code.

        Args:
            code: Code to analyze
            access_patterns: Data access patterns

        Returns:
            Caching strategy recommendations
        """
        logger.info("Analyzing caching opportunities")

        system_prompt = """You are a caching and performance optimization expert.

Suggest caching strategies:
1. What to cache (data, computations, API responses)
2. Where to cache (memory, Redis, CDN)
3. Cache invalidation strategies
4. TTL recommendations
5. Trade-offs (memory vs latency)

Consider:
- Access frequency
- Data volatility
- Consistency requirements
- Memory constraints
"""

        user_prompt = f"""Suggest caching strategies for this code:

```
{code}
```
"""

        if access_patterns:
            user_prompt += f"\n**Access Patterns**: {access_patterns}\n"

        user_prompt += "\nProvide specific caching recommendations with implementation guidance."

        try:
            response = await self._generate_response(user_prompt, system_prompt)

            return {
                "recommendations": response,
                "cache_locations": ["memory", "redis", "cdn"],  # Can be parsed from response
            }

        except Exception as e:
            logger.error(f"Caching analysis failed: {e}")
            return {"recommendations": f"Analysis failed: {str(e)}", "cache_locations": []}

    async def optimize_code(
        self,
        code: str,
        language: str = "python",
        optimization_goal: str = "speed",
    ) -> str:
        """
        Generate optimized version of code.

        Args:
            code: Code to optimize
            language: Programming language
            optimization_goal: Goal (speed, memory, readability)

        Returns:
            Optimized code
        """
        logger.info(f"Optimizing code for {optimization_goal}")

        system_prompt = f"""You are an expert at optimizing {language} code.

Optimize for: {optimization_goal}

Apply optimizations:
- Better algorithms and data structures
- Reduce time/space complexity
- Eliminate unnecessary operations
- Use language-specific optimizations
- Maintain code correctness and readability

Provide the optimized code with comments explaining changes.
"""

        user_prompt = f"""Optimize this code for {optimization_goal}:

```{language}
{code}
```

Return the optimized version with explanation of changes.
"""

        try:
            response = await self._generate_response(user_prompt, system_prompt)

            # Extract code from markdown if present
            if "```" in response:
                code_blocks = response.split("```")
                for i, block in enumerate(code_blocks):
                    if i > 0 and (block.strip().startswith(language) or i == 1):
                        optimized = code_blocks[i + 1].strip() if i + 1 < len(code_blocks) else block.strip()
                        logger.info("Code optimization completed")
                        return optimized

            return response

        except Exception as e:
            logger.error(f"Code optimization failed: {e}")
            return code  # Return original code on failure
