"""Agent Execution Routes"""

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import traceback
import re
import json
import asyncio

from aiops.core.structured_logger import get_structured_logger
from aiops.agents.registry import agent_registry
from aiops.agents.base_agent import (
    AgentExecutionError,
    AgentTimeoutError,
    AgentValidationError,
    AgentRetryExhaustedError,
)
from aiops.agents.orchestrator import (
    orchestrator,
    AgentTask,
    ExecutionMode,
    WorkflowResult,
)


logger = get_structured_logger(__name__)
router = APIRouter()


# Security: Maximum size for input data (1MB)
MAX_INPUT_DATA_SIZE = 1024 * 1024  # 1MB in bytes


def validate_input_data_size(input_data: Dict[str, Any]) -> None:
    """Validate that input data is not too large."""
    try:
        json_str = json.dumps(input_data)
        size_bytes = len(json_str.encode('utf-8'))

        if size_bytes > MAX_INPUT_DATA_SIZE:
            raise ValueError(
                f"Input data too large: {size_bytes} bytes (max: {MAX_INPUT_DATA_SIZE} bytes)"
            )
    except (TypeError, ValueError) as e:
        if "Input data too large" in str(e):
            raise
        raise ValueError("Input data must be JSON serializable")


# Request/Response Models
class AgentExecutionRequest(BaseModel):
    """Request to execute an agent."""

    agent_type: str = Field(
        ...,
        description="Type of agent to execute",
        min_length=1,
        max_length=100,
        examples=["code_reviewer", "security_scanner", "k8s_optimizer"]
    )
    input_data: Dict[str, Any] = Field(
        ...,
        description="Input data for the agent",
        examples=[{"file_path": "/src/main.py", "check_security": True}]
    )
    async_execution: bool = Field(
        default=False,
        description="Execute asynchronously in background. Returns immediately with execution_id",
        examples=[False]
    )
    timeout_seconds: Optional[float] = Field(
        default=None,
        description="Maximum execution time in seconds (default: 300)",
        ge=1.0,
        le=3600.0,  # Max 1 hour
        examples=[300.0]
    )
    max_retries: Optional[int] = Field(
        default=None,
        description="Maximum number of retry attempts on failure (default: 0)",
        ge=0,
        le=5,  # Max 5 retries
        examples=[3]
    )
    callback_url: Optional[str] = Field(
        None,
        description="URL to call when execution completes (for async execution)",
        max_length=500,
        examples=["https://example.com/webhooks/agent-complete"]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "agent_type": "code_reviewer",
                "input_data": {
                    "repository": "example/repo",
                    "file_path": "src/main.py",
                    "check_security": True
                },
                "async_execution": False,
                "timeout_seconds": 300.0,
                "max_retries": 3,
                "callback_url": "https://example.com/webhooks/callback"
            }
        }

    @field_validator('agent_type')
    @classmethod
    def validate_agent_type(cls, v: str) -> str:
        """Validate agent type."""
        # Strip whitespace
        v = v.strip()

        # Only allow alphanumeric, underscores, and hyphens
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Agent type contains invalid characters")

        return v

    @field_validator('input_data')
    @classmethod
    def validate_input_data(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate input data."""
        # Check size
        validate_input_data_size(v)

        # Validate keys (prevent injection through key names)
        for key in v.keys():
            if not isinstance(key, str):
                raise ValueError("All input data keys must be strings")

            # Limit key length
            if len(key) > 255:
                raise ValueError(f"Input data key too long: {key[:50]}...")

            # Only allow safe characters in keys
            if not re.match(r'^[a-zA-Z0-9_.-]+$', key):
                raise ValueError(f"Invalid characters in input data key: {key}")

        return v

    @field_validator('callback_url')
    @classmethod
    def validate_callback_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate callback URL."""
        if v is None:
            return v

        # Strip whitespace
        v = v.strip()

        # Validate URL format (basic check)
        if not re.match(r'^https?://', v):
            raise ValueError("Callback URL must start with http:// or https://")

        # Prevent SSRF - disallow localhost, internal IPs, etc.
        dangerous_patterns = [
            r'localhost',
            r'127\.0\.0\.',
            r'0\.0\.0\.0',
            r'10\.\d+\.\d+\.\d+',      # Private 10.x.x.x
            r'172\.(1[6-9]|2[0-9]|3[01])\.\d+\.\d+',  # Private 172.16-31.x.x
            r'192\.168\.\d+\.\d+',     # Private 192.168.x.x
            r'169\.254\.\d+\.\d+',     # Link-local
            r'\[::\]',                  # IPv6 localhost
            r'\[::1\]',                 # IPv6 localhost
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError(
                    "Callback URL cannot point to internal/local addresses (SSRF protection)"
                )

        return v


class AgentExecutionResponse(BaseModel):
    """Response from agent execution."""

    execution_id: str = Field(..., description="Unique execution identifier")
    agent_type: str = Field(..., description="Type of agent that was executed")
    status: str = Field(..., description="Execution status: running, completed, failed, timeout, cancelled")
    result: Optional[Dict[str, Any]] = Field(None, description="Execution result data if completed successfully")
    error: Optional[str] = Field(None, description="Error message if execution failed")
    started_at: datetime = Field(..., description="Timestamp when execution started")
    completed_at: Optional[datetime] = Field(None, description="Timestamp when execution completed")
    duration_seconds: Optional[float] = Field(None, description="Total execution duration in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "execution_id": "550e8400-e29b-41d4-a716-446655440000",
                "agent_type": "code_reviewer",
                "status": "completed",
                "result": {
                    "status": "success",
                    "message": "Agent code_reviewer executed successfully",
                    "data": {
                        "issues_found": 3,
                        "suggestions": ["Use type hints", "Add docstrings"]
                    }
                },
                "error": None,
                "started_at": "2024-01-15T10:30:00Z",
                "completed_at": "2024-01-15T10:30:05Z",
                "duration_seconds": 5.2
            }
        }


class AgentListResponse(BaseModel):
    """List of available agents."""

    agents: List[Dict[str, Any]] = Field(..., description="List of available agents with their metadata")
    total: int = Field(..., description="Total number of available agents")

    class Config:
        json_schema_extra = {
            "example": {
                "agents": [
                    {
                        "name": "code_reviewer",
                        "description": "Analyzes code for quality issues and best practices",
                        "category": "code_quality",
                        "tags": ["python", "review", "quality"]
                    },
                    {
                        "name": "security_scanner",
                        "description": "Scans code for security vulnerabilities",
                        "category": "security",
                        "tags": ["security", "scanning"]
                    }
                ],
                "total": 2
            }
        }


# In-memory execution tracking (use database in production)
executions: Dict[str, Dict[str, Any]] = {}


@router.get(
    "/",
    response_model=AgentListResponse,
    summary="List available agents",
    description="Retrieve a list of all registered agents with their metadata including name, description, category, and tags.",
    responses={
        200: {
            "description": "Successfully retrieved list of agents",
            "content": {
                "application/json": {
                    "example": {
                        "agents": [
                            {
                                "name": "code_reviewer",
                                "description": "Analyzes code for quality issues",
                                "category": "code_quality",
                                "tags": ["python", "review"]
                            }
                        ],
                        "total": 1
                    }
                }
            }
        }
    }
)
async def list_agents():
    """List all available agents from the registry."""
    registered_agents = agent_registry.list_agents()

    agents = [
        {
            "name": info.name,
            "description": info.description,
            "category": info.category,
            "tags": info.tags,
        }
        for info in registered_agents
    ]

    return AgentListResponse(agents=agents, total=len(agents))


@router.post(
    "/execute",
    response_model=AgentExecutionResponse,
    summary="Execute an agent",
    description="""Execute a specific agent with the provided input data.

    Supports both synchronous and asynchronous execution modes:
    - **Synchronous**: Waits for execution to complete and returns the result
    - **Asynchronous**: Returns immediately with execution_id for later polling

    Features:
    - Configurable timeouts (1s - 1 hour)
    - Automatic retry with exponential backoff
    - Optional callback URL for async execution
    - Input validation and sanitization
    """,
    responses={
        200: {
            "description": "Agent execution completed successfully (synchronous) or started (asynchronous)",
        },
        400: {
            "description": "Invalid request parameters",
            "content": {
                "application/json": {
                    "example": {
                        "error": "ValidationError",
                        "message": "Request validation failed",
                        "details": [{"field": "agent_type", "message": "Unknown agent type"}]
                    }
                }
            }
        },
        408: {
            "description": "Agent execution timed out",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Agent execution timed out after 300.0s"
                    }
                }
            }
        },
        422: {
            "description": "Agent result validation failed",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Agent result validation failed: Invalid output schema"
                    }
                }
            }
        },
        500: {
            "description": "Agent execution failed or internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Agent execution failed: Internal agent error"
                    }
                }
            }
        }
    }
)
async def execute_agent(
    request: AgentExecutionRequest,
    background_tasks: BackgroundTasks,
):
    """Execute an agent."""
    execution_id = str(uuid.uuid4())
    started_at = datetime.now()

    logger.info(
        f"Executing agent: {request.agent_type}",
        execution_id=execution_id,
        agent_type=request.agent_type,
        async_execution=request.async_execution,
    )

    # Initialize execution record
    execution_record = {
        "execution_id": execution_id,
        "agent_type": request.agent_type,
        "status": "running",
        "input_data": request.input_data,
        "started_at": started_at,
        "completed_at": None,
        "result": None,
        "error": None,
    }

    executions[execution_id] = execution_record

    if request.async_execution:
        # Execute in background
        background_tasks.add_task(
            _execute_agent_background,
            execution_id,
            request.agent_type,
            request.input_data,
            request.timeout_seconds,
            request.max_retries,
        )

        return AgentExecutionResponse(
            execution_id=execution_id,
            agent_type=request.agent_type,
            status="running",
            started_at=started_at,
        )
    else:
        # Execute synchronously
        try:
            result = await _execute_agent_sync(
                request.agent_type,
                request.input_data,
                request.timeout_seconds,
                request.max_retries,
            )

            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()

            execution_record.update({
                "status": "completed",
                "completed_at": completed_at,
                "result": result,
            })

            return AgentExecutionResponse(
                execution_id=execution_id,
                agent_type=request.agent_type,
                status="completed",
                result=result,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
            )

        except AgentTimeoutError as e:
            logger.error(
                f"Agent execution timed out: {str(e)}",
                execution_id=execution_id,
                agent_type=request.agent_type,
                timeout_seconds=e.timeout_seconds,
            )

            execution_record.update({
                "status": "timeout",
                "error": str(e),
                "completed_at": datetime.now(),
            })

            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail=f"Agent execution timed out after {e.timeout_seconds}s",
            )

        except AgentValidationError as e:
            logger.error(
                f"Agent result validation failed: {str(e)}",
                execution_id=execution_id,
                agent_type=request.agent_type,
                validation_errors=e.validation_errors,
            )

            execution_record.update({
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.now(),
            })

            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Agent result validation failed: {str(e)}",
            )

        except AgentRetryExhaustedError as e:
            logger.error(
                f"Agent execution failed after {e.attempts} retries: {str(e)}",
                execution_id=execution_id,
                agent_type=request.agent_type,
                attempts=e.attempts,
            )

            execution_record.update({
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.now(),
            })

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Agent execution failed after {e.attempts} retries",
            )

        except AgentExecutionError as e:
            logger.error(
                f"Agent execution error: {str(e)}",
                execution_id=execution_id,
                agent_type=request.agent_type,
                error=str(e),
            )

            execution_record.update({
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.now(),
            })

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Agent execution failed: {str(e)}",
            )

        except Exception as e:
            logger.error(
                f"Unexpected error during agent execution: {str(e)}",
                execution_id=execution_id,
                agent_type=request.agent_type,
                error=str(e),
                traceback=traceback.format_exc(),
            )

            execution_record.update({
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.now(),
            })

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Agent execution failed: {str(e)}",
            )


@router.get(
    "/executions/{execution_id}",
    response_model=AgentExecutionResponse,
    summary="Get execution status",
    description="Retrieve the status and result of a specific agent execution by its ID.",
    responses={
        200: {"description": "Execution found and returned successfully"},
        404: {
            "description": "Execution not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Execution 550e8400-e29b-41d4-a716-446655440000 not found"}
                }
            }
        }
    }
)
async def get_execution(execution_id: str):
    """Get execution status and result."""
    if execution_id not in executions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution {execution_id} not found",
        )

    record = executions[execution_id]

    duration = None
    if record["completed_at"]:
        duration = (record["completed_at"] - record["started_at"]).total_seconds()

    return AgentExecutionResponse(
        execution_id=record["execution_id"],
        agent_type=record["agent_type"],
        status=record["status"],
        result=record.get("result"),
        error=record.get("error"),
        started_at=record["started_at"],
        completed_at=record.get("completed_at"),
        duration_seconds=duration,
    )


@router.get("/executions", response_model=List[AgentExecutionResponse])
async def list_executions(
    agent_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 100,
):
    """List recent agent executions."""
    # Validate limit
    if limit < 1 or limit > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 1000"
        )

    # Validate agent_type if provided
    if agent_type:
        if not re.match(r'^[a-zA-Z0-9_-]+$', agent_type):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid agent type"
            )

    # Validate status_filter if provided
    if status_filter:
        allowed_statuses = ['pending', 'running', 'completed', 'failed', 'cancelled']
        if status_filter not in allowed_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status filter. Allowed: {', '.join(allowed_statuses)}"
            )

    filtered_executions = executions.values()

    if agent_type:
        filtered_executions = [
            e for e in filtered_executions
            if e["agent_type"] == agent_type
        ]

    if status_filter:
        filtered_executions = [
            e for e in filtered_executions
            if e["status"] == status_filter
        ]

    # Sort by started_at descending
    sorted_executions = sorted(
        filtered_executions,
        key=lambda x: x["started_at"],
        reverse=True,
    )[:limit]

    return [
        AgentExecutionResponse(
            execution_id=e["execution_id"],
            agent_type=e["agent_type"],
            status=e["status"],
            result=e.get("result"),
            error=e.get("error"),
            started_at=e["started_at"],
            completed_at=e.get("completed_at"),
            duration_seconds=(
                (e["completed_at"] - e["started_at"]).total_seconds()
                if e.get("completed_at") else None
            ),
        )
        for e in sorted_executions
    ]


# Helper functions
async def _execute_agent_sync(
    agent_type: str,
    input_data: Dict[str, Any],
    timeout_seconds: Optional[float] = None,
    max_retries: Optional[int] = None,
) -> Dict[str, Any]:
    """Execute agent synchronously using the agent registry."""
    # Check if agent exists
    if not agent_registry.has_agent(agent_type):
        raise ValueError(f"Unknown agent type: {agent_type}")

    try:
        # Get agent instance from registry (lazy-loaded)
        agent = await agent_registry.get(agent_type)

        # Determine execution strategy based on parameters
        timeout = timeout_seconds or 300.0  # Default 5 minutes
        retries = max_retries or 0

        # Execute with timeout and retry if specified
        if retries > 0:
            # Execute with retry
            result = await _execute_with_retry_and_timeout(
                agent, input_data, timeout, retries
            )
        else:
            # Execute with timeout only
            result = await asyncio.wait_for(
                agent.execute(**input_data),
                timeout=timeout
            )

        # Convert result to dict if it's a Pydantic model
        if hasattr(result, "model_dump"):
            result_data = result.model_dump()
        elif hasattr(result, "dict"):
            result_data = result.dict()
        elif isinstance(result, dict):
            result_data = result
        else:
            result_data = {"result": str(result)}

        return {
            "status": "success",
            "message": f"Agent {agent_type} executed successfully",
            "data": result_data,
        }

    except asyncio.TimeoutError:
        raise AgentTimeoutError(agent_type, timeout_seconds or 300.0)
    except Exception as e:
        logger.error(
            f"Agent execution error: {str(e)}",
            agent_type=agent_type,
            error=str(e),
            traceback=traceback.format_exc(),
        )
        raise


async def _execute_with_retry_and_timeout(
    agent: Any,
    input_data: Dict[str, Any],
    timeout_seconds: float,
    max_retries: int,
) -> Any:
    """Execute agent with retry and timeout."""
    last_error = None
    delay = 1.0

    for attempt in range(1, max_retries + 1):
        try:
            return await asyncio.wait_for(
                agent.execute(**input_data),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError as e:
            # Don't retry on timeout
            raise AgentTimeoutError(agent.name, timeout_seconds)
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                logger.warning(
                    f"Agent {agent.name}: Attempt {attempt}/{max_retries} failed: {e}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
                delay *= 2.0  # Exponential backoff
            else:
                logger.error(
                    f"Agent {agent.name}: All {max_retries} attempts failed"
                )

    raise AgentRetryExhaustedError(
        agent_name=agent.name,
        attempts=max_retries,
        last_error=last_error
    )


async def _execute_agent_background(
    execution_id: str,
    agent_type: str,
    input_data: Dict[str, Any],
    timeout_seconds: Optional[float] = None,
    max_retries: Optional[int] = None,
):
    """Execute agent in background."""
    try:
        result = await _execute_agent_sync(
            agent_type,
            input_data,
            timeout_seconds,
            max_retries
        )

        executions[execution_id].update({
            "status": "completed",
            "result": result,
            "completed_at": datetime.now(),
        })

    except AgentTimeoutError as e:
        executions[execution_id].update({
            "status": "timeout",
            "error": str(e),
            "completed_at": datetime.now(),
        })

    except (AgentExecutionError, AgentRetryExhaustedError, AgentValidationError) as e:
        executions[execution_id].update({
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.now(),
        })

    except Exception as e:
        executions[execution_id].update({
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.now(),
        })


# Workflow Orchestration Endpoints
class WorkflowTaskRequest(BaseModel):
    """Request model for a workflow task."""

    agent_name: str = Field(..., description="Name of the agent to execute")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Input data for the agent")
    timeout_seconds: Optional[float] = Field(None, description="Task timeout in seconds")
    retry_attempts: int = Field(default=0, description="Number of retry attempts", ge=0, le=5)


class WorkflowExecutionRequest(BaseModel):
    """Request to execute a workflow."""

    tasks: List[WorkflowTaskRequest] = Field(..., description="List of tasks to execute")
    execution_mode: str = Field(
        default="sequential",
        description="Execution mode: sequential, parallel, or waterfall"
    )
    workflow_id: Optional[str] = Field(None, description="Optional workflow identifier")
    max_concurrency: Optional[int] = Field(None, description="Max concurrent tasks (parallel mode only)")
    stop_on_error: bool = Field(default=True, description="Stop on first error (sequential mode only)")


@router.post("/workflows/execute")
async def execute_workflow(request: WorkflowExecutionRequest):
    """Execute a workflow of multiple agents."""
    try:
        # Convert request tasks to AgentTask objects
        tasks = [
            AgentTask(
                agent_name=task.agent_name,
                input_data=task.input_data,
                timeout_seconds=task.timeout_seconds,
                retry_attempts=task.retry_attempts,
            )
            for task in request.tasks
        ]

        # Execute based on mode
        if request.execution_mode == ExecutionMode.SEQUENTIAL:
            result = await orchestrator.execute_sequential(
                tasks=tasks,
                workflow_id=request.workflow_id,
                stop_on_error=request.stop_on_error,
            )
        elif request.execution_mode == ExecutionMode.PARALLEL:
            result = await orchestrator.execute_parallel(
                tasks=tasks,
                workflow_id=request.workflow_id,
                max_concurrency=request.max_concurrency,
            )
        elif request.execution_mode == ExecutionMode.WATERFALL:
            result = await orchestrator.execute_waterfall(
                tasks=tasks,
                workflow_id=request.workflow_id,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid execution mode: {request.execution_mode}. "
                       f"Must be one of: sequential, parallel, waterfall"
            )

        return result

    except Exception as e:
        logger.error(f"Workflow execution failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow execution failed: {str(e)}"
        )


@router.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get workflow status and results."""
    result = orchestrator.get_workflow(workflow_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )

    return result


@router.get("/workflows")
async def list_workflows():
    """List all workflow executions."""
    workflows = orchestrator.list_workflows()
    return {
        "workflows": workflows,
        "total": len(workflows)
    }
