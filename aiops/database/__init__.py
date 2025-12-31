"""Database module for AIOps."""

from aiops.database.base import Base, get_db, init_db, close_db, get_db_manager
from aiops.database.models import (
    User,
    APIKey,
    AgentExecution,
    AuditLog,
    CostTracking,
    SystemMetric,
    Configuration,
    UserRole,
    ExecutionStatus,
)
from aiops.database.query_utils import (
    QueryOptimizer,
    query_timer,
    log_query_plan,
    count_queries,
    BatchLoader,
)

__all__ = [
    "Base",
    "get_db",
    "init_db",
    "close_db",
    "get_db_manager",
    "User",
    "APIKey",
    "AgentExecution",
    "AuditLog",
    "CostTracking",
    "SystemMetric",
    "Configuration",
    "UserRole",
    "ExecutionStatus",
    "QueryOptimizer",
    "query_timer",
    "log_query_plan",
    "count_queries",
    "BatchLoader",
]
