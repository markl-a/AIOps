# Agent System Design Improvements

This document summarizes the comprehensive improvements made to the AIOps agent system.

## Overview

The agent system has been significantly enhanced with proper error handling, timeout management, result validation, and orchestration capabilities.

## 1. Enhanced Error Handling (base_agent.py)

### New Exception Types

Added specialized exception classes for better error tracking and handling:

- **AgentExecutionError**: Base exception for agent execution failures
- **AgentTimeoutError**: Raised when agent execution exceeds timeout
- **AgentValidationError**: Raised when result validation fails
- **AgentRetryExhaustedError**: Raised when all retry attempts are exhausted

### Decorators for Error Handling

#### @with_timeout
```python
@with_timeout(timeout_seconds=30.0)
async def execute(self, data: str) -> Result:
    # Agent execution logic
```

#### @with_retry
```python
@with_retry(max_attempts=3, delay_seconds=1.0, backoff_multiplier=2.0)
async def execute(self, data: str) -> Result:
    # Agent execution logic with automatic retry
```

#### @with_error_handling
```python
@with_error_handling(default_factory=lambda: DefaultResult(), reraise=False)
async def execute(self, data: str) -> Result:
    # Agent execution with fallback default value
```

## 2. Timeout Handling

### BaseAgent Enhancements

- Added `timeout_seconds` parameter to BaseAgent constructor (default: 300s)
- Added `max_retries` parameter for automatic retry logic
- New method: `execute_with_timeout()` - Execute with configurable timeout
- New method: `execute_with_retry()` - Execute with retry logic and exponential backoff

### Usage Example
```python
agent = CodeReviewAgent(timeout_seconds=60.0, max_retries=3)

# Execute with default timeout
result = await agent.execute(code="...")

# Execute with custom timeout
result = await agent.execute_with_timeout(timeout_seconds=120.0, code="...")

# Execute with retry
result = await agent.execute_with_retry(max_attempts=5, code="...")
```

## 3. Result Validation Framework

### Validation Methods

#### _validate_result()
Validates agent execution results against expected types or Pydantic schemas.

#### execute_with_validation()
```python
# Execute and validate against schema
result = await agent.execute_with_validation(
    schema=CodeReviewResult,
    code="...",
    language="python"
)
```

### Features
- Automatic Pydantic model validation
- Type checking
- Detailed validation error messages
- Raises AgentValidationError on validation failure

## 4. Agent Orchestration System (orchestrator.py)

### New File: aiops/agents/orchestrator.py

Provides comprehensive workflow management for multi-agent coordination.

### Execution Modes

#### Sequential Execution
Execute agents one after another, with optional stop-on-error:
```python
result = await orchestrator.execute_sequential(
    tasks=[task1, task2, task3],
    stop_on_error=True
)
```

#### Parallel Execution
Execute agents concurrently with concurrency control:
```python
result = await orchestrator.execute_parallel(
    tasks=[task1, task2, task3],
    max_concurrency=5
)
```

#### Waterfall Execution
Each agent receives the previous agent's output:
```python
result = await orchestrator.execute_waterfall(
    tasks=[task1, task2, task3],
    initial_input={"data": "..."}
)
```

#### DAG Execution
Execute tasks respecting dependencies:
```python
task2 = AgentTask(
    agent_name="test_generator",
    input_data={...},
    depends_on=["task1"]  # Wait for task1 to complete
)

result = await orchestrator.execute_with_dependencies(
    tasks=[task1, task2, task3]
)
```

### AgentTask Configuration

```python
task = AgentTask(
    agent_name="code_reviewer",
    input_data={"code": "...", "language": "python"},
    timeout_seconds=60.0,
    retry_attempts=3,
    depends_on=["previous_task"],  # For DAG execution
    condition=lambda ctx: ctx.get("should_run", True),  # Conditional execution
    on_error="skip"  # Options: "fail", "skip", "default"
)
```

### Workflow Results

All orchestration methods return a `WorkflowResult` with:
- Overall workflow status
- Individual task results
- Execution timing and duration
- Summary statistics

## 5. API Route Improvements (api/routes/agents.py)

### Enhanced Request Model

Added new parameters to AgentExecutionRequest:
```python
{
    "agent_type": "code_reviewer",
    "input_data": {"code": "...", "language": "python"},
    "timeout_seconds": 120.0,  # Optional, default 300s
    "max_retries": 3,          # Optional, default 0
    "async_execution": false,
    "callback_url": "https://..."  # Optional
}
```

### Improved Error Handling

Specific HTTP status codes for different error types:
- **408 Request Timeout**: AgentTimeoutError
- **422 Unprocessable Entity**: AgentValidationError
- **500 Internal Server Error**: AgentExecutionError, AgentRetryExhaustedError

### New Workflow Endpoints

#### POST /api/agents/workflows/execute
Execute complex multi-agent workflows:
```json
{
    "tasks": [
        {
            "agent_name": "code_reviewer",
            "input_data": {"code": "...", "language": "python"},
            "timeout_seconds": 60.0,
            "retry_attempts": 2
        },
        {
            "agent_name": "test_generator",
            "input_data": {"code": "...", "language": "python"},
            "timeout_seconds": 90.0
        }
    ],
    "execution_mode": "sequential",  // or "parallel", "waterfall"
    "max_concurrency": 5,            // for parallel mode
    "stop_on_error": true            // for sequential mode
}
```

#### GET /api/agents/workflows/{workflow_id}
Get workflow status and results

#### GET /api/agents/workflows
List all workflow executions

### Enhanced Execution Functions

- `_execute_agent_sync()`: Now supports timeout and retry parameters
- `_execute_with_retry_and_timeout()`: Helper for retry logic with timeout
- `_execute_agent_background()`: Updated for timeout and retry support

## 6. Registry Improvements (registry.py)

### Added Method

- `has_agent(name)`: Alias for `is_registered()` to improve API compatibility

## Key Benefits

1. **Robust Error Handling**: Specific exception types for different failure scenarios
2. **Timeout Management**: Prevent agents from running indefinitely
3. **Automatic Retries**: Handle transient failures with exponential backoff
4. **Result Validation**: Ensure agents return valid, well-formed data
5. **Workflow Orchestration**: Coordinate multiple agents for complex tasks
6. **Better Observability**: Detailed logging and error tracking
7. **API Flexibility**: Support for various execution modes and configurations

## Usage Examples

### Simple Agent Execution with Timeout
```python
# Via API
POST /api/agents/execute
{
    "agent_type": "code_reviewer",
    "input_data": {"code": "...", "language": "python"},
    "timeout_seconds": 60.0
}
```

### Agent Execution with Retry
```python
# Via API
POST /api/agents/execute
{
    "agent_type": "log_analyzer",
    "input_data": {"logs": "..."},
    "max_retries": 3
}
```

### Complex Workflow
```python
# Via API
POST /api/agents/workflows/execute
{
    "execution_mode": "sequential",
    "stop_on_error": true,
    "tasks": [
        {
            "agent_name": "code_reviewer",
            "input_data": {"code": "...", "language": "python"},
            "timeout_seconds": 60.0
        },
        {
            "agent_name": "security_scanner",
            "input_data": {"code": "...", "language": "python"},
            "timeout_seconds": 90.0,
            "retry_attempts": 2
        },
        {
            "agent_name": "test_generator",
            "input_data": {"code": "...", "language": "python"},
            "timeout_seconds": 120.0
        }
    ]
}
```

### Programmatic Usage
```python
from aiops.agents.registry import agent_registry
from aiops.agents.orchestrator import orchestrator, AgentTask

# Simple execution with timeout
agent = await agent_registry.get("code_reviewer")
result = await agent.execute_with_timeout(
    timeout_seconds=60.0,
    code="...",
    language="python"
)

# Orchestrated workflow
tasks = [
    AgentTask(
        agent_name="code_reviewer",
        input_data={"code": "...", "language": "python"},
        timeout_seconds=60.0,
        retry_attempts=3
    ),
    AgentTask(
        agent_name="test_generator",
        input_data={"code": "...", "language": "python"},
        timeout_seconds=90.0
    )
]

workflow_result = await orchestrator.execute_sequential(
    tasks=tasks,
    stop_on_error=True
)
```

## Files Modified

1. **aiops/agents/base_agent.py** - Enhanced with timeout, retry, and validation
2. **aiops/agents/orchestrator.py** - NEW: Workflow orchestration system
3. **aiops/agents/registry.py** - Added has_agent() method
4. **aiops/api/routes/agents.py** - Enhanced with timeout, retry, and workflow endpoints

## Testing Recommendations

1. Test timeout handling with long-running operations
2. Test retry logic with transient failures
3. Test validation with invalid results
4. Test workflow orchestration in all modes (sequential, parallel, waterfall, DAG)
5. Test error propagation and handling
6. Test API endpoints with various configurations
7. Load test parallel execution with high concurrency

## Future Enhancements

1. Circuit breaker pattern for failing agents
2. Agent result caching
3. Workflow versioning and history
4. Agent health checks and monitoring
5. Dynamic workflow composition based on results
6. Agent chaining with data transformation
7. Workflow templates and presets
8. Integration with message queues for async workflows
