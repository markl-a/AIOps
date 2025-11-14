"""Tests for REST API."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from aiops.api.main import create_app
from aiops.agents.code_reviewer import CodeReviewResult, CodeIssue


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "name" in response.json()
    assert "version" in response.json()


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_code_review_endpoint(client):
    """Test code review endpoint."""
    mock_result = CodeReviewResult(
        overall_score=85.0,
        summary="Good code quality",
        issues=[],
        strengths=["Well structured"],
        recommendations=["Add more comments"],
    )

    with patch("aiops.api.main.CodeReviewAgent") as mock_agent_class:
        mock_agent = AsyncMock()
        mock_agent.execute = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent

        response = client.post(
            "/api/v1/code/review",
            json={"code": "def hello(): pass", "language": "python"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["overall_score"] == 85.0
        assert "summary" in data


def test_code_review_validation(client):
    """Test code review input validation."""
    # Missing required field
    response = client.post("/api/v1/code/review", json={"language": "python"})

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_test_generation_endpoint(client):
    """Test test generation endpoint."""
    from aiops.agents.test_generator import TestSuite, TestCase

    mock_result = TestSuite(
        framework="pytest",
        test_cases=[
            TestCase(
                name="test_hello",
                description="Test hello function",
                test_code="def test_hello(): assert hello() is None",
                test_type="unit",
                priority="high",
            )
        ],
        coverage_notes="Basic coverage",
        edge_cases=["None input"],
    )

    with patch("aiops.api.main.TestGeneratorAgent") as mock_agent_class:
        mock_agent = AsyncMock()
        mock_agent.execute = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent

        response = client.post(
            "/api/v1/tests/generate",
            json={"code": "def hello(): pass", "language": "python"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["framework"] == "pytest"
        assert len(data["test_cases"]) == 1


@pytest.mark.asyncio
async def test_log_analysis_endpoint(client):
    """Test log analysis endpoint."""
    from aiops.agents.log_analyzer import LogAnalysisResult

    mock_result = LogAnalysisResult(
        summary="Errors detected",
        insights=[],
        root_causes=[],
        recommendations=["Fix database connection"],
        anomalies=[],
        trends={},
    )

    with patch("aiops.api.main.LogAnalyzerAgent") as mock_agent_class:
        mock_agent = AsyncMock()
        mock_agent.execute = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent

        response = client.post(
            "/api/v1/logs/analyze", json={"logs": "ERROR: Database connection failed"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "summary" in data


def test_cors_headers(client):
    """Test CORS headers are present."""
    response = client.options("/api/v1/code/review")

    # CORS headers should be present
    assert "access-control-allow-origin" in response.headers


def test_api_error_handling(client):
    """Test API error handling."""
    with patch("aiops.api.main.CodeReviewAgent") as mock_agent_class:
        mock_agent = AsyncMock()
        mock_agent.execute = AsyncMock(side_effect=Exception("Test error"))
        mock_agent_class.return_value = mock_agent

        response = client.post(
            "/api/v1/code/review",
            json={"code": "def test(): pass", "language": "python"},
        )

        assert response.status_code == 500
        assert "detail" in response.json()
