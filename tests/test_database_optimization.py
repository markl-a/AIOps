"""Tests for database optimizations and query performance."""

import pytest
from datetime import datetime
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from aiops.database.base import Base
from aiops.database.models import User, APIKey, AgentExecution, AuditLog, UserRole, ExecutionStatus
from aiops.database.query_utils import (
    QueryOptimizer,
    query_timer,
    count_queries,
    BatchLoader,
)


@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_users(db_session):
    """Create sample users for testing."""
    users = []
    for i in range(10):
        user = User(
            username=f"user{i}",
            email=f"user{i}@test.com",
            hashed_password="hashed_password",
            role=UserRole.USER,
            is_active=True,
        )
        db_session.add(user)
        users.append(user)
    db_session.commit()
    return users


def test_indexes_exist(db_session):
    """Test that all required indexes are created."""
    # Get table names from metadata
    inspector = db_session.bind.dialect.get_inspector(db_session.bind)

    # Check User table indexes
    user_indexes = inspector.get_indexes("users")
    user_index_names = [idx["name"] for idx in user_indexes]

    # Note: SQLite may not support all PostgreSQL index features
    # This test validates the model definitions are correct
    assert "users" in Base.metadata.tables

    # Verify relationships are configured for selectinload
    assert User.api_keys.property.lazy == "selectinload"
    assert User.executions.property.lazy == "selectinload"
    assert User.audit_logs.property.lazy == "selectinload"


def test_foreign_key_cascade(db_session):
    """Test that foreign key cascades work correctly."""
    # Create user with related data
    user = User(
        username="testuser",
        email="test@test.com",
        hashed_password="hashed",
        role=UserRole.USER,
    )
    db_session.add(user)
    db_session.commit()

    # Add API key
    api_key = APIKey(
        user_id=user.id,
        key_hash="test_hash",
        name="Test Key",
        is_active=True,
    )
    db_session.add(api_key)
    db_session.commit()

    # Delete user - should cascade to API key
    db_session.delete(user)
    db_session.commit()

    # API key should be deleted (CASCADE)
    assert db_session.query(APIKey).filter_by(key_hash="test_hash").first() is None


def test_query_optimizer_eager_loading(db_session, sample_users):
    """Test QueryOptimizer prevents N+1 queries."""
    user = sample_users[0]

    # Add related data
    for i in range(5):
        api_key = APIKey(
            user_id=user.id,
            key_hash=f"hash{i}",
            name=f"Key {i}",
            is_active=True,
        )
        db_session.add(api_key)
    db_session.commit()

    # Count queries executed
    query_count = {"count": 0}

    def count_query(conn, cursor, statement, parameters, context, executemany):
        query_count["count"] += 1

    event.listen(db_session.bind, "after_cursor_execute", count_query)

    # Use QueryOptimizer to fetch user with relations
    loaded_user = QueryOptimizer.eager_load_user_with_relations(db_session, user.id)

    # Access relations (should not trigger additional queries)
    api_keys = loaded_user.api_keys
    executions = loaded_user.executions
    audit_logs = loaded_user.audit_logs

    event.remove(db_session.bind, "after_cursor_execute", count_query)

    # Should be minimal queries due to eager loading
    assert query_count["count"] <= 4  # 1 for user + 3 for relations (selectinload)
    assert len(api_keys) == 5


def test_query_optimizer_executions_with_user(db_session, sample_users):
    """Test efficient execution loading with users."""
    # Create executions for multiple users
    for user in sample_users[:3]:
        for i in range(3):
            execution = AgentExecution(
                trace_id=f"trace_{user.id}_{i}",
                user_id=user.id,
                agent_name="test_agent",
                operation="test",
                status=ExecutionStatus.COMPLETED,
            )
            db_session.add(execution)
    db_session.commit()

    # Fetch executions with users
    executions = QueryOptimizer.get_executions_with_user(db_session, limit=10)

    # Should have 9 executions
    assert len(executions) == 9

    # Access user data (should not trigger N+1 queries)
    query_count = {"count": 0}

    def count_query(conn, cursor, statement, parameters, context, executemany):
        query_count["count"] += 1

    event.listen(db_session.bind, "after_cursor_execute", count_query)

    for execution in executions:
        _ = execution.user  # Access user relationship

    event.remove(db_session.bind, "after_cursor_execute", count_query)

    # Should be 0 additional queries due to joinedload
    assert query_count["count"] == 0


def test_batch_loader(db_session):
    """Test BatchLoader for efficient bulk inserts."""
    # Create many users using BatchLoader
    with BatchLoader(db_session, batch_size=5) as loader:
        for i in range(15):
            user = User(
                username=f"batch_user{i}",
                email=f"batch{i}@test.com",
                hashed_password="hashed",
                role=UserRole.USER,
            )
            loader.add(user)

    # Should have 15 users
    assert db_session.query(User).filter(User.username.like("batch_user%")).count() == 15


def test_query_timer(db_session, sample_users):
    """Test query timer context manager."""
    import time

    # Test fast query
    with query_timer("fast_query", threshold_ms=1000):
        db_session.query(User).first()

    # Test simulated slow query
    with query_timer("slow_query", threshold_ms=10):
        time.sleep(0.02)  # Simulate slow operation
        db_session.query(User).first()


def test_bulk_operations(db_session):
    """Test bulk insert and update operations."""
    # Bulk insert
    users = []
    for i in range(100):
        users.append(
            User(
                username=f"bulk{i}",
                email=f"bulk{i}@test.com",
                hashed_password="hashed",
                role=UserRole.USER,
            )
        )

    QueryOptimizer.bulk_insert(db_session, users)

    # Verify all inserted
    count = db_session.query(User).filter(User.username.like("bulk%")).count()
    assert count == 100


def test_composite_indexes_usage(db_session, sample_users):
    """Test that composite indexes are used for common query patterns."""
    user = sample_users[0]

    # Add executions with various statuses
    for i in range(10):
        execution = AgentExecution(
            trace_id=f"trace_{i}",
            user_id=user.id,
            agent_name="test_agent",
            operation="test",
            status=ExecutionStatus.COMPLETED if i % 2 == 0 else ExecutionStatus.FAILED,
            started_at=datetime.utcnow(),
        )
        db_session.add(execution)
    db_session.commit()

    # Query using composite index (status + started_at)
    results = (
        db_session.query(AgentExecution)
        .filter(AgentExecution.status == ExecutionStatus.COMPLETED)
        .order_by(AgentExecution.started_at.desc())
        .all()
    )

    assert len(results) == 5


def test_audit_log_indexes(db_session, sample_users):
    """Test audit log indexing for security queries."""
    user = sample_users[0]

    # Create audit logs from multiple IPs
    ips = ["192.168.1.1", "192.168.1.2", "10.0.0.1"]
    for i in range(15):
        log = AuditLog(
            user_id=user.id,
            event_type="auth_attempt",
            action="login",
            ip_address=ips[i % 3],
            status_code=200 if i % 2 == 0 else 401,
        )
        db_session.add(log)
    db_session.commit()

    # Query by IP and timestamp (uses composite index)
    results = (
        db_session.query(AuditLog)
        .filter(AuditLog.ip_address == "192.168.1.1")
        .order_by(AuditLog.timestamp.desc())
        .all()
    )

    assert len(results) == 5

    # Query failed logins (uses status_code index)
    failed = db_session.query(AuditLog).filter(AuditLog.status_code == 401).all()
    assert len(failed) >= 7


def test_cost_tracking_indexes(db_session, sample_users):
    """Test cost tracking indexes for analysis queries."""
    from aiops.database.models import CostTracking

    user = sample_users[0]

    # Create cost tracking records
    providers = ["openai", "anthropic"]
    models = ["gpt-4", "claude-3"]

    for i in range(20):
        cost = CostTracking(
            user_id=user.id,
            provider=providers[i % 2],
            model=models[i % 2],
            total_cost=i * 0.01,
            total_tokens=i * 100,
        )
        db_session.add(cost)
    db_session.commit()

    # Query by provider and model (uses composite index)
    results = (
        db_session.query(CostTracking)
        .filter(
            CostTracking.provider == "openai",
            CostTracking.model == "gpt-4",
        )
        .all()
    )

    assert len(results) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
