"""Tests for Database Query Analyzer Agent."""

import pytest
from unittest.mock import AsyncMock, patch
from aiops.agents.db_query_analyzer import (
    DatabaseQueryAnalyzer,
    QueryAnalysisResult,
    QueryIssue,
    IndexRecommendation,
)


@pytest.fixture
def db_agent():
    """Create database query analyzer agent."""
    return DatabaseQueryAnalyzer()


@pytest.fixture
def sample_sql_query():
    """Sample SQL query."""
    return """
    SELECT u.id, u.name, p.title, c.content
    FROM users u
    LEFT JOIN posts p ON u.id = p.user_id
    LEFT JOIN comments c ON p.id = c.post_id
    WHERE u.created_at > '2024-01-01'
    ORDER BY p.created_at DESC
    """


@pytest.fixture
def sample_query_plan():
    """Sample query execution plan."""
    return {
        "query_time_ms": 1250.5,
        "rows_examined": 50000,
        "rows_returned": 100,
        "using_index": False,
        "using_filesort": True,
    }


@pytest.mark.asyncio
async def test_analyze_query(db_agent, sample_sql_query, sample_query_plan):
    """Test SQL query analysis."""
    mock_result = QueryAnalysisResult(
        query=sample_sql_query,
        issues=[
            QueryIssue(
                severity="high",
                category="performance",
                description="Query performs filesort operation",
                impact="High latency on large datasets",
                suggestion="Add index on posts.created_at",
            ),
            QueryIssue(
                severity="medium",
                category="optimization",
                description="Large number of rows examined vs returned",
                impact="Inefficient query execution",
                suggestion="Add WHERE clause filtering earlier in query",
            ),
        ],
        index_recommendations=[
            IndexRecommendation(
                table="posts",
                columns=["created_at", "user_id"],
                index_type="BTREE",
                estimated_improvement_percent=75.0,
                justification="Will eliminate filesort and improve join performance",
            ),
            IndexRecommendation(
                table="users",
                columns=["created_at"],
                index_type="BTREE",
                estimated_improvement_percent=30.0,
                justification="Speed up WHERE clause filtering",
            ),
        ],
        estimated_time_saved_ms=937.87,
        optimization_score=65.0,
    )

    with patch.object(
        db_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await db_agent.execute(
            query=sample_sql_query, query_plan=sample_query_plan, database_type="mysql"
        )

        assert isinstance(result, QueryAnalysisResult)
        assert len(result.issues) == 2
        assert len(result.index_recommendations) == 2
        assert result.optimization_score == 65.0


@pytest.mark.asyncio
async def test_detect_n_plus_one(db_agent):
    """Test N+1 query detection."""
    queries = [
        "SELECT * FROM users",
        "SELECT * FROM posts WHERE user_id = 1",
        "SELECT * FROM posts WHERE user_id = 2",
        "SELECT * FROM posts WHERE user_id = 3",
    ]

    mock_result = QueryAnalysisResult(
        query="\n".join(queries),
        issues=[
            QueryIssue(
                severity="critical",
                category="n+1",
                description="N+1 query pattern detected",
                impact="Multiple round trips to database",
                suggestion="Use JOIN or eager loading",
            )
        ],
        index_recommendations=[],
        estimated_time_saved_ms=500.0,
        optimization_score=40.0,
    )

    with patch.object(
        db_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await db_agent.analyze_query_log(queries=queries)

        assert isinstance(result, QueryAnalysisResult)
        assert any(issue.category == "n+1" for issue in result.issues)


@pytest.mark.asyncio
async def test_postgresql_specific(db_agent):
    """Test PostgreSQL-specific analysis."""
    query = "SELECT * FROM users WHERE data->>'name' = 'John'"

    mock_result = QueryAnalysisResult(
        query=query,
        issues=[
            QueryIssue(
                severity="medium",
                category="index",
                description="JSONB field query without GIN index",
                suggestion="Create GIN index on data column",
            )
        ],
        index_recommendations=[
            IndexRecommendation(
                table="users",
                columns=["data"],
                index_type="GIN",
                estimated_improvement_percent=80.0,
            )
        ],
        estimated_time_saved_ms=0,
        optimization_score=70.0,
    )

    with patch.object(
        db_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await db_agent.execute(query=query, database_type="postgresql")

        assert isinstance(result, QueryAnalysisResult)
        assert any(rec.index_type == "GIN" for rec in result.index_recommendations)


@pytest.mark.asyncio
async def test_error_handling(db_agent):
    """Test error handling."""
    with patch.object(
        db_agent,
        "_generate_structured_response",
        side_effect=Exception("Analysis failed"),
    ):
        result = await db_agent.execute(query="INVALID SQL", database_type="mysql")

        assert isinstance(result, QueryAnalysisResult)
        assert result.optimization_score == 0


@pytest.mark.asyncio
async def test_index_recommendation_validation(db_agent, sample_sql_query):
    """Test index recommendation validation."""
    mock_result = QueryAnalysisResult(
        query=sample_sql_query,
        issues=[],
        index_recommendations=[
            IndexRecommendation(
                table="posts",
                columns=["created_at"],
                index_type="BTREE",
                estimated_improvement_percent=50.0,
            )
        ],
        estimated_time_saved_ms=0,
        optimization_score=80.0,
    )

    with patch.object(
        db_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await db_agent.execute(query=sample_sql_query)

        assert all(rec.estimated_improvement_percent <= 100 for rec in result.index_recommendations)
        assert all(rec.estimated_improvement_percent >= 0 for rec in result.index_recommendations)
