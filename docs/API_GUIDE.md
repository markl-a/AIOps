# AIOps API Guide

Complete API reference for the AIOps platform.

## Overview

The AIOps API provides RESTful endpoints for:
- Executing AI agents for various DevOps tasks
- Managing LLM providers and configurations
- Monitoring system health and metrics
- Handling webhooks from external services

**Base URL**: `http://localhost:8000/api/v1`

## Authentication

### API Key Authentication

Include your API key in the request header:

```bash
curl -H "X-API-Key: your_api_key_here" \
     http://localhost:8000/api/v1/agents
```

### JWT Authentication

1. Obtain a token:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username": "user", "password": "pass"}'
```

2. Use the token:
```bash
curl -H "Authorization: Bearer your_jwt_token" \
     http://localhost:8000/api/v1/agents
```

## Rate Limiting

| Tier | Requests/minute | Burst |
|------|-----------------|-------|
| Free | 50 | 10 |
| Basic | 200 | 50 |
| Pro | 500 | 100 |
| Enterprise | 2000 | 500 |

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Unix timestamp when limit resets

## Endpoints

### Health Check

#### GET /health

Check API health status.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:00:00Z"
}
```

### Agents

#### GET /api/v1/agents

List all available agents.

**Response:**
```json
{
  "agents": [
    {
      "name": "code_reviewer",
      "description": "AI-powered code review",
      "operations": ["review", "analyze", "suggest"]
    },
    {
      "name": "security_scanner",
      "description": "Security vulnerability detection",
      "operations": ["scan", "audit"]
    }
  ]
}
```

#### POST /api/v1/agents/execute

Execute an agent operation.

**Request:**
```json
{
  "agent": "code_reviewer",
  "operation": "review",
  "input": {
    "code": "def hello(): print('world')",
    "language": "python"
  },
  "options": {
    "model": "gpt-4",
    "max_tokens": 2000
  }
}
```

**Response:**
```json
{
  "trace_id": "abc123-def456",
  "status": "completed",
  "result": {
    "review": "The code is simple and functional...",
    "suggestions": [...],
    "score": 85
  },
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 300,
    "cost": 0.015
  }
}
```

#### POST /api/v1/agents/batch

Execute batch agent operations.

**Request:**
```json
{
  "agent": "code_reviewer",
  "operation": "review",
  "items": [
    {"code": "def foo(): pass", "file": "foo.py"},
    {"code": "def bar(): pass", "file": "bar.py"}
  ]
}
```

### LLM Management

#### GET /api/v1/llm/providers

List configured LLM providers.

**Response:**
```json
{
  "providers": [
    {
      "name": "openai",
      "models": ["gpt-4", "gpt-3.5-turbo"],
      "status": "active",
      "priority": 1
    },
    {
      "name": "anthropic",
      "models": ["claude-3-opus", "claude-3-sonnet"],
      "status": "active",
      "priority": 2
    }
  ]
}
```

#### POST /api/v1/llm/complete

Direct LLM completion (for advanced use).

**Request:**
```json
{
  "provider": "openai",
  "model": "gpt-4",
  "messages": [
    {"role": "user", "content": "Hello, how are you?"}
  ],
  "temperature": 0.7,
  "max_tokens": 500
}
```

### Analytics

#### GET /api/v1/analytics/usage

Get usage statistics.

**Query Parameters:**
- `start_date`: Start date (ISO format)
- `end_date`: End date (ISO format)
- `group_by`: Group by field (agent, user, model)

**Response:**
```json
{
  "period": {
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-01-15T00:00:00Z"
  },
  "summary": {
    "total_requests": 1500,
    "total_tokens": 2500000,
    "total_cost": 125.50
  },
  "by_agent": {
    "code_reviewer": {"requests": 500, "cost": 45.00},
    "security_scanner": {"requests": 300, "cost": 30.00}
  }
}
```

#### GET /api/v1/analytics/cost

Get cost breakdown.

**Response:**
```json
{
  "total_cost": 125.50,
  "by_provider": {
    "openai": 100.00,
    "anthropic": 25.50
  },
  "by_model": {
    "gpt-4": 80.00,
    "gpt-3.5-turbo": 20.00,
    "claude-3-sonnet": 25.50
  }
}
```

### Webhooks

#### POST /api/v1/webhooks/github

Handle GitHub webhook events.

**Headers:**
- `X-GitHub-Event`: Event type
- `X-Hub-Signature-256`: HMAC signature

**Supported Events:**
- `push`: Code push events
- `pull_request`: PR events
- `issues`: Issue events

#### POST /api/v1/webhooks/gitlab

Handle GitLab webhook events.

#### POST /api/v1/webhooks/jira

Handle Jira webhook events.

### Notifications

#### POST /api/v1/notifications/send

Send a notification.

**Request:**
```json
{
  "channel": "slack",
  "target": "#alerts",
  "message": "Deployment completed successfully",
  "severity": "info"
}
```

## Error Responses

### Error Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "field": "code",
      "issue": "Required field missing"
    }
  },
  "trace_id": "abc123-def456"
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Invalid input |
| `UNAUTHORIZED` | 401 | Missing/invalid auth |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMITED` | 429 | Rate limit exceeded |
| `LLM_ERROR` | 502 | LLM provider error |
| `INTERNAL_ERROR` | 500 | Internal server error |

## SDKs and Examples

### Python SDK

```python
from aiops import AIOpsClient

client = AIOpsClient(api_key="your_key")

# Execute code review
result = client.agents.execute(
    agent="code_reviewer",
    operation="review",
    code=open("app.py").read()
)

print(result.review)
```

### cURL Examples

```bash
# Health check
curl http://localhost:8000/health

# List agents
curl -H "X-API-Key: $API_KEY" \
     http://localhost:8000/api/v1/agents

# Execute agent
curl -X POST \
     -H "X-API-Key: $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"agent":"code_reviewer","operation":"review","input":{"code":"..."}}' \
     http://localhost:8000/api/v1/agents/execute
```

## Best Practices

1. **Use Async Execution**: For long-running tasks, use the async endpoint
2. **Handle Rate Limits**: Implement exponential backoff
3. **Cache Results**: Use semantic caching for similar requests
4. **Monitor Usage**: Track token usage and costs
5. **Secure Webhooks**: Validate webhook signatures

## Changelog

### v1.0.0 (2024-01-15)
- Initial API release
- 29 AI agents available
- Multi-LLM provider support
- Webhook integrations
