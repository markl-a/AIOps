# Database Optimization Quick Reference

## Common Patterns

### Fetch User with Relations (Prevent N+1)
```python
from aiops.database import QueryOptimizer

# ✅ GOOD - Single optimized query
user = QueryOptimizer.eager_load_user_with_relations(session, user_id)
api_keys = user.api_keys       # No additional query
executions = user.executions   # No additional query

# ❌ BAD - N+1 queries
user = session.query(User).get(user_id)
api_keys = user.api_keys       # Triggers query!
executions = user.executions   # Triggers query!
```

### Fetch Executions with Users
```python
from aiops.database import QueryOptimizer

# ✅ GOOD - Efficient join
executions = QueryOptimizer.get_executions_with_user(
    session, limit=100, status="completed"
)
for exec in executions:
    print(exec.user.username)  # No additional queries

# ❌ BAD - N+1 queries
executions = session.query(AgentExecution).all()
for exec in executions:
    print(exec.user.username)  # Query for each execution!
```

### Bulk Insert
```python
from aiops.database import BatchLoader

# ✅ GOOD - Batch insert
with BatchLoader(session, batch_size=100) as loader:
    for data in items:
        loader.add(MyModel(**data))

# ❌ BAD - Individual inserts
for data in items:
    session.add(MyModel(**data))
    session.commit()  # Too many commits!
```

### Time Queries
```python
from aiops.database import query_timer

# ✅ GOOD - Monitor performance
with query_timer("user_search", threshold_ms=100):
    users = session.query(User).filter(...).all()
```

### Count Queries (Debug N+1)
```python
from aiops.database import count_queries

@count_queries
def get_user_data(user_id):
    user = session.query(User).get(user_id)
    # ... more operations
    return user
# Logs: "get_user_data executed X queries"
```

## Environment Variables

```bash
# Connection Pool
DB_POOL_SIZE=20              # Base connections (default: 20 prod, 5 dev)
DB_MAX_OVERFLOW=40           # Additional connections (default: 40 prod, 10 dev)
DB_POOL_TIMEOUT=30           # Wait time in seconds
DB_POOL_RECYCLE=3600         # Recycle after 1 hour

# Debugging
DB_ECHO=false                # Log all SQL (dev only)
DB_ECHO_POOL=false           # Log pool events
```

## Pool Monitoring

```python
from aiops.database import get_db_manager

db = get_db_manager()
stats = db.get_pool_stats()

# Check for issues
if stats['overflow'] > 0:
    print("⚠️ Pool overflow - consider increasing pool size")
if stats['total_invalidations'] > 10:
    print("⚠️ High invalidation rate - check DB connection")
```

## Index Usage

### Single Column Indexes
```python
# These columns have indexes - efficient to query
User.role
User.is_active
User.last_login
APIKey.is_active
APIKey.expires_at
AgentExecution.status
AgentExecution.started_at
AgentExecution.llm_provider
AuditLog.ip_address
AuditLog.status_code
```

### Composite Indexes (Use Together)
```python
# Query these together for best performance
User: (is_active, role)
APIKey: (expires_at, is_active)
AgentExecution: (status, started_at)
AgentExecution: (status, completed_at)
AgentExecution: (llm_provider, llm_model)
AuditLog: (ip_address, timestamp)
AuditLog: (event_type, timestamp)
CostTracking: (provider, model, timestamp)
```

## Common Queries (Optimized)

### Get Active Users by Role
```python
# Uses composite index: (is_active, role)
users = session.query(User).filter(
    User.is_active == True,
    User.role == UserRole.ADMIN
).all()
```

### Get Recent Executions by Status
```python
# Uses composite index: (status, started_at)
executions = session.query(AgentExecution).filter(
    AgentExecution.status == ExecutionStatus.COMPLETED
).order_by(
    AgentExecution.started_at.desc()
).limit(100).all()
```

### Find Failed Logins from IP
```python
# Uses composite index: (ip_address, timestamp)
logs = session.query(AuditLog).filter(
    AuditLog.ip_address == "192.168.1.1",
    AuditLog.status_code == 401
).order_by(
    AuditLog.timestamp.desc()
).limit(50).all()
```

### Get Cost by Provider/Model
```python
# Uses composite index: (provider, model, timestamp)
from sqlalchemy import func
cost = session.query(
    func.sum(CostTracking.total_cost)
).filter(
    CostTracking.provider == "openai",
    CostTracking.model == "gpt-4"
).scalar()
```

## Migration

```bash
# Apply optimizations
alembic upgrade head

# Rollback if needed
alembic downgrade 002_add_indexes
```

## Testing

```bash
# Run all optimization tests
pytest tests/test_database_optimization.py -v

# Run specific test
pytest tests/test_database_optimization.py::test_query_optimizer_eager_loading
```

## Troubleshooting

### Pool Exhausted Error
```
QueuePool limit of size X overflow Y reached
```
**Fix**: Increase pool size
```bash
export DB_POOL_SIZE=30
export DB_MAX_OVERFLOW=50
```

### Slow Queries
```
Slow query detected (1234ms): SELECT ...
```
**Fix**:
1. Add missing index
2. Use eager loading
3. Check query plan: `log_query_plan(session, query)`

### N+1 Queries
```
get_data executed 101 queries  # Should be 1-2!
```
**Fix**:
1. Use `QueryOptimizer` methods
2. Add `lazy="selectinload"` to relationships
3. Use explicit `joinedload()` or `selectinload()`

## Metrics to Monitor

```python
# Prometheus metrics
aiops_db_queries_total          # Total queries
aiops_db_query_duration_seconds # Query time
aiops_db_connections_active     # Active connections
aiops_db_connections_total      # Pool size
```

## Best Practices

✅ **DO**:
- Use `QueryOptimizer` for related data
- Use `BatchLoader` for bulk operations
- Monitor pool stats in production
- Add indexes for new query patterns
- Use `query_timer` to identify slow queries

❌ **DON'T**:
- Access relationships in loops without eager loading
- Insert records one at a time in large batches
- Ignore slow query warnings
- Add unnecessary indexes
- Leave sessions open for extended periods

## Files Reference

- **Models**: `/home/user/AIOps/aiops/database/models.py`
- **Connection**: `/home/user/AIOps/aiops/database/base.py`
- **Utilities**: `/home/user/AIOps/aiops/database/query_utils.py`
- **Migration**: `/home/user/AIOps/aiops/database/migrations/versions/003_optimize_indexes_and_fks.py`
- **Tests**: `/home/user/AIOps/tests/test_database_optimization.py`
- **Full Docs**: `/home/user/AIOps/docs/DATABASE_OPTIMIZATION.md`
- **Summary**: `/home/user/AIOps/DATABASE_FIXES_SUMMARY.md`
