"""
Database Query Analyzer Agent

This agent analyzes SQL queries for performance issues, suggests optimizations,
identifies missing indexes, and provides query rewrite recommendations.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from aiops.core.logger import get_logger
import re

logger = get_logger(__name__)


class IndexRecommendation(BaseModel):
    """Index recommendation for query optimization"""
    table_name: str = Field(description="Table name")
    columns: List[str] = Field(description="Columns to index")
    index_type: str = Field(description="Type of index (btree, hash, gin, etc.)")
    reason: str = Field(description="Why this index is recommended")
    estimated_impact: str = Field(description="Expected performance impact")
    ddl: str = Field(description="SQL DDL to create the index")


class QueryOptimization(BaseModel):
    """Query optimization suggestion"""
    issue_type: str = Field(description="Type of issue (N+1, missing index, full scan, etc.)")
    severity: str = Field(description="critical, high, medium, low")
    original_query: str = Field(description="Original SQL query")
    optimized_query: Optional[str] = Field(description="Optimized version of the query")
    explanation: str = Field(description="Detailed explanation of the issue")
    estimated_speedup: str = Field(description="Expected performance improvement")
    recommendations: List[str] = Field(description="Step-by-step recommendations")


class QueryAnalysisResult(BaseModel):
    """Complete query analysis result"""
    analyzed_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    database_type: str = Field(description="Database type (PostgreSQL, MySQL, etc.)")
    queries_analyzed: int = Field(description="Number of queries analyzed")
    optimizations: List[QueryOptimization] = Field(description="Query optimization suggestions")
    index_recommendations: List[IndexRecommendation] = Field(description="Index recommendations")
    overall_score: float = Field(description="Overall query quality score (0-100)")
    summary: str = Field(description="Executive summary")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Performance metrics")


class DatabaseQueryAnalyzer:
    """
    AI-powered database query analyzer and optimizer.

    Features:
    - SQL query performance analysis
    - Index recommendations
    - Query rewrite suggestions
    - N+1 query detection
    - Join optimization
    - Execution plan analysis
    """

    def __init__(self, llm_factory=None):
        """Initialize the Database Query Analyzer Agent"""
        self.llm_factory = llm_factory
        logger.info("Database Query Analyzer Agent initialized")

    async def analyze_query(
        self,
        query: str,
        database_type: str = "PostgreSQL",
        execution_plan: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None
    ) -> QueryAnalysisResult:
        """
        Analyze a SQL query and provide optimization recommendations.

        Args:
            query: SQL query string to analyze
            database_type: Type of database (PostgreSQL, MySQL, etc.)
            execution_plan: Optional EXPLAIN output
            schema: Optional database schema information

        Returns:
            QueryAnalysisResult with optimizations and recommendations
        """
        try:
            optimizations = []
            index_recommendations = []

            # Analyze query structure
            query_lower = query.lower()

            # Check for SELECT *
            if 'select *' in query_lower:
                optimizations.append(QueryOptimization(
                    issue_type="SELECT_STAR",
                    severity="medium",
                    original_query=query,
                    optimized_query=self._suggest_explicit_columns(query),
                    explanation="Using SELECT * retrieves all columns, including unnecessary ones. This increases I/O, network transfer, and memory usage.",
                    estimated_speedup="10-30% faster",
                    recommendations=[
                        "Specify only the columns you need",
                        "Reduces data transfer and memory usage",
                        "Improves query cache efficiency",
                        "Makes query intent clearer"
                    ]
                ))

            # Check for missing WHERE clause
            if 'select' in query_lower and 'where' not in query_lower and 'join' in query_lower:
                optimizations.append(QueryOptimization(
                    issue_type="MISSING_WHERE",
                    severity="high",
                    original_query=query,
                    optimized_query=None,
                    explanation="Query with JOIN but no WHERE clause may perform a full table scan, returning all rows.",
                    estimated_speedup="Could be 100x+ faster with proper filtering",
                    recommendations=[
                        "Add WHERE clause to filter results",
                        "Use indexed columns in WHERE clause",
                        "Consider if you really need all rows",
                        "Add LIMIT if appropriate"
                    ]
                ))

            # Check for N+1 query pattern (multiple similar queries)
            # This would typically be detected from query logs, but we can check structure
            if query_lower.count('select') > 1:
                optimizations.append(QueryOptimization(
                    issue_type="POSSIBLE_N_PLUS_1",
                    severity="critical",
                    original_query=query,
                    optimized_query="Use JOIN or IN clause instead of multiple queries",
                    explanation="Multiple SELECT queries detected. This may indicate N+1 query problem where you're making one query per result.",
                    estimated_speedup="10-100x faster",
                    recommendations=[
                        "Use JOIN to fetch related data in single query",
                        "Use IN clause with subquery",
                        "Consider using eager loading in ORM",
                        "Batch queries when possible"
                    ]
                ))

            # Check for NOT IN (inefficient)
            if 'not in' in query_lower:
                optimized = query.replace('NOT IN', 'NOT EXISTS')
                optimizations.append(QueryOptimization(
                    issue_type="NOT_IN_CLAUSE",
                    severity="medium",
                    original_query=query,
                    optimized_query=optimized,
                    explanation="NOT IN can be inefficient, especially with NULL values. NOT EXISTS often performs better.",
                    estimated_speedup="20-50% faster",
                    recommendations=[
                        "Replace NOT IN with NOT EXISTS",
                        "Use LEFT JOIN with NULL check as alternative",
                        "Ensure subquery columns are NOT NULL if using IN"
                    ]
                ))

            # Check for functions on indexed columns
            if self._has_function_on_column(query):
                optimizations.append(QueryOptimization(
                    issue_type="FUNCTION_ON_INDEXED_COLUMN",
                    severity="high",
                    original_query=query,
                    optimized_query=None,
                    explanation="Using functions on indexed columns (e.g., WHERE YEAR(date) = 2024) prevents index usage.",
                    estimated_speedup="10-1000x faster",
                    recommendations=[
                        "Rewrite to avoid functions on WHERE clause columns",
                        "Use range queries instead (e.g., date >= '2024-01-01' AND date < '2025-01-01')",
                        "Consider computed/generated columns with indexes",
                        "Use functional indexes if database supports them"
                    ]
                ))

            # Check for implicit type conversions
            if self._has_implicit_conversion(query):
                optimizations.append(QueryOptimization(
                    issue_type="IMPLICIT_TYPE_CONVERSION",
                    severity="medium",
                    original_query=query,
                    optimized_query=None,
                    explanation="Comparing different data types (e.g., string column = 123) forces type conversion and prevents index usage.",
                    estimated_speedup="5-50x faster",
                    recommendations=[
                        "Match data types in comparisons",
                        "Use proper quotes for strings",
                        "Cast explicitly if conversion needed",
                        "Check schema for mismatched types"
                    ]
                ))

            # Analyze JOINs
            join_issues = self._analyze_joins(query)
            optimizations.extend(join_issues)

            # Generate index recommendations
            if schema:
                index_recs = self._generate_index_recommendations(query, schema)
                index_recommendations.extend(index_recs)
            else:
                # Basic recommendations without schema
                index_recs = self._basic_index_recommendations(query)
                index_recommendations.extend(index_recs)

            # Analyze execution plan if provided
            if execution_plan:
                plan_issues = self._analyze_execution_plan(execution_plan)
                optimizations.extend(plan_issues)

            # Calculate overall score
            score = self._calculate_query_score(optimizations)

            # Generate summary
            summary = self._generate_summary(optimizations, index_recommendations, score)

            # Calculate metrics
            metrics = {
                "critical_issues": sum(1 for o in optimizations if o.severity == "critical"),
                "high_priority_issues": sum(1 for o in optimizations if o.severity == "high"),
                "total_index_recommendations": len(index_recommendations),
                "estimated_overall_speedup": self._estimate_overall_speedup(optimizations)
            }

            result = QueryAnalysisResult(
                database_type=database_type,
                queries_analyzed=1,
                optimizations=optimizations,
                index_recommendations=index_recommendations,
                overall_score=score,
                summary=summary,
                metrics=metrics
            )

            logger.info(f"Query analysis complete: score={score:.1f}, issues={len(optimizations)}")
            return result

        except Exception as e:
            logger.error(f"Error analyzing query: {str(e)}")
            raise

    def _suggest_explicit_columns(self, query: str) -> str:
        """Suggest explicit column selection"""
        return query.replace('SELECT *', 'SELECT id, name, email, created_at  -- Specify only needed columns')

    def _has_function_on_column(self, query: str) -> bool:
        """Check if query uses functions on columns in WHERE clause"""
        patterns = [
            r'where\s+\w+\(',  # WHERE FUNC(
            r'and\s+\w+\(',    # AND FUNC(
            r'or\s+\w+\('      # OR FUNC(
        ]
        query_lower = query.lower()
        return any(re.search(pattern, query_lower) for pattern in patterns)

    def _has_implicit_conversion(self, query: str) -> bool:
        """Check for potential implicit type conversions"""
        # Look for quoted numbers or unquoted strings (simplified heuristic)
        patterns = [
            r"=\s*'\d+'",  # = '123' (number as string)
            r"=\s*\d+\.\d+",  # Comparing int column to float
        ]
        return any(re.search(pattern, query) for pattern in patterns)

    def _analyze_joins(self, query: str) -> List[QueryOptimization]:
        """Analyze JOIN clauses"""
        issues = []
        query_lower = query.lower()

        # Check for Cartesian product (JOIN without ON)
        if 'join' in query_lower and 'on' not in query_lower:
            issues.append(QueryOptimization(
                issue_type="CARTESIAN_PRODUCT",
                severity="critical",
                original_query=query,
                optimized_query=None,
                explanation="JOIN without ON clause creates a Cartesian product, multiplying all rows from both tables.",
                estimated_speedup="Essential - query may timeout without fix",
                recommendations=[
                    "Add ON clause with join condition",
                    "Ensure join columns are indexed",
                    "Use appropriate join type (INNER, LEFT, etc.)"
                ]
            ))

        # Check for multiple JOINs (complexity warning)
        join_count = query_lower.count('join')
        if join_count >= 4:
            issues.append(QueryOptimization(
                issue_type="COMPLEX_JOINS",
                severity="medium",
                original_query=query,
                optimized_query=None,
                explanation=f"Query has {join_count} JOINs. Complex join queries can be slow and hard to optimize.",
                estimated_speedup="Varies",
                recommendations=[
                    "Consider breaking into multiple queries",
                    "Use materialized views for complex joins",
                    "Ensure all join columns are indexed",
                    "Review join order (smaller tables first)",
                    "Consider denormalization for frequent queries"
                ]
            ))

        return issues

    def _generate_index_recommendations(
        self,
        query: str,
        schema: Dict[str, Any]
    ) -> List[IndexRecommendation]:
        """Generate index recommendations based on schema"""
        recommendations = []

        # Parse WHERE clause columns
        where_columns = self._extract_where_columns(query)

        for table, columns in where_columns.items():
            for column in columns:
                recommendations.append(IndexRecommendation(
                    table_name=table,
                    columns=[column],
                    index_type="btree",
                    reason=f"Column '{column}' used in WHERE clause for filtering",
                    estimated_impact="High - significantly speeds up filtering",
                    ddl=f"CREATE INDEX idx_{table}_{column} ON {table}({column});"
                ))

        return recommendations

    def _basic_index_recommendations(self, query: str) -> List[IndexRecommendation]:
        """Generate basic index recommendations without schema"""
        recommendations = []
        query_lower = query.lower()

        # Extract table and column patterns (simplified)
        where_match = re.search(r'where\s+(\w+)\.(\w+)', query_lower)
        if where_match:
            table = where_match.group(1)
            column = where_match.group(2)

            recommendations.append(IndexRecommendation(
                table_name=table,
                columns=[column],
                index_type="btree",
                reason=f"Column '{column}' appears in WHERE clause",
                estimated_impact="High - can significantly improve query performance",
                ddl=f"CREATE INDEX idx_{table}_{column} ON {table}({column});"
            ))

        return recommendations

    def _extract_where_columns(self, query: str) -> Dict[str, List[str]]:
        """Extract columns used in WHERE clause"""
        result = {}
        # Simplified extraction - in production, use proper SQL parser
        where_pattern = r'where\s+(\w+)\.(\w+)'
        matches = re.finditer(where_pattern, query.lower())

        for match in matches:
            table = match.group(1)
            column = match.group(2)
            if table not in result:
                result[table] = []
            result[table].append(column)

        return result

    def _analyze_execution_plan(self, plan: str) -> List[QueryOptimization]:
        """Analyze EXPLAIN output"""
        issues = []
        plan_lower = plan.lower()

        # Check for sequential scans
        if 'seq scan' in plan_lower:
            issues.append(QueryOptimization(
                issue_type="SEQUENTIAL_SCAN",
                severity="high",
                original_query="",
                optimized_query=None,
                explanation="Execution plan shows sequential scan. Database is reading entire table instead of using an index.",
                estimated_speedup="10-1000x faster with proper index",
                recommendations=[
                    "Add index on columns used in WHERE clause",
                    "Ensure statistics are up to date (ANALYZE)",
                    "Check if index exists but not being used",
                    "Review query selectivity"
                ]
            ))

        # Check for nested loops on large tables
        if 'nested loop' in plan_lower:
            issues.append(QueryOptimization(
                issue_type="NESTED_LOOP",
                severity="medium",
                original_query="",
                optimized_query=None,
                explanation="Nested loop join detected. May be inefficient for large datasets.",
                estimated_speedup="2-10x faster with better join strategy",
                recommendations=[
                    "Ensure join columns are indexed",
                    "Consider hash join or merge join",
                    "Update table statistics",
                    "Review join order"
                ]
            ))

        return issues

    def _calculate_query_score(self, optimizations: List[QueryOptimization]) -> float:
        """Calculate overall query quality score"""
        if not optimizations:
            return 100.0

        score = 100.0
        severity_penalties = {
            "critical": 30,
            "high": 20,
            "medium": 10,
            "low": 5
        }

        for opt in optimizations:
            score -= severity_penalties.get(opt.severity, 5)

        return max(0.0, score)

    def _estimate_overall_speedup(self, optimizations: List[QueryOptimization]) -> str:
        """Estimate overall potential speedup"""
        if not optimizations:
            return "No optimization needed"

        critical = sum(1 for o in optimizations if o.severity == "critical")
        high = sum(1 for o in optimizations if o.severity == "high")

        if critical > 0:
            return "10-100x or more"
        elif high > 0:
            return "5-10x"
        else:
            return "2-5x"

    def _generate_summary(
        self,
        optimizations: List[QueryOptimization],
        index_recommendations: List[IndexRecommendation],
        score: float
    ) -> str:
        """Generate executive summary"""
        summary = f"Query Performance Score: {score:.1f}/100\n\n"

        if score >= 80:
            summary += "✓ Query is well-optimized with minimal issues.\n"
        elif score >= 60:
            summary += "⚠ Query has some optimization opportunities.\n"
        else:
            summary += "✗ Query has significant performance issues requiring attention.\n"

        if optimizations:
            summary += f"\nFound {len(optimizations)} optimization opportunities:\n"
            critical = sum(1 for o in optimizations if o.severity == "critical")
            high = sum(1 for o in optimizations if o.severity == "high")
            if critical:
                summary += f"  • {critical} critical issues\n"
            if high:
                summary += f"  • {high} high-priority issues\n"

        if index_recommendations:
            summary += f"\n{len(index_recommendations)} index recommendations to improve performance.\n"

        return summary
