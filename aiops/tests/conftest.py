"""Pytest configuration and fixtures."""

import pytest
import os
from unittest.mock import AsyncMock, MagicMock
from aiops.core.config import Config, set_config
from aiops.core.llm_factory import LLMFactory


@pytest.fixture(scope="session")
def test_config():
    """Create test configuration."""
    config = Config(
        openai_api_key="test_key",
        default_llm_provider="openai",
        default_model="gpt-4-turbo-preview",
        log_level="ERROR",
        enable_metrics=False,
    )
    set_config(config)
    return config


@pytest.fixture
def mock_llm():
    """Create mock LLM for testing."""
    llm = AsyncMock()
    llm.generate = AsyncMock(return_value="Mock response")
    llm.generate_structured = AsyncMock(return_value={"mock": "data"})
    return llm


@pytest.fixture
def sample_code():
    """Sample code for testing."""
    return """
def calculate_sum(numbers):
    total = 0
    for i in range(len(numbers)):
        total = total + numbers[i]
    return total
"""


@pytest.fixture
def sample_logs():
    """Sample logs for testing."""
    return """
2024-01-10 10:15:23 ERROR Failed to connect to database
2024-01-10 10:15:24 WARN Retrying connection
2024-01-10 10:15:29 ERROR Failed to connect to database
2024-01-10 10:15:41 CRITICAL Database connection failed
"""


@pytest.fixture
def sample_pipeline_config():
    """Sample CI/CD pipeline config."""
    return """
name: CI Pipeline
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - run: npm install
      - run: npm test
"""


@pytest.fixture
def sample_metrics():
    """Sample metrics for testing."""
    return {
        "cpu_usage": 85.2,
        "memory_usage": 92.1,
        "error_rate": 5.2,
        "response_time_ms": 1200,
    }


@pytest.fixture
def baseline_metrics():
    """Baseline metrics for testing."""
    return {
        "cpu_usage": 45.0,
        "memory_usage": 60.0,
        "error_rate": 0.5,
        "response_time_ms": 200,
    }


@pytest.fixture(autouse=True)
def cleanup():
    """Cleanup after each test."""
    yield
    # Clear LLM cache
    LLMFactory.clear_cache()


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    return MagicMock(
        content="This is a mock response from OpenAI",
        usage=MagicMock(total_tokens=100),
    )


@pytest.fixture
def mock_anthropic_response():
    """Mock Anthropic API response."""
    return MagicMock(
        content="This is a mock response from Anthropic",
        usage=MagicMock(input_tokens=50, output_tokens=50),
    )
