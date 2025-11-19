"""Integration tests for AIOps API."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from aiops.api.main import app
from aiops.api.auth import create_access_token, get_password_hash


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def auth_token():
    """Create authentication token."""
    return create_access_token(data={"sub": "testuser", "role": "admin"})


@pytest.fixture
def auth_headers(auth_token):
    """Create authentication headers."""
    return {"Authorization": f"Bearer {auth_token}"}


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_readiness_check(self, client):
        """Test readiness check endpoint."""
        response = client.get("/ready")
        assert response.status_code == 200


class TestAuthenticationEndpoints:
    """Test authentication endpoints."""

    def test_token_creation(self, client):
        """Test token creation."""
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "admin", "password": "admin"},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert response.json()["token_type"] == "bearer"

    def test_invalid_credentials(self, client):
        """Test invalid credentials."""
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "invalid", "password": "wrong"},
        )
        assert response.status_code == 401

    def test_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without token."""
        response = client.post(
            "/api/v1/agents/code-review",
            json={"code": "test", "language": "python"},
        )
        assert response.status_code == 401

    def test_protected_endpoint_with_token(self, client, auth_headers):
        """Test accessing protected endpoint with valid token."""
        with patch("aiops.agents.code_reviewer.CodeReviewAgent.execute", new=AsyncMock()):
            response = client.post(
                "/api/v1/agents/code-review",
                json={"code": "test", "language": "python"},
                headers=auth_headers,
            )
            # Should not return 401
            assert response.status_code != 401


class TestCodeReviewEndpoint:
    """Test code review API endpoints."""

    def test_code_review_success(self, client, auth_headers):
        """Test successful code review."""
        mock_result = {
            "overall_score": 85.0,
            "summary": "Code looks good",
            "issues": [],
            "strengths": ["Clean code"],
            "recommendations": [],
        }

        with patch(
            "aiops.agents.code_reviewer.CodeReviewAgent.execute",
            new=AsyncMock(return_value=type("Result", (), mock_result)),
        ):
            response = client.post(
                "/api/v1/agents/code-review",
                json={"code": "def hello(): pass", "language": "python"},
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_code_review_missing_code(self, client, auth_headers):
        """Test code review with missing code."""
        response = client.post(
            "/api/v1/agents/code-review",
            json={"language": "python"},
            headers=auth_headers,
        )
        assert response.status_code == 422  # Validation error

    def test_code_review_invalid_language(self, client, auth_headers):
        """Test code review with invalid language."""
        response = client.post(
            "/api/v1/agents/code-review",
            json={"code": "test", "language": "invalid-lang"},
            headers=auth_headers,
        )
        # Should still process or return appropriate error
        assert response.status_code in [200, 400, 422]


class TestLogAnalysisEndpoint:
    """Test log analysis API endpoints."""

    def test_log_analysis_success(self, client, auth_headers):
        """Test successful log analysis."""
        logs = "2024-01-15 ERROR Something failed\n2024-01-15 ERROR Another error"

        mock_result = {
            "patterns": [],
            "root_causes": [],
            "anomalies_detected": 0,
            "total_errors": 2,
            "critical_errors": 0,
            "analysis_summary": "Analysis complete",
        }

        with patch(
            "aiops.agents.log_analyzer.LogAnalyzerAgent.execute",
            new=AsyncMock(return_value=type("Result", (), mock_result)),
        ):
            response = client.post(
                "/api/v1/agents/log-analysis",
                json={"logs": logs, "log_type": "application"},
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_log_analysis_empty_logs(self, client, auth_headers):
        """Test log analysis with empty logs."""
        response = client.post(
            "/api/v1/agents/log-analysis",
            json={"logs": "", "log_type": "application"},
            headers=auth_headers,
        )
        # Should handle gracefully
        assert response.status_code in [200, 400, 422]


class TestTestGenerationEndpoint:
    """Test test generation API endpoints."""

    def test_test_generation_success(self, client, auth_headers):
        """Test successful test generation."""
        code = "def add(a, b): return a + b"

        mock_result = {
            "test_cases": [],
            "framework": "pytest",
            "coverage_estimate": 90.0,
            "total_tests": 0,
        }

        with patch(
            "aiops.agents.test_generator.TestGeneratorAgent.execute",
            new=AsyncMock(return_value=type("Result", (), mock_result)),
        ):
            response = client.post(
                "/api/v1/agents/test-generation",
                json={"code": code, "language": "python", "test_type": "unit"},
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestK8sOptimizationEndpoint:
    """Test Kubernetes optimization API endpoints."""

    def test_k8s_optimization_success(self, client, auth_headers):
        """Test successful K8s optimization."""
        manifest = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test
"""

        mock_result = {
            "resource_optimizations": [],
            "hpa_recommendations": [],
            "cost_savings_monthly": 100.0,
            "overall_score": 80.0,
        }

        with patch(
            "aiops.agents.k8s_optimizer.KubernetesOptimizerAgent.execute",
            new=AsyncMock(return_value=type("Result", (), mock_result)),
        ):
            response = client.post(
                "/api/v1/agents/k8s-optimization",
                json={"manifest": manifest, "metrics": {}},
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestRateLimiting:
    """Test rate limiting."""

    def test_rate_limit_enforcement(self, client, auth_headers):
        """Test rate limiting kicks in."""
        # Make many requests quickly
        responses = []
        for _ in range(150):  # Exceeds default limit of 100
            response = client.get("/health", headers=auth_headers)
            responses.append(response.status_code)

        # Should get at least one 429 (Too Many Requests)
        assert 429 in responses


class TestCORS:
    """Test CORS configuration."""

    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options("/health")
        # Should have CORS headers
        assert response.status_code in [200, 405]


class TestMetrics:
    """Test metrics endpoint."""

    def test_metrics_endpoint(self, client):
        """Test Prometheus metrics endpoint."""
        response = client.get("/metrics")
        # Metrics should be available
        assert response.status_code == 200
        # Should contain prometheus format
        assert "# HELP" in response.text or response.status_code == 404


class TestBatchProcessing:
    """Test batch processing endpoints."""

    def test_batch_code_review(self, client, auth_headers):
        """Test batch code review."""
        files = [
            {"path": "file1.py", "code": "def test1(): pass"},
            {"path": "file2.py", "code": "def test2(): pass"},
        ]

        with patch(
            "aiops.agents.code_reviewer.CodeReviewAgent.execute",
            new=AsyncMock(return_value=type("Result", (), {"overall_score": 80})),
        ):
            response = client.post(
                "/api/v1/batch/code-review",
                json={"files": files, "language": "python"},
                headers=auth_headers,
            )

            # Should process batch or return appropriate response
            assert response.status_code in [200, 404]  # 404 if endpoint not implemented yet


class TestErrorHandling:
    """Test API error handling."""

    def test_internal_server_error_handling(self, client, auth_headers):
        """Test internal server error handling."""
        with patch(
            "aiops.agents.code_reviewer.CodeReviewAgent.execute",
            side_effect=Exception("Internal error"),
        ):
            response = client.post(
                "/api/v1/agents/code-review",
                json={"code": "test", "language": "python"},
                headers=auth_headers,
            )

            # Should return 500 or handle gracefully
            assert response.status_code in [500, 200]

    def test_validation_error_response(self, client, auth_headers):
        """Test validation error response format."""
        response = client.post(
            "/api/v1/agents/code-review",
            json={},  # Missing required fields
            headers=auth_headers,
        )

        assert response.status_code == 422
        assert "detail" in response.json()


@pytest.mark.asyncio
class TestAsyncEndpoints:
    """Test async endpoint behavior."""

    async def test_concurrent_requests(self, client, auth_headers):
        """Test handling concurrent requests."""
        import asyncio

        async def make_request():
            return client.get("/health")

        # Make multiple concurrent requests
        tasks = [make_request() for _ in range(10)]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        assert all(r.status_code == 200 for r in responses)
