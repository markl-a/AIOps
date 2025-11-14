# AIOps Framework Architecture

## Overview

The AIOps Framework is designed with a layered architecture that promotes modularity, scalability, and ease of use.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interfaces                         │
├─────────────────┬─────────────────┬─────────────────────────┤
│   CLI (Typer)   │  REST API       │  Python SDK             │
│   - Commands    │  (FastAPI)      │  - Direct Import        │
│   - Rich Output │  - Endpoints    │  - Async/Await          │
└─────────────────┴─────────────────┴─────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────────┐
│                      Agent Layer                            │
├─────────────────────────────────────────────────────────────┤
│  Basic Layer:                                               │
│  - CodeReviewAgent                                          │
│  - TestGeneratorAgent                                       │
│  - LogAnalyzerAgent                                         │
│                                                             │
│  Intermediate Layer:                                        │
│  - CICDOptimizerAgent                                       │
│  - DocGeneratorAgent                                        │
│  - PerformanceAnalyzerAgent                                 │
│                                                             │
│  Advanced Layer:                                            │
│  - AnomalyDetectorAgent                                     │
│  - AutoFixerAgent                                           │
│  - IntelligentMonitorAgent                                  │
└─────────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────────┐
│                      Core Layer                             │
├─────────────────────────────────────────────────────────────┤
│  - LLMFactory (Provider Abstraction)                        │
│  - Config (Configuration Management)                        │
│  - Logger (Logging Infrastructure)                          │
│  - BaseAgent (Agent Base Class)                             │
└─────────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────────┐
│                   LLM Providers                             │
├─────────────────┬─────────────────┬─────────────────────────┤
│   OpenAI        │   Anthropic     │   Future: DeepSeek,     │
│   - GPT-4       │   - Claude      │   Local Models, etc.    │
└─────────────────┴─────────────────┴─────────────────────────┘
```

## Component Details

### 1. User Interfaces Layer

#### CLI (Command Line Interface)
- Built with Typer for type-safe commands
- Rich formatting for beautiful terminal output
- Supports all agent operations
- File I/O handling

#### REST API
- FastAPI-based RESTful API
- OpenAPI/Swagger documentation
- Async request handling
- CORS support for web integration

#### Python SDK
- Direct Python imports
- Async/await support
- Type hints throughout
- Pydantic models for validation

### 2. Agent Layer

All agents inherit from `BaseAgent` and follow a common pattern:

```python
class SomeAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(name="SomeAgent", **kwargs)

    async def execute(self, *args, **kwargs):
        # Agent logic
        system_prompt = self._create_system_prompt()
        user_prompt = self._create_user_prompt(...)

        result = await self._generate_response(
            prompt=user_prompt,
            system_prompt=system_prompt
        )

        return result
```

#### Basic Layer Agents

**CodeReviewAgent**
- Input: Code string, language, context
- Output: CodeReviewResult with issues, scores, recommendations
- LLM Usage: Code analysis with security focus

**TestGeneratorAgent**
- Input: Code, language, test framework
- Output: TestSuite with test cases
- LLM Usage: Test generation with edge case coverage

**LogAnalyzerAgent**
- Input: Logs, context, focus areas
- Output: LogAnalysisResult with insights and root causes
- LLM Usage: Pattern recognition and root cause analysis

#### Intermediate Layer Agents

**CICDOptimizerAgent**
- Input: Pipeline config, logs, metrics
- Output: PipelineOptimization with recommendations
- LLM Usage: Performance analysis and optimization

**DocGeneratorAgent**
- Input: Code, doc type, language
- Output: Documentation string
- LLM Usage: Technical writing and documentation

**PerformanceAnalyzerAgent**
- Input: Code, profiling data, metrics
- Output: PerformanceAnalysisResult
- LLM Usage: Performance issue detection

#### Advanced Layer Agents

**AnomalyDetectorAgent**
- Input: Metrics, baseline, context
- Output: AnomalyDetectionResult
- LLM Usage: Anomaly pattern recognition

**AutoFixerAgent**
- Input: Issue description, logs, system state
- Output: AutoFixResult with fixes
- LLM Usage: Solution generation with safety checks

**IntelligentMonitorAgent**
- Input: Metrics, logs, historical data
- Output: MonitoringAnalysisResult
- LLM Usage: Alert generation and insights

### 3. Core Layer

#### LLMFactory
Provides abstraction over multiple LLM providers:

```python
# Usage
llm = LLMFactory.create(
    provider="openai",  # or "anthropic"
    model="gpt-4-turbo-preview",
    temperature=0.7
)

response = await llm.generate(prompt, system_prompt)
```

Features:
- Provider abstraction
- Model configuration
- Instance caching
- Error handling

#### Config
Centralized configuration management:

```python
from aiops.core.config import get_config

config = get_config()
config.default_llm_provider = "anthropic"
config.enable_metrics = True
```

Features:
- Environment variable loading
- Pydantic validation
- Type safety
- Global configuration instance

#### Logger
Structured logging with loguru:

```python
from aiops.core.logger import get_logger

logger = get_logger(__name__)
logger.info("Agent started")
logger.error("Operation failed", exc_info=True)
```

Features:
- Structured logging
- File rotation
- Console and file output
- Configurable log levels

### 4. LLM Provider Layer

#### OpenAI Integration
- GPT-4 and GPT-3.5 support
- Function calling for structured output
- Streaming support (planned)

#### Anthropic Integration
- Claude 3.5 Sonnet support
- Tool use for structured output
- Long context handling

## Design Principles

### 1. Separation of Concerns
Each layer has a clear responsibility:
- UI layer handles user interaction
- Agent layer contains business logic
- Core layer provides infrastructure
- LLM layer abstracts AI providers

### 2. Modularity
- Agents are independent and reusable
- New agents can be added easily
- LLM providers are pluggable

### 3. Type Safety
- Pydantic models for all data structures
- Type hints throughout
- Runtime validation

### 4. Async-First
- All agents use async/await
- Non-blocking I/O operations
- Concurrent execution support

### 5. Error Handling
- Graceful degradation
- Informative error messages
- Fallback responses

## Data Flow

### Example: Code Review Flow

```
1. User Input
   ├─> CLI: aiops review code.py
   ├─> API: POST /api/v1/code/review
   └─> SDK: agent.execute(code="...")

2. Agent Layer
   ├─> CodeReviewAgent initialized
   ├─> System prompt created
   └─> User prompt created

3. Core Layer
   ├─> LLMFactory creates provider instance
   ├─> Configuration loaded
   └─> Logger records operation

4. LLM Provider
   ├─> API request to OpenAI/Anthropic
   ├─> Structured output requested
   └─> Response received

5. Result Processing
   ├─> Pydantic validation
   ├─> Type conversion
   └─> Error handling

6. Output
   ├─> CLI: Rich formatted output
   ├─> API: JSON response
   └─> SDK: CodeReviewResult object
```

## Extension Points

### Adding New Agents

```python
from aiops.agents.base_agent import BaseAgent

class MyCustomAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(name="MyCustomAgent", **kwargs)

    async def execute(self, input_data: str):
        # Your logic here
        result = await self._generate_response(
            prompt=f"Process: {input_data}",
            system_prompt="You are an expert..."
        )
        return result
```

### Adding New LLM Providers

```python
from aiops.core.llm_factory import BaseLLM

class NewProviderLLM(BaseLLM):
    def __init__(self, config):
        super().__init__(config)
        # Initialize provider client

    async def generate(self, prompt, system_prompt):
        # Implementation
        pass
```

### Adding New CLI Commands

```python
# In aiops/cli/main.py

@app.command()
def my_command(
    input_file: str = typer.Argument(...),
):
    """My custom command."""
    agent = MyCustomAgent()
    result = asyncio.run(agent.execute(input_file))
    console.print(result)
```

## Performance Considerations

### Caching
- LLM instances are cached
- Configuration loaded once
- Reusable agent instances

### Concurrency
- Multiple agents can run in parallel
- Async operations prevent blocking
- Batch processing support

### Resource Management
- Token usage monitoring (planned)
- Rate limiting (planned)
- Connection pooling

## Security

### API Key Management
- Environment variables
- No hardcoded secrets
- .env file support

### Input Validation
- Pydantic validation
- Type checking
- Sanitization

### Safe Operations
- Conservative auto-fix recommendations
- Risk assessment
- Rollback plans

## Future Enhancements

1. **Plugin System**: Allow third-party agents
2. **Metrics Collection**: Prometheus integration
3. **Caching Layer**: Redis for response caching
4. **Streaming Support**: Real-time response streaming
5. **Web Dashboard**: React-based UI
6. **Webhooks**: Event-driven integrations

## Conclusion

The AIOps Framework architecture is designed for:
- **Scalability**: Handle growing workloads
- **Maintainability**: Clean, organized code
- **Extensibility**: Easy to add new features
- **Reliability**: Robust error handling
- **Performance**: Async operations and caching

For more details, see the [README](README.md) and [examples](aiops/examples/).
