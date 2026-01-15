# AIOps Troubleshooting Guide

This document provides diagnostic and resolution methods for common issues in the AIOps project.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [API Related Issues](#api-related-issues)
- [Database Issues](#database-issues)
- [LLM Related Issues](#llm-related-issues)
- [Celery Worker Issues](#celery-worker-issues)
- [Performance Issues](#performance-issues)
- [Kubernetes Issues](#kubernetes-issues)
- [Monitoring and Logging](#monitoring-and-logging)

---

## Quick Diagnostics

### System Health Check

```bash
# Check API health status
curl http://localhost:8000/health

# Check readiness status
curl http://localhost:8000/ready

# View metrics
curl http://localhost:8000/metrics
```

### Kubernetes Quick Diagnostics

```bash
# View all Pod status
kubectl get pods -n aiops

# View Pod logs
kubectl logs -f deployment/aiops-api -n aiops

# View Pod resource usage
kubectl top pods -n aiops

# View Events
kubectl get events -n aiops --sort-by='.lastTimestamp'
```

---

## API Related Issues

### Issue 1: API Fails to Start

**Symptoms**:
```
Error: Could not connect to database
```

**Diagnostics**:
```bash
# Check database connection
psql $DATABASE_URL -c "SELECT 1"

# Check environment variables
env | grep DATABASE_URL
```

**Solutions**:
1. Confirm database service is running
2. Check connection string format: `postgresql://user:pass@host:port/dbname`
3. Verify network connectivity: `telnet db-host 5432`
4. Check firewall rules

### Issue 2: 401 Unauthorized

**Symptoms**:
```json
{"detail": "Could not validate credentials"}
```

**Diagnostics**:
```bash
# Test token generation
curl -X POST http://localhost:8000/api/v1/auth/token \
  -d "username=admin&password=admin"
```

**Solutions**:
1. Confirm JWT_SECRET_KEY is set
2. Check username and password
3. Confirm token format: `Bearer <token>`
4. Check if token has expired (default 60 minutes)

### Issue 3: 429 Too Many Requests

**Symptoms**:
```json
{"detail": "Rate limit exceeded"}
```

**Diagnostics**:
```bash
# Check Redis connection
redis-cli -u $REDIS_URL ping

# View current rate limit status
curl http://localhost:8000/api/v1/rate-limit-status
```

**Solutions**:
1. Reduce request frequency
2. Increase rate limit: Set `RATE_LIMIT=200`
3. Use a different API Key
4. Check if Redis is running properly

### Issue 4: 500 Internal Server Error

**Diagnostic Steps**:

```bash
# 1. View detailed logs
tail -f logs/aiops_$(date +%Y-%m-%d).log

# 2. View error logs
tail -f logs/aiops_errors_$(date +%Y-%m-%d).log

# 3. View Sentry (if configured)
# Access Sentry console to view detailed stack traces
```

**Common Causes**:
- Invalid LLM API key
- Lost database connection
- Insufficient memory
- Dependency service unavailable

---

## Database Issues

### Issue 1: Connection Pool Exhausted

**Symptoms**:
```
QueuePool limit of size 10 overflow 20 reached
```

**Diagnostics**:
```bash
# View active connection count
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity WHERE datname='aiops';"

# View long-running queries
psql $DATABASE_URL -c "
SELECT pid, now() - query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY duration DESC;
"
```

**Solutions**:
1. Increase connection pool size:
```python
engine = create_engine(
    DATABASE_URL,
    pool_size=20,  # Default 10
    max_overflow=40,  # Default 20
)
```

2. Terminate long-running queries:
```sql
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'active' AND now() - query_start > interval '5 minutes';
```

3. Add connection timeout:
```python
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
)
```

### Issue 2: Slow Queries

**Diagnostics**:
```sql
-- Enable slow query logging
ALTER DATABASE aiops SET log_min_duration_statement = 1000;  -- 1 second

-- View slowest queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

**Solutions**:
1. Add indexes
2. Optimize queries
3. Use EXPLAIN ANALYZE to analyze execution plans

### Issue 3: Database Disk Space Insufficient

**Diagnostics**:
```sql
-- View table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

**Solutions**:
1. Clean up old data (see maintenance tasks)
2. Enable automatic VACUUM
3. Increase disk space

---

## LLM Related Issues

### Issue 1: OpenAI Rate Limit

**Symptoms**:
```
Error: Rate limit exceeded
```

**Diagnostics**:
```bash
# View token usage
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/usage

# View in-app cost tracking
curl http://localhost:8000/api/v1/costs/summary
```

**Solutions**:
1. Enable automatic retry:
```python
from aiops.core.error_handler import retry_on_error

@retry_on_error(max_retries=3, backoff_factor=2.0)
async def call_llm():
    ...
```

2. Implement rate limiting:
```python
# Add delay before agent execution
import asyncio
await asyncio.sleep(1.0)  # 1 second delay
```

3. Switch to another model or provider:
```env
DEFAULT_LLM_PROVIDER=anthropic
DEFAULT_MODEL=claude-3-sonnet-20240229
```

### Issue 2: LLM Response Timeout

**Symptoms**:
```
Error: Request timed out after 30s
```

**Solutions**:
1. Increase timeout:
```python
from openai import AsyncOpenAI
client = AsyncOpenAI(timeout=60.0)  # 60 seconds
```

2. Reduce input length
3. Use a faster model

### Issue 3: Invalid API Key

**Diagnostics**:
```bash
# Test OpenAI key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Test Anthropic key
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01"
```

**Solutions**:
1. Verify API key validity
2. Check environment variable settings
3. Confirm API quota has not been exhausted

---

## Celery Worker Issues

### Issue 1: Worker Cannot Connect to Broker

**Symptoms**:
```
Error: Cannot connect to redis://localhost:6379/0
```

**Diagnostics**:
```bash
# Test Redis connection
redis-cli -u $REDIS_URL ping

# Check Redis logs
docker logs redis
```

**Solutions**:
1. Confirm Redis service is running
2. Check CELERY_BROKER_URL configuration
3. Verify network connectivity
4. Check Redis authentication configuration

### Issue 2: Task Stuck in PENDING State

**Diagnostics**:
```bash
# Check Worker status
celery -A aiops.tasks.celery_app inspect active

# Check queue length
redis-cli -u $REDIS_URL llen celery

# View Worker logs
kubectl logs deployment/aiops-worker -n aiops
```

**Solutions**:
1. Confirm Worker is started
2. Check task routing configuration
3. Increase Worker concurrency:
```bash
celery -A aiops.tasks.celery_app worker --concurrency=8
```

### Issue 3: Task Execution Failure

**Diagnostics**:
```python
# View task result
from celery.result import AsyncResult
result = AsyncResult(task_id)
print(result.status)
print(result.traceback)
```

**Solutions**:
1. View error traceback
2. Check task parameters
3. Verify dependency service availability
4. Check Worker resource usage

---

## Performance Issues

### Issue 1: Slow API Response

**Diagnostics**:
```bash
# Test endpoint response time
time curl http://localhost:8000/api/v1/agents/code-review

# View Prometheus metrics
curl http://localhost:8000/metrics | grep http_request_duration
```

**Optimization Recommendations**:
1. Enable response caching
2. Increase Worker count
3. Optimize database queries
4. Use CDN
5. Enable Gzip compression

### Issue 2: High Memory Usage

**Diagnostics**:
```bash
# View process memory usage
ps aux | grep uvicorn

# Kubernetes environment
kubectl top pods -n aiops
```

**Solutions**:
1. Increase memory limit:
```yaml
resources:
  limits:
    memory: "2Gi"
```

2. Reduce Worker concurrency
3. Enable memory profiling:
```python
import tracemalloc
tracemalloc.start()
```

### Issue 3: High CPU Usage

**Diagnostics**:
```bash
# View CPU usage
top -p $(pgrep -f uvicorn)

# Performance profiling
python -m cProfile -o profile.stats aiops/api/main.py
```

**Solutions**:
1. Horizontal scaling (increase Pod replicas)
2. Optimize CPU-intensive code
3. Use asynchronous processing
4. Enable CPU affinity

---

## Kubernetes Issues

### Issue 1: Pod CrashLoopBackOff

**Diagnostics**:
```bash
# View Pod status
kubectl describe pod <pod-name> -n aiops

# View Pod logs
kubectl logs <pod-name> -n aiops --previous
```

**Common Causes**:
1. Application startup failure
2. Configuration error
3. Health check failure
4. Insufficient resources

**Solutions**:
```bash
# Modify health check
kubectl edit deployment/aiops-api -n aiops

# Increase initial delay
initialDelaySeconds: 60
```

### Issue 2: ImagePullBackOff

**Diagnostics**:
```bash
# View detailed information
kubectl describe pod <pod-name> -n aiops
```

**Solutions**:
1. Confirm image name is correct
2. Check image registry access permissions
3. Configure imagePullSecrets:
```bash
kubectl create secret docker-registry regcred \
  --docker-server=<registry> \
  --docker-username=<username> \
  --docker-password=<password>
```

### Issue 3: HPA Not Working

**Diagnostics**:
```bash
# View HPA status
kubectl get hpa -n aiops
kubectl describe hpa aiops-api-hpa -n aiops

# Check metrics-server
kubectl get deployment metrics-server -n kube-system
```

**Solutions**:
1. Install metrics-server
2. Confirm resource requests are set
3. Check CPU/memory metrics availability

---

## Monitoring and Logging

### Enable Detailed Logging

```bash
# Set log level to DEBUG
export LOG_LEVEL=DEBUG

# Kubernetes
kubectl set env deployment/aiops-api LOG_LEVEL=DEBUG -n aiops
```

### View Structured Logs

```bash
# Parse JSON logs
tail -f logs/aiops_$(date +%Y-%m-%d).log | jq '.'

# Filter by specific trace_id
tail -f logs/aiops_$(date +%Y-%m-%d).log | jq 'select(.trace_id=="xxx")'
```

### Using Distributed Tracing

```bash
# View Jaeger UI
kubectl port-forward svc/jaeger-query 16686:16686 -n aiops

# Access http://localhost:16686
```

---

## Emergency Recovery Procedures

### Database Recovery

```bash
# 1. Stop all connections
psql $DATABASE_URL -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'aiops' AND pid <> pg_backend_pid();
"

# 2. Restore from backup
psql $DATABASE_URL < backup_latest.sql

# 3. Verify data
psql $DATABASE_URL -c "SELECT count(*) FROM users;"
```

### Rollback Deployment

```bash
# Kubernetes rollback
kubectl rollout undo deployment/aiops-api -n aiops

# View rollback status
kubectl rollout status deployment/aiops-api -n aiops
```

### Clear Redis Cache

```bash
# Clear all cache
redis-cli -u $REDIS_URL FLUSHDB

# Clear specific keys
redis-cli -u $REDIS_URL DEL "cache:*"
```

---

## Getting Help

If the issue remains unresolved:

1. **Check Logs**: `logs/aiops_errors_*.log`
2. **Check Sentry**: View error tracking
3. **Check Metrics**: Prometheus/Grafana
4. **Submit Issue**: https://github.com/markl-a/AIOps/issues

---

**Last Updated**: 2024-01-15
**Version**: 1.0.0
