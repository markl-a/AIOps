"""Database query utilities and helpers for preventing N+1 queries."""

from typing import List, Type, TypeVar, Optional
from sqlalchemy.orm import Session, Query, joinedload, selectinload, subqueryload
from sqlalchemy.ext.declarative import DeclarativeMeta
from contextlib import contextmanager
import time
from loguru import logger

T = TypeVar("T", bound=DeclarativeMeta)


class QueryOptimizer:
    """Helper class for optimizing database queries and preventing N+1 issues."""

    @staticmethod
    def eager_load_user_with_relations(session: Session, user_id: int):
        """
        Fetch user with all related data in a single query to prevent N+1.

        Args:
            session: Database session
            user_id: User ID to fetch

        Returns:
            User object with eagerly loaded relationships
        """
        from aiops.database.models import User

        return (
            session.query(User)
            .options(
                selectinload(User.api_keys),
                selectinload(User.executions),
                selectinload(User.audit_logs),
            )
            .filter(User.id == user_id)
            .first()
        )

    @staticmethod
    def get_executions_with_user(
        session: Session,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None,
    ):
        """
        Fetch executions with user data efficiently (prevent N+1).

        Args:
            session: Database session
            limit: Maximum number of results
            offset: Offset for pagination
            status: Optional status filter

        Returns:
            List of executions with eagerly loaded user data
        """
        from aiops.database.models import AgentExecution

        query = (
            session.query(AgentExecution)
            .options(joinedload(AgentExecution.user))
            .order_by(AgentExecution.started_at.desc())
        )

        if status:
            query = query.filter(AgentExecution.status == status)

        return query.limit(limit).offset(offset).all()

    @staticmethod
    def get_audit_logs_with_user(
        session: Session,
        limit: int = 100,
        offset: int = 0,
        event_type: Optional[str] = None,
    ):
        """
        Fetch audit logs with user data efficiently (prevent N+1).

        Args:
            session: Database session
            limit: Maximum number of results
            offset: Offset for pagination
            event_type: Optional event type filter

        Returns:
            List of audit logs with eagerly loaded user data
        """
        from aiops.database.models import AuditLog

        query = (
            session.query(AuditLog)
            .options(joinedload(AuditLog.user))
            .order_by(AuditLog.timestamp.desc())
        )

        if event_type:
            query = query.filter(AuditLog.event_type == event_type)

        return query.limit(limit).offset(offset).all()

    @staticmethod
    def bulk_insert(session: Session, objects: List[T]):
        """
        Bulk insert objects efficiently.

        Args:
            session: Database session
            objects: List of objects to insert
        """
        session.bulk_save_objects(objects)
        session.commit()

    @staticmethod
    def bulk_update(session: Session, model: Type[T], mappings: List[dict]):
        """
        Bulk update objects efficiently.

        Args:
            session: Database session
            model: Model class
            mappings: List of dictionaries with id and fields to update
        """
        session.bulk_update_mappings(model, mappings)
        session.commit()


@contextmanager
def query_timer(query_name: str, threshold_ms: float = 100.0):
    """
    Context manager to time database queries and log slow queries.

    Args:
        query_name: Name/description of the query
        threshold_ms: Threshold in milliseconds to log as slow query

    Example:
        with query_timer("fetch_users"):
            users = session.query(User).all()
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration_ms = (time.time() - start_time) * 1000
        if duration_ms > threshold_ms:
            logger.warning(
                f"Slow query detected: {query_name} took {duration_ms:.2f}ms "
                f"(threshold: {threshold_ms}ms)"
            )
        else:
            logger.debug(f"Query {query_name} completed in {duration_ms:.2f}ms")


def log_query_plan(session: Session, query: Query):
    """
    Log the EXPLAIN plan for a query (PostgreSQL).

    Args:
        session: Database session
        query: SQLAlchemy query object

    Note: This is for debugging purposes only
    """
    try:
        # Get the compiled query
        compiled = query.statement.compile(
            dialect=session.bind.dialect, compile_kwargs={"literal_binds": True}
        )

        # Execute EXPLAIN
        explain_query = f"EXPLAIN (FORMAT JSON) {compiled}"
        result = session.execute(explain_query).fetchone()

        logger.debug(f"Query plan:\n{result[0]}")
    except Exception as e:
        logger.warning(f"Failed to get query plan: {e}")


def count_queries(func):
    """
    Decorator to count and log database queries executed by a function.

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """
    def wrapper(*args, **kwargs):
        from sqlalchemy import event
        from sqlalchemy.engine import Engine

        query_count = {"count": 0}

        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            query_count["count"] += 1

        # Register event listener
        event.listen(Engine, "after_cursor_execute", receive_after_cursor_execute)

        try:
            result = func(*args, **kwargs)
            logger.info(f"{func.__name__} executed {query_count['count']} database queries")
            return result
        finally:
            # Remove event listener
            event.remove(Engine, "after_cursor_execute", receive_after_cursor_execute)

    return wrapper


class BatchLoader:
    """Helper for batching database operations to prevent N+1 queries."""

    def __init__(self, session: Session, batch_size: int = 100):
        """
        Initialize batch loader.

        Args:
            session: Database session
            batch_size: Size of each batch
        """
        self.session = session
        self.batch_size = batch_size
        self._batch = []

    def add(self, obj):
        """Add object to batch."""
        self._batch.append(obj)
        if len(self._batch) >= self.batch_size:
            self.flush()

    def flush(self):
        """Flush current batch to database."""
        if self._batch:
            self.session.bulk_save_objects(self._batch)
            self.session.commit()
            logger.debug(f"Batch inserted {len(self._batch)} objects")
            self._batch = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.flush()
