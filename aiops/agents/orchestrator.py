"""Agent Orchestrator for managing complex workflows and multi-agent coordination."""

import asyncio
from typing import Any, Dict, List, Optional, Callable, Union, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from pydantic import BaseModel

from aiops.core.logger import get_logger
from aiops.agents.registry import agent_registry
from aiops.agents.base_agent import (
    AgentExecutionError,
    AgentTimeoutError,
    AgentValidationError,
)

logger = get_logger(__name__)


class ExecutionMode(str, Enum):
    """Agent execution modes."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    WATERFALL = "waterfall"  # Each agent gets previous agent's output


class ExecutionStatus(str, Enum):
    """Execution status for tasks."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


@dataclass
class AgentTask:
    """Represents a task for an agent to execute."""

    agent_name: str
    input_data: Dict[str, Any]
    task_id: Optional[str] = None
    depends_on: List[str] = field(default_factory=list)
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    timeout_seconds: Optional[float] = None
    retry_attempts: int = 0
    on_error: Optional[str] = "fail"  # "fail", "skip", "default"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    """Result of a task execution."""

    task_id: str
    agent_name: str
    status: ExecutionStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkflowResult(BaseModel):
    """Result of a workflow execution."""

    workflow_id: str
    status: ExecutionStatus
    tasks: List[TaskResult]
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    summary: Dict[str, Any] = {}


class AgentOrchestrator:
    """
    Orchestrator for managing complex agent workflows.

    Features:
    - Sequential and parallel execution
    - Conditional execution based on previous results
    - Dependency management between tasks
    - Timeout and retry handling
    - Result aggregation and validation
    """

    def __init__(self):
        """Initialize the orchestrator."""
        self.workflows: Dict[str, WorkflowResult] = {}
        self._task_counter = 0

    def _generate_task_id(self, agent_name: str) -> str:
        """Generate unique task ID."""
        self._task_counter += 1
        return f"{agent_name}_{self._task_counter}_{datetime.now().timestamp()}"

    async def execute_sequential(
        self,
        tasks: List[AgentTask],
        workflow_id: Optional[str] = None,
        stop_on_error: bool = True,
    ) -> WorkflowResult:
        """
        Execute tasks sequentially.

        Args:
            tasks: List of tasks to execute
            workflow_id: Optional workflow identifier
            stop_on_error: Whether to stop execution on first error

        Returns:
            WorkflowResult with all task results
        """
        workflow_id = workflow_id or f"seq_{datetime.now().timestamp()}"
        started_at = datetime.now()

        logger.info(f"Starting sequential workflow {workflow_id} with {len(tasks)} tasks")

        results = []
        context = {}  # Shared context for passing data between tasks

        for task in tasks:
            task_id = task.task_id or self._generate_task_id(task.agent_name)

            # Check condition if provided
            if task.condition and not task.condition(context):
                logger.info(f"Task {task_id} skipped due to condition")
                results.append(TaskResult(
                    task_id=task_id,
                    agent_name=task.agent_name,
                    status=ExecutionStatus.SKIPPED,
                    metadata=task.metadata
                ))
                continue

            # Execute task
            result = await self._execute_single_task(task, task_id, context)
            results.append(result)

            # Update context with result
            if result.status == ExecutionStatus.COMPLETED and result.result:
                context[task_id] = result.result
                context[f"{task.agent_name}_latest"] = result.result

            # Stop on error if configured
            if stop_on_error and result.status == ExecutionStatus.FAILED:
                logger.error(f"Stopping workflow {workflow_id} due to task failure: {task_id}")
                break

        completed_at = datetime.now()
        duration = (completed_at - started_at).total_seconds()

        # Determine overall status
        failed_count = sum(1 for r in results if r.status == ExecutionStatus.FAILED)
        completed_count = sum(1 for r in results if r.status == ExecutionStatus.COMPLETED)

        if failed_count > 0 and stop_on_error:
            overall_status = ExecutionStatus.FAILED
        elif completed_count == len([t for t in tasks if not (t.condition and not t.condition(context))]):
            overall_status = ExecutionStatus.COMPLETED
        else:
            overall_status = ExecutionStatus.FAILED

        workflow_result = WorkflowResult(
            workflow_id=workflow_id,
            status=overall_status,
            tasks=results,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration,
            summary={
                "total_tasks": len(tasks),
                "completed": completed_count,
                "failed": failed_count,
                "skipped": sum(1 for r in results if r.status == ExecutionStatus.SKIPPED),
            }
        )

        self.workflows[workflow_id] = workflow_result
        logger.info(f"Workflow {workflow_id} completed: {workflow_result.summary}")

        return workflow_result

    async def execute_parallel(
        self,
        tasks: List[AgentTask],
        workflow_id: Optional[str] = None,
        max_concurrency: Optional[int] = None,
    ) -> WorkflowResult:
        """
        Execute tasks in parallel.

        Args:
            tasks: List of tasks to execute
            workflow_id: Optional workflow identifier
            max_concurrency: Maximum number of concurrent tasks

        Returns:
            WorkflowResult with all task results
        """
        workflow_id = workflow_id or f"par_{datetime.now().timestamp()}"
        started_at = datetime.now()

        logger.info(f"Starting parallel workflow {workflow_id} with {len(tasks)} tasks")

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrency or len(tasks))

        async def execute_with_semaphore(task: AgentTask) -> TaskResult:
            async with semaphore:
                task_id = task.task_id or self._generate_task_id(task.agent_name)
                return await self._execute_single_task(task, task_id, {})

        # Execute all tasks concurrently
        results = await asyncio.gather(
            *[execute_with_semaphore(task) for task in tasks],
            return_exceptions=False
        )

        completed_at = datetime.now()
        duration = (completed_at - started_at).total_seconds()

        # Determine overall status
        failed_count = sum(1 for r in results if r.status == ExecutionStatus.FAILED)
        completed_count = sum(1 for r in results if r.status == ExecutionStatus.COMPLETED)

        overall_status = ExecutionStatus.COMPLETED if failed_count == 0 else ExecutionStatus.FAILED

        workflow_result = WorkflowResult(
            workflow_id=workflow_id,
            status=overall_status,
            tasks=results,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration,
            summary={
                "total_tasks": len(tasks),
                "completed": completed_count,
                "failed": failed_count,
                "max_concurrency": max_concurrency or len(tasks),
            }
        )

        self.workflows[workflow_id] = workflow_result
        logger.info(f"Workflow {workflow_id} completed: {workflow_result.summary}")

        return workflow_result

    async def execute_waterfall(
        self,
        tasks: List[AgentTask],
        workflow_id: Optional[str] = None,
        initial_input: Optional[Dict[str, Any]] = None,
    ) -> WorkflowResult:
        """
        Execute tasks in waterfall mode (each task receives previous task's output).

        Args:
            tasks: List of tasks to execute
            workflow_id: Optional workflow identifier
            initial_input: Initial input for first task

        Returns:
            WorkflowResult with all task results
        """
        workflow_id = workflow_id or f"waterfall_{datetime.now().timestamp()}"
        started_at = datetime.now()

        logger.info(f"Starting waterfall workflow {workflow_id} with {len(tasks)} tasks")

        results = []
        current_output = initial_input or {}

        for i, task in enumerate(tasks):
            task_id = task.task_id or self._generate_task_id(task.agent_name)

            # Merge task input with previous output
            merged_input = {**current_output, **task.input_data}
            task.input_data = merged_input

            # Execute task
            result = await self._execute_single_task(task, task_id, current_output)
            results.append(result)

            # Stop on error
            if result.status == ExecutionStatus.FAILED:
                logger.error(f"Stopping waterfall {workflow_id} at task {task_id}")
                break

            # Use result as input for next task
            if result.result:
                if isinstance(result.result, dict):
                    current_output = result.result
                else:
                    current_output = {"previous_result": result.result}

        completed_at = datetime.now()
        duration = (completed_at - started_at).total_seconds()

        # Determine overall status
        failed_count = sum(1 for r in results if r.status == ExecutionStatus.FAILED)
        completed_count = sum(1 for r in results if r.status == ExecutionStatus.COMPLETED)

        overall_status = ExecutionStatus.COMPLETED if failed_count == 0 else ExecutionStatus.FAILED

        workflow_result = WorkflowResult(
            workflow_id=workflow_id,
            status=overall_status,
            tasks=results,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration,
            summary={
                "total_tasks": len(tasks),
                "completed": completed_count,
                "failed": failed_count,
                "final_output": current_output,
            }
        )

        self.workflows[workflow_id] = workflow_result
        logger.info(f"Workflow {workflow_id} completed: {workflow_result.summary}")

        return workflow_result

    async def execute_with_dependencies(
        self,
        tasks: List[AgentTask],
        workflow_id: Optional[str] = None,
    ) -> WorkflowResult:
        """
        Execute tasks respecting dependencies (DAG execution).

        Args:
            tasks: List of tasks with dependencies
            workflow_id: Optional workflow identifier

        Returns:
            WorkflowResult with all task results
        """
        workflow_id = workflow_id or f"dag_{datetime.now().timestamp()}"
        started_at = datetime.now()

        logger.info(f"Starting DAG workflow {workflow_id} with {len(tasks)} tasks")

        # Build dependency graph
        task_map = {(task.task_id or self._generate_task_id(task.agent_name)): task
                   for task in tasks}
        results_map: Dict[str, TaskResult] = {}
        in_progress: Dict[str, asyncio.Task] = {}

        async def can_execute(task_id: str) -> bool:
            """Check if all dependencies are completed."""
            task = task_map[task_id]
            for dep_id in task.depends_on:
                if dep_id not in results_map:
                    return False
                if results_map[dep_id].status != ExecutionStatus.COMPLETED:
                    return False
            return True

        async def execute_when_ready(task_id: str):
            """Execute task when dependencies are ready."""
            # Wait for dependencies
            while not await can_execute(task_id):
                await asyncio.sleep(0.1)

            # Collect dependency results for context
            context = {}
            for dep_id in task_map[task_id].depends_on:
                if dep_id in results_map:
                    context[dep_id] = results_map[dep_id].result

            # Execute task
            result = await self._execute_single_task(task_map[task_id], task_id, context)
            results_map[task_id] = result

        # Start all tasks
        for task_id in task_map:
            in_progress[task_id] = asyncio.create_task(execute_when_ready(task_id))

        # Wait for all tasks to complete
        await asyncio.gather(*in_progress.values(), return_exceptions=True)

        completed_at = datetime.now()
        duration = (completed_at - started_at).total_seconds()

        results = list(results_map.values())
        failed_count = sum(1 for r in results if r.status == ExecutionStatus.FAILED)
        completed_count = sum(1 for r in results if r.status == ExecutionStatus.COMPLETED)

        overall_status = ExecutionStatus.COMPLETED if failed_count == 0 else ExecutionStatus.FAILED

        workflow_result = WorkflowResult(
            workflow_id=workflow_id,
            status=overall_status,
            tasks=results,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration,
            summary={
                "total_tasks": len(tasks),
                "completed": completed_count,
                "failed": failed_count,
            }
        )

        self.workflows[workflow_id] = workflow_result
        logger.info(f"Workflow {workflow_id} completed: {workflow_result.summary}")

        return workflow_result

    async def _execute_single_task(
        self,
        task: AgentTask,
        task_id: str,
        context: Dict[str, Any],
    ) -> TaskResult:
        """
        Execute a single agent task.

        Args:
            task: Task to execute
            task_id: Unique task identifier
            context: Execution context from previous tasks

        Returns:
            TaskResult with execution details
        """
        started_at = datetime.now()

        logger.info(f"Executing task {task_id} with agent {task.agent_name}")

        try:
            # Get agent instance
            if not agent_registry.is_registered(task.agent_name):
                raise ValueError(f"Agent '{task.agent_name}' not registered")

            agent = await agent_registry.get(task.agent_name)

            # Execute with timeout if specified
            if task.timeout_seconds:
                try:
                    result = await asyncio.wait_for(
                        agent.execute(**task.input_data),
                        timeout=task.timeout_seconds
                    )
                except asyncio.TimeoutError:
                    raise AgentTimeoutError(task.agent_name, task.timeout_seconds)
            else:
                # Execute with retry if specified
                if task.retry_attempts > 0:
                    result = await agent.execute_with_retry(
                        max_attempts=task.retry_attempts,
                        **task.input_data
                    )
                else:
                    result = await agent.execute(**task.input_data)

            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()

            return TaskResult(
                task_id=task_id,
                agent_name=task.agent_name,
                status=ExecutionStatus.COMPLETED,
                result=result,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
                metadata=task.metadata,
            )

        except AgentTimeoutError as e:
            logger.error(f"Task {task_id} timed out: {e}")
            return TaskResult(
                task_id=task_id,
                agent_name=task.agent_name,
                status=ExecutionStatus.TIMEOUT,
                error=str(e),
                started_at=started_at,
                completed_at=datetime.now(),
                metadata=task.metadata,
            )

        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}", exc_info=True)

            # Handle error based on configuration
            if task.on_error == "skip":
                return TaskResult(
                    task_id=task_id,
                    agent_name=task.agent_name,
                    status=ExecutionStatus.SKIPPED,
                    error=str(e),
                    started_at=started_at,
                    completed_at=datetime.now(),
                    metadata=task.metadata,
                )

            return TaskResult(
                task_id=task_id,
                agent_name=task.agent_name,
                status=ExecutionStatus.FAILED,
                error=str(e),
                started_at=started_at,
                completed_at=datetime.now(),
                metadata=task.metadata,
            )

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowResult]:
        """Get workflow result by ID."""
        return self.workflows.get(workflow_id)

    def list_workflows(self) -> List[WorkflowResult]:
        """List all workflow results."""
        return list(self.workflows.values())

    def clear_workflows(self) -> None:
        """Clear all workflow history."""
        self.workflows.clear()
        logger.info("Cleared all workflow history")


# Global orchestrator instance
orchestrator = AgentOrchestrator()
