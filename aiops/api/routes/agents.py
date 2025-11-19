"""Agent Execution Routes"""

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from aiops.core.structured_logger import get_structured_logger


logger = get_structured_logger(__name__)
router = APIRouter()


# Request/Response Models
class AgentExecutionRequest(BaseModel):
    """Request to execute an agent."""

    agent_type: str = Field(..., description="Type of agent to execute")
    input_data: Dict[str, Any] = Field(..., description="Input data for the agent")
    async_execution: bool = Field(default=False, description="Execute asynchronously")
    callback_url: Optional[str] = Field(None, description="URL to call when complete")


class AgentExecutionResponse(BaseModel):
    """Response from agent execution."""

    execution_id: str
    agent_type: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None


class AgentListResponse(BaseModel):
    """List of available agents."""

    agents: List[Dict[str, Any]]
    total: int


# In-memory execution tracking (use database in production)
executions: Dict[str, Dict[str, Any]] = {}


@router.get("/", response_model=AgentListResponse)
async def list_agents():
    """List all available agents."""
    agents = [
        {
            "name": "code_reviewer",
            "description": "Reviews code for quality and security issues",
            "category": "code_quality",
        },
        {
            "name": "k8s_optimizer",
            "description": "Optimizes Kubernetes resource configurations",
            "category": "infrastructure",
        },
        {
            "name": "security_scanner",
            "description": "Scans code for security vulnerabilities",
            "category": "security",
        },
        {
            "name": "test_generator",
            "description": "Generates unit and integration tests",
            "category": "testing",
        },
        {
            "name": "performance_analyzer",
            "description": "Analyzes code and system performance",
            "category": "performance",
        },
        {
            "name": "cost_optimizer",
            "description": "Optimizes cloud infrastructure costs",
            "category": "cost",
        },
    ]

    return AgentListResponse(agents=agents, total=len(agents))


@router.post("/execute", response_model=AgentExecutionResponse)
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

        except Exception as e:
            logger.error(
                f"Agent execution failed: {str(e)}",
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


@router.get("/executions/{execution_id}", response_model=AgentExecutionResponse)
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
async def _execute_agent_sync(agent_type: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Execute agent synchronously (mock implementation)."""
    # In production, this would actually execute the agent
    import asyncio
    await asyncio.sleep(0.5)  # Simulate execution

    return {
        "status": "success",
        "message": f"Agent {agent_type} executed successfully",
        "data": {
            "agent_type": agent_type,
            "processed": True,
        },
    }


async def _execute_agent_background(
    execution_id: str,
    agent_type: str,
    input_data: Dict[str, Any],
):
    """Execute agent in background."""
    try:
        result = await _execute_agent_sync(agent_type, input_data)

        executions[execution_id].update({
            "status": "completed",
            "result": result,
            "completed_at": datetime.now(),
        })

    except Exception as e:
        executions[execution_id].update({
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.now(),
        })
