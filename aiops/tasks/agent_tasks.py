"""Celery tasks for agent execution."""

from typing import Dict, Any, List
from celery import Task, group, chord
from loguru import logger

from aiops.tasks.celery_app import celery_app
from aiops.database import get_db, AgentExecution, ExecutionStatus
from aiops.core.structured_logger import get_structured_logger, TraceContext
from datetime import datetime


class AgentTask(Task):
    """Base task for agent execution."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure.

        Args:
            exc: Exception raised
            task_id: Task ID
            args: Task args
            kwargs: Task kwargs
            einfo: Exception info
        """
        logger.error(f"Agent task {task_id} failed: {exc}", exc_info=einfo)

        # Update execution status in database
        try:
            trace_id = kwargs.get("trace_id")
            if trace_id:
                # Note: This is simplified - in production, use proper DB session
                pass
        except Exception as e:
            logger.error(f"Failed to update execution status: {e}")

    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success.

        Args:
            retval: Return value
            task_id: Task ID
            args: Task args
            kwargs: Task kwargs
        """
        logger.info(f"Agent task {task_id} completed successfully")


@celery_app.task(
    base=AgentTask,
    bind=True,
    name="aiops.tasks.agent_tasks.execute_agent_task",
    max_retries=3,
    default_retry_delay=60,
)
def execute_agent_task(
    self,
    agent_name: str,
    operation: str,
    input_data: Dict[str, Any],
    user_id: int = None,
    trace_id: str = None,
) -> Dict[str, Any]:
    """Execute an agent task asynchronously.

    Args:
        agent_name: Name of the agent to execute
        operation: Operation to perform
        input_data: Input data for the agent
        user_id: User ID executing the task
        trace_id: Trace ID for tracking

    Returns:
        Task result
    """
    from aiops.agents import get_agent

    log = get_structured_logger(__name__)

    with TraceContext(trace_id):
        start_time = datetime.utcnow()

        try:
            log.info(
                f"Starting agent task: {agent_name}.{operation}",
                agent_name=agent_name,
                operation=operation,
                task_id=self.request.id,
            )

            # Get agent instance
            agent = get_agent(agent_name)

            # Execute agent
            result = agent.execute(**input_data)

            # Calculate duration
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            log.log_agent_execution(
                agent_name=agent_name,
                operation=operation,
                status="completed",
                duration_ms=duration_ms,
            )

            return {
                "success": True,
                "result": result,
                "duration_ms": duration_ms,
            }

        except Exception as exc:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            log.log_agent_execution(
                agent_name=agent_name,
                operation=operation,
                status="failed",
                duration_ms=duration_ms,
                error=str(exc),
            )

            # Retry on transient errors
            if "rate limit" in str(exc).lower() or "timeout" in str(exc).lower():
                raise self.retry(exc=exc)

            raise


@celery_app.task(name="aiops.tasks.agent_tasks.batch_code_review")
def batch_code_review(
    files: List[Dict[str, str]],
    language: str,
    user_id: int = None,
) -> Dict[str, Any]:
    """Perform batch code review on multiple files.

    Args:
        files: List of files with 'path' and 'code' keys
        language: Programming language
        user_id: User ID

    Returns:
        Batch review results
    """
    log = get_structured_logger(__name__)

    log.info(f"Starting batch code review for {len(files)} files", file_count=len(files))

    # Create tasks for each file
    tasks = [
        execute_agent_task.s(
            agent_name="code_reviewer",
            operation="execute",
            input_data={"code": file["code"], "language": language},
            user_id=user_id,
        )
        for file in files
    ]

    # Execute in parallel using Celery group
    job = group(tasks)
    result = job.apply_async()

    # Wait for all tasks to complete
    results = result.get()

    # Aggregate results
    total_issues = sum(len(r.get("result", {}).get("issues", [])) for r in results if r["success"])

    return {
        "success": True,
        "files_reviewed": len(files),
        "total_issues": total_issues,
        "results": results,
    }


@celery_app.task(name="aiops.tasks.agent_tasks.scheduled_analysis")
def scheduled_analysis(
    project_path: str,
    analysis_types: List[str],
    user_id: int = None,
) -> Dict[str, Any]:
    """Run scheduled project analysis.

    Args:
        project_path: Path to project
        analysis_types: Types of analysis to run (e.g., ['code_review', 'security_scan'])
        user_id: User ID

    Returns:
        Analysis results
    """
    log = get_structured_logger(__name__)

    log.info(
        f"Starting scheduled analysis for {project_path}",
        project_path=project_path,
        analysis_types=analysis_types,
    )

    results = {}

    for analysis_type in analysis_types:
        try:
            # Map analysis type to agent
            agent_mapping = {
                "code_review": "code_reviewer",
                "security_scan": "security_scanner",
                "test_generation": "test_generator",
                "performance": "performance_analyzer",
            }

            agent_name = agent_mapping.get(analysis_type)
            if not agent_name:
                log.warning(f"Unknown analysis type: {analysis_type}")
                continue

            # Execute analysis
            task_result = execute_agent_task.delay(
                agent_name=agent_name,
                operation="execute",
                input_data={"project_path": project_path},
                user_id=user_id,
            )

            results[analysis_type] = {
                "status": "submitted",
                "task_id": task_result.id,
            }

        except Exception as e:
            log.error(f"Failed to schedule {analysis_type}: {e}")
            results[analysis_type] = {
                "status": "failed",
                "error": str(e),
            }

    return {
        "success": True,
        "project_path": project_path,
        "results": results,
    }


@celery_app.task(name="aiops.tasks.agent_tasks.chain_analysis")
def chain_analysis(
    code: str,
    language: str,
    user_id: int = None,
) -> Dict[str, Any]:
    """Run chained analysis: code review -> security scan -> test generation.

    Args:
        code: Source code
        language: Programming language
        user_id: User ID

    Returns:
        Chained analysis results
    """
    log = get_structured_logger(__name__)

    # Create task chain using Celery chord
    tasks = [
        execute_agent_task.s(
            agent_name="code_reviewer",
            operation="execute",
            input_data={"code": code, "language": language},
            user_id=user_id,
        ),
        execute_agent_task.s(
            agent_name="security_scanner",
            operation="execute",
            input_data={"code": code, "language": language},
            user_id=user_id,
        ),
        execute_agent_task.s(
            agent_name="test_generator",
            operation="execute",
            input_data={"code": code, "language": language},
            user_id=user_id,
        ),
    ]

    # Execute as group
    job = group(tasks)
    result = job.apply_async()

    return {
        "success": True,
        "task_group_id": result.id,
        "message": "Analysis chain started",
    }
