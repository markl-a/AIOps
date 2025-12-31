"""Comprehensive tests for Database Query Utilities."""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch, call
from contextlib import contextmanager
from sqlalchemy.orm import Session, Query
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from aiops.database.query_utils import (
    QueryOptimizer,
    query_timer,
    log_query_plan,
    count_queries,
    BatchLoader,
)


Base = declarative_base()


class MockUser(Base):
    """Mock User model for testing."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String)
    email = Column(String)

    api_keys = relationship("MockAPIKey", back_populates="user")
    executions = relationship("MockExecution", back_populates="user")
    audit_logs = relationship("MockAuditLog", back_populates="user")


class MockAPIKey(Base):
    """Mock APIKey model."""
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    key = Column(String)

    user = relationship("MockUser", back_populates="api_keys")


class MockExecution(Base):
    """Mock Execution model."""
    __tablename__ = "executions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String)

    user = relationship("MockUser", back_populates="executions")


class MockAuditLog(Base):
    """Mock AuditLog model."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    event_type = Column(String)

    user = relationship("MockUser", back_populates="audit_logs")


@pytest.fixture
def mock_session():
    """Create a mock SQLAlchemy session."""
    session = MagicMock(spec=Session)
    return session


@pytest.fixture
def mock_query():
    """Create a mock SQLAlchemy query."""
    query = MagicMock(spec=Query)
    return query


class TestQueryOptimizer:
    """Tests for QueryOptimizer class."""

    def test_eager_load_user_with_relations(self, mock_session):
        """Test eager loading user with all relationships."""
        # Mock the query chain
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = MockUser(id=1, username="test")

        with patch("aiops.database.query_utils.User", MockUser):
            with patch("aiops.database.query_utils.selectinload") as mock_selectinload:
                result = QueryOptimizer.eager_load_user_with_relations(mock_session, 1)

                # Verify query was built with eager loading
                assert mock_session.query.called
                assert mock_query.options.called
                assert mock_query.filter.called
                assert mock_query.first.called

                # Verify selectinload was called for relationships
                assert mock_selectinload.call_count == 3

    def test_get_executions_with_user(self, mock_session):
        """Test fetching executions with user data efficiently."""
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = []

        with patch("aiops.database.query_utils.AgentExecution", MockExecution):
            with patch("aiops.database.query_utils.joinedload") as mock_joinedload:
                result = QueryOptimizer.get_executions_with_user(
                    mock_session, limit=50, offset=10, status="completed"
                )

                # Verify joinedload was used
                assert mock_joinedload.called

                # Verify filter was applied for status
                assert mock_query.filter.called

                # Verify pagination
                mock_query.limit.assert_called_with(50)
                mock_query.offset.assert_called_with(10)

    def test_get_executions_without_status_filter(self, mock_session):
        """Test fetching executions without status filter."""
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = []

        with patch("aiops.database.query_utils.AgentExecution", MockExecution):
            with patch("aiops.database.query_utils.joinedload"):
                QueryOptimizer.get_executions_with_user(mock_session)

                # Filter should not be called when no status provided
                assert not mock_query.filter.called

    def test_get_audit_logs_with_user(self, mock_session):
        """Test fetching audit logs with user data efficiently."""
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = []

        with patch("aiops.database.query_utils.AuditLog", MockAuditLog):
            with patch("aiops.database.query_utils.joinedload") as mock_joinedload:
                result = QueryOptimizer.get_audit_logs_with_user(
                    mock_session, limit=100, offset=0, event_type="login"
                )

                assert mock_joinedload.called
                assert mock_query.filter.called
                mock_query.limit.assert_called_with(100)
                mock_query.offset.assert_called_with(0)

    def test_bulk_insert(self, mock_session):
        """Test bulk insert operation."""
        objects = [MockUser(username=f"user{i}") for i in range(10)]

        QueryOptimizer.bulk_insert(mock_session, objects)

        mock_session.bulk_save_objects.assert_called_once_with(objects)
        mock_session.commit.assert_called_once()

    def test_bulk_update(self, mock_session):
        """Test bulk update operation."""
        mappings = [
            {"id": 1, "username": "updated1"},
            {"id": 2, "username": "updated2"},
        ]

        QueryOptimizer.bulk_update(mock_session, MockUser, mappings)

        mock_session.bulk_update_mappings.assert_called_once_with(MockUser, mappings)
        mock_session.commit.assert_called_once()


class TestQueryTimer:
    """Tests for query_timer context manager."""

    def test_query_timer_under_threshold(self):
        """Test query timer when execution is under threshold."""
        with patch("aiops.database.query_utils.logger") as mock_logger:
            with query_timer("test_query", threshold_ms=100):
                time.sleep(0.01)  # 10ms

            # Should log debug (under threshold)
            assert mock_logger.debug.called
            assert not mock_logger.warning.called

    def test_query_timer_over_threshold(self):
        """Test query timer when execution exceeds threshold."""
        with patch("aiops.database.query_utils.logger") as mock_logger:
            with query_timer("slow_query", threshold_ms=10):
                time.sleep(0.02)  # 20ms

            # Should log warning (over threshold)
            assert mock_logger.warning.called
            call_args = str(mock_logger.warning.call_args)
            assert "slow_query" in call_args.lower()
            assert "slow query detected" in call_args.lower()

    def test_query_timer_with_exception(self):
        """Test that query timer logs even when exception occurs."""
        with patch("aiops.database.query_utils.logger") as mock_logger:
            try:
                with query_timer("failing_query", threshold_ms=100):
                    raise ValueError("Test error")
            except ValueError:
                pass

            # Should still log the query time
            assert mock_logger.debug.called or mock_logger.warning.called

    def test_query_timer_custom_threshold(self):
        """Test query timer with custom threshold."""
        with patch("aiops.database.query_utils.logger") as mock_logger:
            with query_timer("custom_query", threshold_ms=500):
                time.sleep(0.01)

            # 10ms should be under 500ms threshold
            assert mock_logger.debug.called
            assert not mock_logger.warning.called


class TestLogQueryPlan:
    """Tests for log_query_plan function."""

    def test_log_query_plan_success(self, mock_session, mock_query):
        """Test logging query plan successfully."""
        mock_statement = Mock()
        mock_statement.compile.return_value = "SELECT * FROM users"
        mock_query.statement = mock_statement

        mock_session.bind.dialect = Mock()
        mock_session.execute.return_value.fetchone.return_value = ['{"plan": "test"}']

        with patch("aiops.database.query_utils.logger") as mock_logger:
            log_query_plan(mock_session, mock_query)

            assert mock_logger.debug.called

    def test_log_query_plan_handles_exception(self, mock_session, mock_query):
        """Test that exceptions in log_query_plan are handled gracefully."""
        mock_query.statement.compile.side_effect = Exception("Compile error")

        with patch("aiops.database.query_utils.logger") as mock_logger:
            log_query_plan(mock_session, mock_query)

            # Should log warning, not raise exception
            assert mock_logger.warning.called
            call_args = str(mock_logger.warning.call_args)
            assert "failed to get query plan" in call_args.lower()


class TestCountQueries:
    """Tests for count_queries decorator."""

    def test_count_queries_decorator(self):
        """Test that count_queries decorator counts queries."""
        mock_func = Mock(return_value="result")

        with patch("aiops.database.query_utils.logger") as mock_logger:
            with patch("aiops.database.query_utils.event") as mock_event:
                decorated = count_queries(mock_func)
                result = decorated("arg1", kwarg="value")

                assert result == "result"
                mock_func.assert_called_once_with("arg1", kwarg="value")

                # Verify event listener was registered and removed
                assert mock_event.listen.called
                assert mock_event.remove.called

    def test_count_queries_logs_count(self):
        """Test that query count is logged."""
        def test_func():
            return "result"

        with patch("aiops.database.query_utils.logger") as mock_logger:
            with patch("aiops.database.query_utils.event"):
                decorated = count_queries(test_func)
                decorated()

                # Should log the query count
                assert mock_logger.info.called
                call_args = str(mock_logger.info.call_args)
                assert "executed" in call_args.lower()
                assert "database queries" in call_args.lower()

    def test_count_queries_handles_exception(self):
        """Test that decorator handles exceptions properly."""
        def failing_func():
            raise ValueError("Test error")

        with patch("aiops.database.query_utils.event"):
            decorated = count_queries(failing_func)

            with pytest.raises(ValueError):
                decorated()

            # Event listener should still be removed even on exception
            # (tested by no hanging listeners)


class TestBatchLoader:
    """Tests for BatchLoader class."""

    def test_batch_loader_initialization(self, mock_session):
        """Test batch loader initialization."""
        loader = BatchLoader(mock_session, batch_size=50)

        assert loader.session == mock_session
        assert loader.batch_size == 50
        assert loader._batch == []

    def test_batch_loader_add_single_item(self, mock_session):
        """Test adding a single item doesn't trigger flush."""
        loader = BatchLoader(mock_session, batch_size=10)

        obj = MockUser(username="test")
        loader.add(obj)

        assert len(loader._batch) == 1
        assert not mock_session.bulk_save_objects.called

    def test_batch_loader_auto_flush_on_batch_size(self, mock_session):
        """Test that batch auto-flushes when batch size is reached."""
        loader = BatchLoader(mock_session, batch_size=3)

        loader.add(MockUser(username="user1"))
        loader.add(MockUser(username="user2"))
        assert not mock_session.bulk_save_objects.called

        loader.add(MockUser(username="user3"))

        # Should auto-flush when batch size reached
        assert mock_session.bulk_save_objects.called
        assert mock_session.commit.called
        assert len(loader._batch) == 0

    def test_batch_loader_manual_flush(self, mock_session):
        """Test manual flush."""
        loader = BatchLoader(mock_session, batch_size=10)

        loader.add(MockUser(username="user1"))
        loader.add(MockUser(username="user2"))

        loader.flush()

        mock_session.bulk_save_objects.assert_called_once()
        assert len(loader._batch) == 0

    def test_batch_loader_flush_empty_batch(self, mock_session):
        """Test flushing empty batch does nothing."""
        loader = BatchLoader(mock_session, batch_size=10)

        loader.flush()

        assert not mock_session.bulk_save_objects.called

    def test_batch_loader_context_manager(self, mock_session):
        """Test batch loader as context manager."""
        with BatchLoader(mock_session, batch_size=10) as loader:
            loader.add(MockUser(username="user1"))
            loader.add(MockUser(username="user2"))

        # Should auto-flush on exit
        assert mock_session.bulk_save_objects.called
        assert mock_session.commit.called

    def test_batch_loader_context_manager_with_exception(self, mock_session):
        """Test batch loader context manager handles exceptions."""
        try:
            with BatchLoader(mock_session, batch_size=10) as loader:
                loader.add(MockUser(username="user1"))
                raise ValueError("Test error")
        except ValueError:
            pass

        # Should not flush on exception
        assert not mock_session.bulk_save_objects.called

    def test_batch_loader_large_batch(self, mock_session):
        """Test batch loader with large number of items."""
        loader = BatchLoader(mock_session, batch_size=5)

        for i in range(23):
            loader.add(MockUser(username=f"user{i}"))

        # Should have flushed 4 times (5 + 5 + 5 + 5 = 20 items)
        # 3 items remaining in batch
        assert mock_session.bulk_save_objects.call_count == 4
        assert len(loader._batch) == 3

        loader.flush()

        # Final flush
        assert mock_session.bulk_save_objects.call_count == 5


class TestEdgeCases:
    """Edge case tests."""

    def test_query_optimizer_with_none_session(self):
        """Test query optimizer with None session."""
        with pytest.raises(AttributeError):
            QueryOptimizer.eager_load_user_with_relations(None, 1)

    def test_batch_loader_with_zero_batch_size(self, mock_session):
        """Test batch loader with zero batch size."""
        loader = BatchLoader(mock_session, batch_size=0)
        loader.add(MockUser(username="test"))

        # Should flush immediately with batch_size=0
        # (0 >= 0 is True, so it should flush)
        assert mock_session.bulk_save_objects.called

    def test_batch_loader_with_negative_batch_size(self, mock_session):
        """Test batch loader with negative batch size."""
        loader = BatchLoader(mock_session, batch_size=-1)
        loader.add(MockUser(username="test"))

        # Should flush immediately with negative batch_size
        assert mock_session.bulk_save_objects.called

    def test_query_timer_very_fast_query(self):
        """Test query timer with extremely fast query."""
        with patch("aiops.database.query_utils.logger") as mock_logger:
            with query_timer("instant_query", threshold_ms=1000):
                pass  # Nearly instant

            # Should still log without errors
            assert mock_logger.debug.called

    def test_bulk_operations_with_empty_list(self, mock_session):
        """Test bulk operations with empty lists."""
        QueryOptimizer.bulk_insert(mock_session, [])
        QueryOptimizer.bulk_update(mock_session, MockUser, [])

        # Should still call the methods
        assert mock_session.bulk_save_objects.called
        assert mock_session.bulk_update_mappings.called


class TestPerformanceOptimization:
    """Tests for performance optimization features."""

    def test_eager_loading_prevents_n_plus_one(self, mock_session):
        """Test that eager loading is configured to prevent N+1 queries."""
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        with patch("aiops.database.query_utils.User", MockUser):
            with patch("aiops.database.query_utils.selectinload") as mock_selectinload:
                QueryOptimizer.eager_load_user_with_relations(mock_session, 1)

                # Verify all relationships are eagerly loaded
                assert mock_selectinload.call_count >= 3

    def test_bulk_operations_efficiency(self, mock_session):
        """Test that bulk operations use efficient SQLAlchemy methods."""
        objects = [MockUser(username=f"user{i}") for i in range(100)]

        QueryOptimizer.bulk_insert(mock_session, objects)

        # Should use bulk_save_objects, not individual inserts
        mock_session.bulk_save_objects.assert_called_once()

        # Should commit only once for all objects
        assert mock_session.commit.call_count == 1

    def test_batch_loader_minimizes_commits(self, mock_session):
        """Test that batch loader minimizes number of commits."""
        loader = BatchLoader(mock_session, batch_size=10)

        # Add 25 items
        for i in range(25):
            loader.add(MockUser(username=f"user{i}"))

        loader.flush()

        # Should commit 3 times (10 + 10 + 5)
        assert mock_session.commit.call_count == 3
