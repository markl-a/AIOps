"""Tests for Test Generator Agent."""

import pytest
from unittest.mock import AsyncMock, patch
from aiops.agents.test_generator import (
    TestGeneratorAgent,
    TestSuite,
    TestCase,
)


@pytest.fixture
def test_gen_agent():
    """Create test generator agent."""
    return TestGeneratorAgent()


@pytest.fixture
def sample_function_code():
    """Sample function to generate tests for."""
    return """
def calculate_discount(price: float, discount_percent: float) -> float:
    '''Calculate discounted price.

    Args:
        price: Original price
        discount_percent: Discount percentage (0-100)

    Returns:
        Discounted price
    '''
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("Discount must be between 0 and 100")
    if price < 0:
        raise ValueError("Price cannot be negative")

    return price * (1 - discount_percent / 100)
"""


@pytest.mark.asyncio
async def test_generate_unit_tests(test_gen_agent, sample_function_code):
    """Test unit test generation."""
    mock_result = TestSuite(
        test_cases=[
            TestCase(
                name="test_calculate_discount_normal",
                code='assert calculate_discount(100.0, 20.0) == 80.0',
                category="normal",
                description="Test normal discount calculation",
            ),
            TestCase(
                name="test_calculate_discount_zero",
                code='assert calculate_discount(100.0, 0.0) == 100.0',
                category="edge",
                description="Test zero discount",
            ),
            TestCase(
                name="test_calculate_discount_invalid_negative",
                code='with pytest.raises(ValueError): calculate_discount(100.0, -10.0)',
                category="error",
                description="Test negative discount raises error",
            ),
            TestCase(
                name="test_calculate_discount_invalid_over_100",
                code='with pytest.raises(ValueError): calculate_discount(100.0, 150.0)',
                category="error",
                description="Test discount over 100 raises error",
            ),
        ],
        framework="pytest",
        coverage_estimate=95.0,
        total_tests=4,
    )

    with patch.object(
        test_gen_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await test_gen_agent.execute(
            code=sample_function_code, language="python", test_type="unit"
        )

        assert isinstance(result, TestSuite)
        assert len(result.test_cases) == 4
        assert result.framework == "pytest"
        assert result.coverage_estimate == 95.0


@pytest.mark.asyncio
async def test_generate_integration_tests(test_gen_agent):
    """Test integration test generation."""
    api_code = """
@app.post("/users")
async def create_user(user: UserCreate, db: Session):
    db_user = User(**user.dict())
    db.add(db_user)
    db.commit()
    return db_user
"""

    mock_result = TestSuite(
        test_cases=[
            TestCase(
                name="test_create_user_success",
                code='response = client.post("/users", json={"name": "John"})',
                category="normal",
            ),
            TestCase(
                name="test_create_user_invalid_data",
                code='response = client.post("/users", json={})',
                category="error",
            ),
        ],
        framework="pytest",
        coverage_estimate=80.0,
        total_tests=2,
    )

    with patch.object(
        test_gen_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await test_gen_agent.execute(
            code=api_code, language="python", test_type="integration"
        )

        assert isinstance(result, TestSuite)
        assert result.test_type == "integration"


@pytest.mark.asyncio
async def test_generate_edge_cases(test_gen_agent, sample_function_code):
    """Test edge case generation."""
    mock_result = TestSuite(
        test_cases=[
            TestCase(
                name="test_zero_price",
                code='assert calculate_discount(0.0, 50.0) == 0.0',
                category="edge",
            ),
            TestCase(
                name="test_100_percent_discount",
                code='assert calculate_discount(100.0, 100.0) == 0.0',
                category="edge",
            ),
            TestCase(
                name="test_very_large_price",
                code='assert calculate_discount(1e10, 10.0) == 9e9',
                category="edge",
            ),
        ],
        framework="pytest",
        coverage_estimate=85.0,
        total_tests=3,
    )

    with patch.object(
        test_gen_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
    ):
        result = await test_gen_agent.execute(
            code=sample_function_code, focus="edge_cases"
        )

        edge_cases = [tc for tc in result.test_cases if tc.category == "edge"]
        assert len(edge_cases) >= 2


@pytest.mark.asyncio
async def test_different_frameworks(test_gen_agent, sample_function_code):
    """Test generation for different testing frameworks."""
    for framework in ["pytest", "unittest", "jest"]:
        mock_result = TestSuite(
            test_cases=[TestCase(name="test_example", code="pass", category="normal")],
            framework=framework,
            coverage_estimate=70.0,
            total_tests=1,
        )

        with patch.object(
            test_gen_agent, "_generate_structured_response", new=AsyncMock(return_value=mock_result)
        ):
            result = await test_gen_agent.execute(
                code=sample_function_code, framework=framework
            )

            assert result.framework == framework


@pytest.mark.asyncio
async def test_error_handling(test_gen_agent):
    """Test error handling."""
    with patch.object(
        test_gen_agent,
        "_generate_structured_response",
        side_effect=Exception("Generation failed"),
    ):
        result = await test_gen_agent.execute(code="invalid")

        assert isinstance(result, TestSuite)
        assert result.total_tests == 0


def test_coverage_estimate_validation(test_gen_agent):
    """Test coverage estimate is valid percentage."""
    test_suite = TestSuite(
        test_cases=[],
        framework="pytest",
        coverage_estimate=85.0,
        total_tests=0,
    )

    assert 0 <= test_suite.coverage_estimate <= 100
