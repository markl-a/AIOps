"""Comprehensive tests for Agent Orchestrator."""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from aiops.agents.orchestrator import (
    AgentOrchestrator,
    AgentTask,
    TaskResult,
    WorkflowResult,
    ExecutionMode,
    ExecutionStatus,
)
from aiops.agents.base_agent import (
    AgentExecutionError,
    AgentTimeoutError,
    AgentValidationError,
)


class MockAgent:
    """Mock agent for testing."""

    def __init__(self, name: str, result: any = None, should_fail: bool = False, delay: float = 0):
        self.name = name
        self.result = result or {"status": "success", "data": f"Result from {name}"}
        self.should_fail = should_fail
        self.delay = delay
        self.call_count = 0

    async def execute(self, **kwargs):
        """Mock execute method."""
        self.call_count += 1
        if self.delay:
            await asyncio.sleep(self.delay)

        if self.should_fail:
            raise AgentExecutionError(self.name, "Mock agent failed")

        return self.result

    async def execute_with_retry(self, max_attempts: int = 3, **kwargs):
        """Mock execute with retry."""
        return await self.execute(**kwargs)


@pytest.fixture
def orchestrator():
    """Create orchestrator instance."""
    return AgentOrchestrator()


@pytest.fixture
def mock_registry():
    """Mock agent registry."""
    agents = {}

    async def get_agent(name: str):
        if name not in agents:
            raise ValueError(f"Agent '{name}' not registered")
        return agents[name]

    def register_agent(name: str, agent: MockAgent):
        agents[name] = agent

    def is_registered(name: str):
        return name in agents

    registry_mock = Mock()
    registry_mock.get = AsyncMock(side_effect=get_agent)
    registry_mock.is_registered = Mock(side_effect=is_registered)
    registry_mock._register = register_agent

    return registry_mock


class TestSequentialExecution:
    """Tests for sequential task execution."""

    @pytest.mark.asyncio
    async def test_sequential_execution_success(self, orchestrator, mock_registry):
        """Test successful sequential execution."""
        # Register agents
        agent1 = MockAgent("agent1", {"value": 1})
        agent2 = MockAgent("agent2", {"value": 2})
        mock_registry._register("agent1", agent1)
        mock_registry._register("agent2", agent2)

        with patch("aiops.agents.orchestrator.agent_registry", mock_registry):
            tasks = [
                AgentTask(agent_name="agent1", input_data={"input": "test1"}),
                AgentTask(agent_name="agent2", input_data={"input": "test2"}),
            ]

            result = await orchestrator.execute_sequential(tasks, workflow_id="test_seq")

            assert isinstance(result, WorkflowResult)
            assert result.workflow_id == "test_seq"
            assert result.status == ExecutionStatus.COMPLETED
            assert len(result.tasks) == 2
            assert all(t.status == ExecutionStatus.COMPLETED for t in result.tasks)
            assert result.summary["completed"] == 2
            assert result.summary["failed"] == 0

    @pytest.mark.asyncio
    async def test_sequential_execution_with_failure(self, orchestrator, mock_registry):
        """Test sequential execution with failure and stop_on_error."""
        agent1 = MockAgent("agent1", should_fail=True)
        agent2 = MockAgent("agent2")
        mock_registry._register("agent1", agent1)
        mock_registry._register("agent2", agent2)

        with patch("aiops.agents.orchestrator.agent_registry", mock_registry):
            tasks = [
                AgentTask(agent_name="agent1", input_data={}),
                AgentTask(agent_name="agent2", input_data={}),
            ]

            result = await orchestrator.execute_sequential(tasks, stop_on_error=True)

            assert result.status == ExecutionStatus.FAILED
            assert len(result.tasks) == 1  # Should stop after first failure
            assert result.tasks[0].status == ExecutionStatus.FAILED
            assert result.summary["failed"] == 1

    @pytest.mark.asyncio
    async def test_sequential_execution_continue_on_error(self, orchestrator, mock_registry):
        """Test sequential execution continues when stop_on_error=False."""
        agent1 = MockAgent("agent1", should_fail=True)
        agent2 = MockAgent("agent2")
        mock_registry._register("agent1", agent1)
        mock_registry._register("agent2", agent2)

        with patch("aiops.agents.orchestrator.agent_registry", mock_registry):
            tasks = [
                AgentTask(agent_name="agent1", input_data={}),
                AgentTask(agent_name="agent2", input_data={}),
            ]

            result = await orchestrator.execute_sequential(tasks, stop_on_error=False)

            assert len(result.tasks) == 2
            assert result.tasks[0].status == ExecutionStatus.FAILED
            assert result.tasks[1].status == ExecutionStatus.COMPLETED
            assert result.summary["failed"] == 1
            assert result.summary["completed"] == 1

    @pytest.mark.asyncio
    async def test_sequential_with_conditional_execution(self, orchestrator, mock_registry):
        """Test sequential execution with conditional tasks."""
        agent1 = MockAgent("agent1", {"condition_met": True})
        agent2 = MockAgent("agent2")
        agent3 = MockAgent("agent3")
        mock_registry._register("agent1", agent1)
        mock_registry._register("agent2", agent2)
        mock_registry._register("agent3", agent3)

        with patch("aiops.agents.orchestrator.agent_registry", mock_registry):
            tasks = [
                AgentTask(agent_name="agent1", input_data={}),
                AgentTask(
                    agent_name="agent2",
                    input_data={},
                    condition=lambda ctx: ctx.get("agent1_latest", {}).get("condition_met", False)
                ),
                AgentTask(
                    agent_name="agent3",
                    input_data={},
                    condition=lambda ctx: False  # Always skip
                ),
            ]

            result = await orchestrator.execute_sequential(tasks)

            assert len(result.tasks) == 3
            assert result.tasks[0].status == ExecutionStatus.COMPLETED
            assert result.tasks[1].status == ExecutionStatus.COMPLETED
            assert result.tasks[2].status == ExecutionStatus.SKIPPED
            assert result.summary["skipped"] == 1


class TestParallelExecution:
    """Tests for parallel task execution."""

    @pytest.mark.asyncio
    async def test_parallel_execution_success(self, orchestrator, mock_registry):
        """Test successful parallel execution."""
        agent1 = MockAgent("agent1")
        agent2 = MockAgent("agent2")
        agent3 = MockAgent("agent3")
        mock_registry._register("agent1", agent1)
        mock_registry._register("agent2", agent2)
        mock_registry._register("agent3", agent3)

        with patch("aiops.agents.orchestrator.agent_registry", mock_registry):
            tasks = [
                AgentTask(agent_name="agent1", input_data={}),
                AgentTask(agent_name="agent2", input_data={}),
                AgentTask(agent_name="agent3", input_data={}),
            ]

            result = await orchestrator.execute_parallel(tasks)

            assert result.status == ExecutionStatus.COMPLETED
            assert len(result.tasks) == 3
            assert all(t.status == ExecutionStatus.COMPLETED for t in result.tasks)
            assert result.summary["completed"] == 3
            assert result.summary["failed"] == 0

    @pytest.mark.asyncio
    async def test_parallel_execution_with_failures(self, orchestrator, mock_registry):
        """Test parallel execution with some failures."""
        agent1 = MockAgent("agent1")
        agent2 = MockAgent("agent2", should_fail=True)
        agent3 = MockAgent("agent3")
        mock_registry._register("agent1", agent1)
        mock_registry._register("agent2", agent2)
        mock_registry._register("agent3", agent3)

        with patch("aiops.agents.orchestrator.agent_registry", mock_registry):
            tasks = [
                AgentTask(agent_name="agent1", input_data={}),
                AgentTask(agent_name="agent2", input_data={}),
                AgentTask(agent_name="agent3", input_data={}),
            ]

            result = await orchestrator.execute_parallel(tasks)

            assert result.status == ExecutionStatus.FAILED  # Overall failed due to one failure
            assert len(result.tasks) == 3
            assert result.summary["completed"] == 2
            assert result.summary["failed"] == 1

    @pytest.mark.asyncio
    async def test_parallel_execution_with_concurrency_limit(self, orchestrator, mock_registry):
        """Test parallel execution with concurrency limit."""
        agents = [MockAgent(f"agent{i}", delay=0.1) for i in range(5)]
        for i, agent in enumerate(agents):
            mock_registry._register(f"agent{i}", agent)

        with patch("aiops.agents.orchestrator.agent_registry", mock_registry):
            tasks = [AgentTask(agent_name=f"agent{i}", input_data={}) for i in range(5)]

            result = await orchestrator.execute_parallel(tasks, max_concurrency=2)

            assert result.status == ExecutionStatus.COMPLETED
            assert len(result.tasks) == 5
            assert result.summary["max_concurrency"] == 2


class TestWaterfallExecution:
    """Tests for waterfall task execution."""

    @pytest.mark.asyncio
    async def test_waterfall_execution_success(self, orchestrator, mock_registry):
        """Test successful waterfall execution."""
        agent1 = MockAgent("agent1", {"step": 1, "value": 100})
        agent2 = MockAgent("agent2", {"step": 2, "value": 200})
        agent3 = MockAgent("agent3", {"step": 3, "value": 300})
        mock_registry._register("agent1", agent1)
        mock_registry._register("agent2", agent2)
        mock_registry._register("agent3", agent3)

        with patch("aiops.agents.orchestrator.agent_registry", mock_registry):
            tasks = [
                AgentTask(agent_name="agent1", input_data={"initial": True}),
                AgentTask(agent_name="agent2", input_data={}),
                AgentTask(agent_name="agent3", input_data={}),
            ]

            result = await orchestrator.execute_waterfall(
                tasks, initial_input={"start": "value"}
            )

            assert result.status == ExecutionStatus.COMPLETED
            assert len(result.tasks) == 3
            assert all(t.status == ExecutionStatus.COMPLETED for t in result.tasks)
            assert result.summary["final_output"] == {"step": 3, "value": 300}

    @pytest.mark.asyncio
    async def test_waterfall_stops_on_failure(self, orchestrator, mock_registry):
        """Test waterfall stops on failure."""
        agent1 = MockAgent("agent1", {"value": 1})
        agent2 = MockAgent("agent2", should_fail=True)
        agent3 = MockAgent("agent3")
        mock_registry._register("agent1", agent1)
        mock_registry._register("agent2", agent2)
        mock_registry._register("agent3", agent3)

        with patch("aiops.agents.orchestrator.agent_registry", mock_registry):
            tasks = [
                AgentTask(agent_name="agent1", input_data={}),
                AgentTask(agent_name="agent2", input_data={}),
                AgentTask(agent_name="agent3", input_data={}),
            ]

            result = await orchestrator.execute_waterfall(tasks)

            assert result.status == ExecutionStatus.FAILED
            assert len(result.tasks) == 2  # Stops after failure
            assert result.tasks[1].status == ExecutionStatus.FAILED

    @pytest.mark.asyncio
    async def test_waterfall_passes_output_to_next_task(self, orchestrator, mock_registry):
        """Test that waterfall passes output to next task."""
        received_inputs = []

        class TrackingAgent(MockAgent):
            async def execute(self, **kwargs):
                received_inputs.append(kwargs)
                return await super().execute(**kwargs)

        agent1 = TrackingAgent("agent1", {"data": "from_agent1"})
        agent2 = TrackingAgent("agent2", {"data": "from_agent2"})
        mock_registry._register("agent1", agent1)
        mock_registry._register("agent2", agent2)

        with patch("aiops.agents.orchestrator.agent_registry", mock_registry):
            tasks = [
                AgentTask(agent_name="agent1", input_data={"initial": "value"}),
                AgentTask(agent_name="agent2", input_data={"extra": "data"}),
            ]

            await orchestrator.execute_waterfall(tasks, initial_input={"start": True})

            # Check that second agent received output from first
            assert len(received_inputs) == 2
            assert received_inputs[0]["initial"] == "value"
            assert received_inputs[0]["start"] is True
            # Second task should have output from first task merged
            assert "data" in received_inputs[1]


class TestDependencyExecution:
    """Tests for DAG-based dependency execution."""

    @pytest.mark.asyncio
    async def test_dependency_execution_simple_chain(self, orchestrator, mock_registry):
        """Test execution with simple dependency chain."""
        agent1 = MockAgent("agent1")
        agent2 = MockAgent("agent2")
        agent3 = MockAgent("agent3")
        mock_registry._register("agent1", agent1)
        mock_registry._register("agent2", agent2)
        mock_registry._register("agent3", agent3)

        with patch("aiops.agents.orchestrator.agent_registry", mock_registry):
            tasks = [
                AgentTask(agent_name="agent1", input_data={}, task_id="task1"),
                AgentTask(agent_name="agent2", input_data={}, task_id="task2", depends_on=["task1"]),
                AgentTask(agent_name="agent3", input_data={}, task_id="task3", depends_on=["task2"]),
            ]

            result = await orchestrator.execute_with_dependencies(tasks)

            assert result.status == ExecutionStatus.COMPLETED
            assert len(result.tasks) == 3

    @pytest.mark.asyncio
    async def test_dependency_execution_parallel_branches(self, orchestrator, mock_registry):
        """Test execution with parallel branches that merge."""
        agents = {f"agent{i}": MockAgent(f"agent{i}") for i in range(4)}
        for name, agent in agents.items():
            mock_registry._register(name, agent)

        with patch("aiops.agents.orchestrator.agent_registry", mock_registry):
            tasks = [
                AgentTask(agent_name="agent0", input_data={}, task_id="task0"),
                AgentTask(agent_name="agent1", input_data={}, task_id="task1", depends_on=["task0"]),
                AgentTask(agent_name="agent2", input_data={}, task_id="task2", depends_on=["task0"]),
                AgentTask(agent_name="agent3", input_data={}, task_id="task3", depends_on=["task1", "task2"]),
            ]

            result = await orchestrator.execute_with_dependencies(tasks)

            assert result.status == ExecutionStatus.COMPLETED
            assert len(result.tasks) == 4


class TestTaskTimeout:
    """Tests for task timeout handling."""

    @pytest.mark.asyncio
    async def test_task_timeout(self, orchestrator, mock_registry):
        """Test that tasks timeout correctly."""
        agent = MockAgent("slow_agent", delay=2.0)
        mock_registry._register("slow_agent", agent)

        with patch("aiops.agents.orchestrator.agent_registry", mock_registry):
            tasks = [
                AgentTask(agent_name="slow_agent", input_data={}, timeout_seconds=0.5),
            ]

            result = await orchestrator.execute_sequential(tasks)

            assert len(result.tasks) == 1
            assert result.tasks[0].status == ExecutionStatus.TIMEOUT
            assert result.tasks[0].error is not None


class TestTaskRetry:
    """Tests for task retry handling."""

    @pytest.mark.asyncio
    async def test_task_retry_success(self, orchestrator, mock_registry):
        """Test task retry mechanism."""
        class RetryAgent(MockAgent):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.attempt = 0

            async def execute_with_retry(self, max_attempts=3, **kwargs):
                self.attempt += 1
                if self.attempt < 2:
                    raise AgentExecutionError(self.name, "Temporary failure")
                return await super().execute(**kwargs)

        agent = RetryAgent("retry_agent")
        mock_registry._register("retry_agent", agent)

        with patch("aiops.agents.orchestrator.agent_registry", mock_registry):
            tasks = [
                AgentTask(agent_name="retry_agent", input_data={}, retry_attempts=3),
            ]

            result = await orchestrator.execute_sequential(tasks)

            assert result.status == ExecutionStatus.COMPLETED
            assert agent.attempt == 2  # Should succeed on second attempt


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_unregistered_agent_error(self, orchestrator, mock_registry):
        """Test error when agent is not registered."""
        with patch("aiops.agents.orchestrator.agent_registry", mock_registry):
            tasks = [
                AgentTask(agent_name="nonexistent", input_data={}),
            ]

            result = await orchestrator.execute_sequential(tasks)

            assert result.status == ExecutionStatus.FAILED
            assert len(result.tasks) == 1
            assert result.tasks[0].status == ExecutionStatus.FAILED
            assert "not registered" in result.tasks[0].error

    @pytest.mark.asyncio
    async def test_task_on_error_skip(self, orchestrator, mock_registry):
        """Test task with on_error='skip'."""
        agent = MockAgent("agent", should_fail=True)
        mock_registry._register("agent", agent)

        with patch("aiops.agents.orchestrator.agent_registry", mock_registry):
            tasks = [
                AgentTask(agent_name="agent", input_data={}, on_error="skip"),
            ]

            result = await orchestrator.execute_sequential(tasks)

            assert len(result.tasks) == 1
            assert result.tasks[0].status == ExecutionStatus.SKIPPED


class TestWorkflowManagement:
    """Tests for workflow storage and retrieval."""

    @pytest.mark.asyncio
    async def test_workflow_storage(self, orchestrator, mock_registry):
        """Test that workflows are stored."""
        agent = MockAgent("agent")
        mock_registry._register("agent", agent)

        with patch("aiops.agents.orchestrator.agent_registry", mock_registry):
            tasks = [AgentTask(agent_name="agent", input_data={})]
            result = await orchestrator.execute_sequential(tasks, workflow_id="stored_workflow")

            retrieved = orchestrator.get_workflow("stored_workflow")
            assert retrieved is not None
            assert retrieved.workflow_id == "stored_workflow"
            assert retrieved is result

    def test_list_workflows(self, orchestrator):
        """Test listing all workflows."""
        # Create some mock workflows
        workflow1 = WorkflowResult(
            workflow_id="wf1",
            status=ExecutionStatus.COMPLETED,
            tasks=[],
            started_at=datetime.now(),
        )
        workflow2 = WorkflowResult(
            workflow_id="wf2",
            status=ExecutionStatus.FAILED,
            tasks=[],
            started_at=datetime.now(),
        )

        orchestrator.workflows["wf1"] = workflow1
        orchestrator.workflows["wf2"] = workflow2

        workflows = orchestrator.list_workflows()
        assert len(workflows) == 2
        assert workflow1 in workflows
        assert workflow2 in workflows

    def test_clear_workflows(self, orchestrator):
        """Test clearing workflow history."""
        orchestrator.workflows["test"] = Mock()
        assert len(orchestrator.workflows) > 0

        orchestrator.clear_workflows()
        assert len(orchestrator.workflows) == 0

    def test_get_nonexistent_workflow(self, orchestrator):
        """Test getting a workflow that doesn't exist."""
        result = orchestrator.get_workflow("nonexistent")
        assert result is None


class TestTaskMetadata:
    """Tests for task metadata handling."""

    @pytest.mark.asyncio
    async def test_task_metadata_preserved(self, orchestrator, mock_registry):
        """Test that task metadata is preserved in results."""
        agent = MockAgent("agent")
        mock_registry._register("agent", agent)

        with patch("aiops.agents.orchestrator.agent_registry", mock_registry):
            tasks = [
                AgentTask(
                    agent_name="agent",
                    input_data={},
                    metadata={"priority": "high", "user": "test_user"}
                ),
            ]

            result = await orchestrator.execute_sequential(tasks)

            assert result.tasks[0].metadata["priority"] == "high"
            assert result.tasks[0].metadata["user"] == "test_user"
