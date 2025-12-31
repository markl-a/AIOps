"""Generic agent endpoint handler to reduce code duplication."""

from typing import Any, Callable, Dict, Optional, Type, TypeVar
from functools import wraps
from fastapi import HTTPException
from pydantic import BaseModel

from aiops.core.logger import get_logger
from aiops.agents.base_agent import BaseAgent, AgentExecutionError

logger = get_logger(__name__)

T = TypeVar('T', bound=BaseModel)
AgentType = TypeVar('AgentType', bound=BaseAgent)


class AgentEndpointHandler:
    """
    Generic handler for agent API endpoints.

    Reduces boilerplate code for agent execution endpoints by providing
    consistent error handling, logging, and response formatting.

    Usage:
        handler = AgentEndpointHandler()

        @app.post("/api/v1/code/review")
        async def review_code(request: CodeReviewRequest, ...):
            return await handler.execute(
                agent_class=CodeReviewAgent,
                request=request,
                execute_kwargs={"code": request.code, "language": request.language},
                user=current_user,
            )
    """

    def __init__(self, log_requests: bool = True):
        """
        Initialize the handler.

        Args:
            log_requests: Whether to log incoming requests
        """
        self.log_requests = log_requests

    async def execute(
        self,
        agent_class: Type[AgentType],
        request: BaseModel,
        execute_kwargs: Dict[str, Any],
        user: Optional[Dict[str, Any]] = None,
        agent_kwargs: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Execute an agent and handle errors consistently.

        Args:
            agent_class: The agent class to instantiate
            request: The incoming request model
            execute_kwargs: Keyword arguments to pass to agent.execute()
            user: Optional user information for logging
            agent_kwargs: Optional keyword arguments for agent initialization

        Returns:
            Agent execution result

        Raises:
            HTTPException: On execution failure
        """
        agent_name = agent_class.__name__
        username = user.get('username', 'anonymous') if user else 'anonymous'

        if self.log_requests:
            logger.info(f"{agent_name} requested by {username}")

        try:
            # Initialize agent
            agent = agent_class(**(agent_kwargs or {}))

            # Execute agent
            result = await agent.execute(**execute_kwargs)

            logger.debug(f"{agent_name} completed successfully for {username}")
            return result

        except AgentExecutionError as e:
            logger.error(f"{agent_name} execution error: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Agent execution failed: {e.message}"
            )
        except ValueError as e:
            logger.warning(f"{agent_name} validation error: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid request: {str(e)}"
            )
        except Exception as e:
            logger.error(f"{agent_name} unexpected error: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Internal error: {str(e)}"
            )


def agent_endpoint(
    agent_class: Type[BaseAgent],
    extract_kwargs: Optional[Callable[[BaseModel], Dict[str, Any]]] = None,
):
    """
    Decorator to create an agent endpoint with consistent error handling.

    Args:
        agent_class: The agent class to use
        extract_kwargs: Function to extract execute() kwargs from request

    Usage:
        @app.post("/api/v1/code/review")
        @agent_endpoint(
            CodeReviewAgent,
            extract_kwargs=lambda r: {"code": r.code, "language": r.language}
        )
        async def review_code(request: CodeReviewRequest, current_user: Dict):
            pass  # Handler logic is provided by decorator
    """
    handler = AgentEndpointHandler()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: BaseModel, current_user: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
            # Extract kwargs from request
            if extract_kwargs:
                execute_kwargs = extract_kwargs(request)
            else:
                # Default: use all request fields except internal ones
                execute_kwargs = {
                    k: v for k, v in request.model_dump().items()
                    if not k.startswith('_')
                }

            return await handler.execute(
                agent_class=agent_class,
                request=request,
                execute_kwargs=execute_kwargs,
                user=current_user,
            )
        return wrapper
    return decorator


# Pre-configured handler instance
default_handler = AgentEndpointHandler()
