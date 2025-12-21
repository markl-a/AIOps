"""Tests for BaseAgent class."""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from aiops.agents.base_agent import BaseAgent
from aiops.core.llm_factory import LLMFactory


# Create a concrete implementation for testing
class TestableAgent(BaseAgent):
    """Concrete implementation for testing."""

    async def execute(self, *args, **kwargs):
        """Execute method for testing."""
        prompt = kwargs.get('prompt', 'test prompt')
        system_prompt = kwargs.get('system_prompt', None)
        return await self._generate_response(prompt, system_prompt)


class TestableStructuredAgent(BaseAgent):
    """Concrete implementation for testing structured responses."""

    async def execute(self, schema: dict, *args, **kwargs):
        """Execute method for testing structured responses."""
        prompt = kwargs.get('prompt', 'test prompt')
        system_prompt = kwargs.get('system_prompt', None)
        return await self._generate_structured_response(prompt, schema, system_prompt)


class TestBaseAgent:
    """Test suite for BaseAgent."""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM."""
        llm = MagicMock()
        llm.generate = AsyncMock(return_value="mock response")
        llm.generate_structured = AsyncMock(return_value={"status": "success", "data": "test"})
        return llm

    @pytest.fixture
    def agent(self, mock_llm, test_config):
        """Create a testable agent instance."""
        with patch.object(LLMFactory, 'create', return_value=mock_llm):
            return TestableAgent(name="TestAgent")

    @pytest.fixture
    def structured_agent(self, mock_llm, test_config):
        """Create a testable structured agent instance."""
        with patch.object(LLMFactory, 'create', return_value=mock_llm):
            return TestableStructuredAgent(name="StructuredAgent")

    # Test 1: Agent initialization
    @pytest.mark.asyncio
    async def test_agent_initialization_default(self, mock_llm, test_config):
        """Test agent initializes correctly with default parameters."""
        with patch.object(LLMFactory, 'create', return_value=mock_llm) as mock_create:
            agent = TestableAgent(name="TestAgent")

            assert agent.name == "TestAgent"
            assert agent.llm == mock_llm
            mock_create.assert_called_once_with(
                provider=None,
                model=None,
                temperature=None
            )

    @pytest.mark.asyncio
    async def test_agent_initialization_custom_params(self, mock_llm, test_config):
        """Test agent initializes with custom LLM parameters."""
        with patch.object(LLMFactory, 'create', return_value=mock_llm) as mock_create:
            agent = TestableAgent(
                name="CustomAgent",
                llm_provider="openai",
                model="gpt-4",
                temperature=0.7
            )

            assert agent.name == "CustomAgent"
            assert agent.llm == mock_llm
            mock_create.assert_called_once_with(
                provider="openai",
                model="gpt-4",
                temperature=0.7
            )

    # Test 2: Successful response generation
    @pytest.mark.asyncio
    async def test_generate_response_success(self, agent, mock_llm):
        """Test successful response generation."""
        result = await agent.execute(prompt="test prompt")

        assert result == "mock response"
        mock_llm.generate.assert_called_once_with("test prompt", None)

    @pytest.mark.asyncio
    async def test_generate_response_with_custom_prompt(self, agent, mock_llm):
        """Test response generation with custom prompt."""
        custom_prompt = "What is the meaning of life?"
        result = await agent.execute(prompt=custom_prompt)

        assert result == "mock response"
        mock_llm.generate.assert_called_once_with(custom_prompt, None)

    # Test 3: Response generation with system prompt
    @pytest.mark.asyncio
    async def test_generate_response_with_system_prompt(self, agent, mock_llm):
        """Test response generation with system prompt."""
        system_prompt = "You are a helpful assistant"
        user_prompt = "Help me debug this code"

        result = await agent.execute(prompt=user_prompt, system_prompt=system_prompt)

        assert result == "mock response"
        mock_llm.generate.assert_called_once_with(user_prompt, system_prompt)

    @pytest.mark.asyncio
    async def test_generate_response_with_long_prompts(self, agent, mock_llm):
        """Test response generation with long prompts."""
        long_prompt = "A" * 10000
        long_system_prompt = "B" * 5000

        result = await agent.execute(prompt=long_prompt, system_prompt=long_system_prompt)

        assert result == "mock response"
        mock_llm.generate.assert_called_once_with(long_prompt, long_system_prompt)

    # Test 4: Error handling
    @pytest.mark.asyncio
    async def test_error_handling_llm_exception(self, agent, mock_llm):
        """Test error handling when LLM raises exception."""
        mock_llm.generate.side_effect = Exception("LLM error")

        with pytest.raises(Exception) as exc_info:
            await agent.execute(prompt="test")

        assert "LLM error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_handling_connection_error(self, agent, mock_llm):
        """Test error handling for connection errors."""
        mock_llm.generate.side_effect = ConnectionError("Failed to connect to API")

        with pytest.raises(ConnectionError) as exc_info:
            await agent.execute(prompt="test")

        assert "Failed to connect to API" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_handling_value_error(self, agent, mock_llm):
        """Test error handling for invalid input."""
        mock_llm.generate.side_effect = ValueError("Invalid input format")

        with pytest.raises(ValueError) as exc_info:
            await agent.execute(prompt="test")

        assert "Invalid input format" in str(exc_info.value)

    # Test 5: Timeout handling
    @pytest.mark.asyncio
    async def test_timeout_handling(self, agent, mock_llm):
        """Test timeout handling."""
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(10)
            return "slow response"

        mock_llm.generate = AsyncMock(side_effect=slow_response)

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(agent.execute(prompt="test"), timeout=0.1)

    @pytest.mark.asyncio
    async def test_timeout_handling_with_cancellation(self, agent, mock_llm):
        """Test that timeouts properly cancel the task."""
        async def slow_response(*args, **kwargs):
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                raise
            return "slow response"

        mock_llm.generate = AsyncMock(side_effect=slow_response)

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(agent.execute(prompt="test"), timeout=0.1)

    # Test 6: Structured response generation
    @pytest.mark.asyncio
    async def test_generate_structured_response_success(self, structured_agent, mock_llm):
        """Test successful structured response generation."""
        schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "data": {"type": "string"}
            }
        }

        result = await structured_agent.execute(schema=schema, prompt="test prompt")

        assert result == {"status": "success", "data": "test"}
        mock_llm.generate_structured.assert_called_once_with("test prompt", schema, None)

    @pytest.mark.asyncio
    async def test_generate_structured_response_with_system_prompt(self, structured_agent, mock_llm):
        """Test structured response generation with system prompt."""
        schema = {"type": "object"}
        system_prompt = "You are a data validator"

        result = await structured_agent.execute(
            schema=schema,
            prompt="validate this",
            system_prompt=system_prompt
        )

        assert result == {"status": "success", "data": "test"}
        mock_llm.generate_structured.assert_called_once_with(
            "validate this",
            schema,
            system_prompt
        )

    @pytest.mark.asyncio
    async def test_generate_structured_response_complex_schema(self, structured_agent, mock_llm):
        """Test structured response with complex schema."""
        complex_schema = {
            "type": "object",
            "properties": {
                "analysis": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                        "issues": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    }
                }
            },
            "required": ["analysis"]
        }

        mock_llm.generate_structured.return_value = {
            "analysis": {
                "severity": "high",
                "issues": ["issue1", "issue2"]
            }
        }

        result = await structured_agent.execute(schema=complex_schema, prompt="analyze")

        assert result["analysis"]["severity"] == "high"
        assert len(result["analysis"]["issues"]) == 2

    @pytest.mark.asyncio
    async def test_structured_response_error_handling(self, structured_agent, mock_llm):
        """Test error handling in structured response generation."""
        schema = {"type": "object"}
        mock_llm.generate_structured.side_effect = Exception("Schema validation failed")

        with pytest.raises(Exception) as exc_info:
            await structured_agent.execute(schema=schema, prompt="test")

        assert "Schema validation failed" in str(exc_info.value)

    # Test 7: Abstract method enforcement
    def test_abstract_execute_method_enforcement(self):
        """Test that BaseAgent cannot be instantiated without implementing execute."""
        with pytest.raises(TypeError) as exc_info:
            BaseAgent(name="AbstractAgent")

        assert "abstract" in str(exc_info.value).lower() or "execute" in str(exc_info.value).lower()

    # Test 8: Multiple concurrent executions
    @pytest.mark.asyncio
    async def test_concurrent_executions(self, agent, mock_llm):
        """Test multiple concurrent agent executions."""
        # Simulate async behavior
        call_count = 0

        async def counted_generate(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)  # Small delay to simulate real async
            return f"response {call_count}"

        mock_llm.generate = AsyncMock(side_effect=counted_generate)

        # Execute multiple concurrent requests
        results = await asyncio.gather(
            agent.execute(prompt="prompt 1"),
            agent.execute(prompt="prompt 2"),
            agent.execute(prompt="prompt 3"),
        )

        assert len(results) == 3
        assert call_count == 3
        # All responses should be unique due to counter
        assert len(set(results)) == 3

    # Test 9: Empty and edge case inputs
    @pytest.mark.asyncio
    async def test_empty_prompt(self, agent, mock_llm):
        """Test handling of empty prompt."""
        result = await agent.execute(prompt="")

        assert result == "mock response"
        mock_llm.generate.assert_called_once_with("", None)

    @pytest.mark.asyncio
    async def test_empty_system_prompt(self, agent, mock_llm):
        """Test handling of empty system prompt."""
        result = await agent.execute(prompt="test", system_prompt="")

        assert result == "mock response"
        mock_llm.generate.assert_called_once_with("test", "")

    @pytest.mark.asyncio
    async def test_special_characters_in_prompts(self, agent, mock_llm):
        """Test handling of special characters in prompts."""
        special_prompt = "Test with 特殊字符 and émojis 🚀 and symbols !@#$%^&*()"
        result = await agent.execute(prompt=special_prompt)

        assert result == "mock response"
        mock_llm.generate.assert_called_once_with(special_prompt, None)

    @pytest.mark.asyncio
    async def test_multiline_prompts(self, agent, mock_llm):
        """Test handling of multiline prompts."""
        multiline_prompt = """
        Line 1
        Line 2
        Line 3
        """
        result = await agent.execute(prompt=multiline_prompt)

        assert result == "mock response"
        mock_llm.generate.assert_called_once_with(multiline_prompt, None)

    # Test 10: Response variations
    @pytest.mark.asyncio
    async def test_different_response_types(self, agent, mock_llm):
        """Test handling of different response types."""
        # Test with different mock responses
        test_responses = [
            "Short",
            "A" * 10000,  # Very long response
            "",  # Empty response
            "Multi\nline\nresponse",
            "Unicode: 你好世界 🌍"
        ]

        for response in test_responses:
            mock_llm.generate.return_value = response
            result = await agent.execute(prompt="test")
            assert result == response

    # Test 11: Agent state consistency
    @pytest.mark.asyncio
    async def test_agent_state_consistency(self, agent, mock_llm):
        """Test that agent maintains consistent state across calls."""
        initial_name = agent.name
        initial_llm = agent.llm

        # Make multiple calls
        await agent.execute(prompt="call 1")
        await agent.execute(prompt="call 2")
        await agent.execute(prompt="call 3")

        # Verify state hasn't changed
        assert agent.name == initial_name
        assert agent.llm == initial_llm

    # Test 12: LLM Factory integration
    @pytest.mark.asyncio
    async def test_llm_factory_called_correctly(self, mock_llm, test_config):
        """Test that LLM Factory is called with correct parameters."""
        with patch.object(LLMFactory, 'create', return_value=mock_llm) as mock_create:
            agent = TestableAgent(
                name="FactoryTest",
                llm_provider="anthropic",
                model="claude-3-opus",
                temperature=0.5
            )

            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs['provider'] == "anthropic"
            assert call_kwargs['model'] == "claude-3-opus"
            assert call_kwargs['temperature'] == 0.5

    # Test 13: Retry behavior on transient errors
    @pytest.mark.asyncio
    async def test_no_automatic_retry_on_error(self, agent, mock_llm):
        """Test that agent doesn't automatically retry on errors."""
        call_count = 0

        def counting_error(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise Exception("Error")

        mock_llm.generate.side_effect = counting_error

        with pytest.raises(Exception):
            await agent.execute(prompt="test")

        # Should only call once (no automatic retry)
        assert call_count == 1

    # Test 14: Response logging verification
    @pytest.mark.asyncio
    async def test_response_logging(self, agent, mock_llm):
        """Test that responses are logged correctly."""
        with patch('aiops.agents.base_agent.logger') as mock_logger:
            await agent.execute(prompt="test")

            # Verify debug log was called for response generation
            debug_calls = [call for call in mock_logger.debug.call_args_list
                          if 'Generated response' in str(call)]
            assert len(debug_calls) > 0

    @pytest.mark.asyncio
    async def test_error_logging(self, agent, mock_llm):
        """Test that errors are logged correctly."""
        mock_llm.generate.side_effect = Exception("Test error")

        with patch('aiops.agents.base_agent.logger') as mock_logger:
            with pytest.raises(Exception):
                await agent.execute(prompt="test")

            # Verify error log was called
            error_calls = [call for call in mock_logger.error.call_args_list
                          if 'Failed to generate response' in str(call)]
            assert len(error_calls) > 0

    # Test 15: Performance and response time
    @pytest.mark.asyncio
    async def test_fast_response_time(self, agent, mock_llm):
        """Test that agent responds quickly with fast LLM."""
        import time

        start_time = time.time()
        await agent.execute(prompt="test")
        end_time = time.time()

        # Should complete quickly (less than 1 second for mocked LLM)
        assert (end_time - start_time) < 1.0

    # Test 16: Different agent instances
    @pytest.mark.asyncio
    async def test_multiple_agent_instances(self, mock_llm, test_config):
        """Test creating multiple agent instances."""
        with patch.object(LLMFactory, 'create', return_value=mock_llm):
            agent1 = TestableAgent(name="Agent1")
            agent2 = TestableAgent(name="Agent2")
            agent3 = TestableAgent(name="Agent3")

            assert agent1.name == "Agent1"
            assert agent2.name == "Agent2"
            assert agent3.name == "Agent3"

            # Each should be independent
            assert agent1 is not agent2
            assert agent2 is not agent3

    # Test 17: Structured response edge cases
    @pytest.mark.asyncio
    async def test_structured_response_empty_schema(self, structured_agent, mock_llm):
        """Test structured response with empty schema."""
        empty_schema = {}
        result = await structured_agent.execute(schema=empty_schema, prompt="test")

        assert result == {"status": "success", "data": "test"}
        mock_llm.generate_structured.assert_called_once_with("test", empty_schema, None)

    @pytest.mark.asyncio
    async def test_structured_response_returns_empty_object(self, structured_agent, mock_llm):
        """Test structured response when LLM returns empty object."""
        schema = {"type": "object"}
        mock_llm.generate_structured.return_value = {}

        result = await structured_agent.execute(schema=schema, prompt="test")
        assert result == {}
