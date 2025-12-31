"""Database models for AIOps."""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
    JSON,
    ForeignKey,
    Index,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship, selectinload
import enum

from aiops.database.base import Base


class UserRole(str, enum.Enum):
    """User role enumeration."""

    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"


class ExecutionStatus(str, enum.Enum):
    """Agent execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class User(Base):
    """User model."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow(), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.utcnow(), onupdate=lambda: datetime.utcnow())
    last_login = Column(DateTime, nullable=True)

    # Relationships with lazy loading (use selectinload when querying to prevent N+1 queries)
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    executions = relationship("AgentExecution", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        # Composite index for common query pattern: active users with specific role
        Index("idx_user_active_role", "is_active", "role"),
        # Index for last login time queries
        Index("idx_user_last_login", "last_login"),
    )

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


class APIKey(Base):
    """API Key model."""

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow(), nullable=False)
    expires_at = Column(DateTime, nullable=True, index=True)
    last_used_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="api_keys")

    __table_args__ = (
        Index("idx_api_key_user", "user_id", "is_active"),
        # Index for checking expired keys
        Index("idx_api_key_expires", "expires_at", "is_active"),
    )

    def __repr__(self):
        return f"<APIKey(id={self.id}, name='{self.name}', user_id={self.user_id})>"


class AgentExecution(Base):
    """Agent execution tracking model."""

    __tablename__ = "agent_executions"

    id = Column(Integer, primary_key=True, index=True)
    trace_id = Column(String(100), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    agent_name = Column(String(100), nullable=False, index=True)
    operation = Column(String(100), nullable=False)
    status = Column(SQLEnum(ExecutionStatus), default=ExecutionStatus.PENDING, nullable=False, index=True)

    # Input/Output
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)

    # Timing
    started_at = Column(DateTime, default=lambda: datetime.utcnow(), nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True, index=True)
    duration_ms = Column(Float, nullable=True)

    # LLM Usage
    llm_provider = Column(String(50), nullable=True, index=True)
    llm_model = Column(String(100), nullable=True)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    llm_cost = Column(Float, default=0.0)

    # Metadata
    execution_metadata = Column(JSON, nullable=True)

    # Relationships
    user = relationship("User", back_populates="executions")

    __table_args__ = (
        Index("idx_execution_user_agent", "user_id", "agent_name"),
        Index("idx_execution_status_created", "status", "started_at"),
        Index("idx_execution_trace", "trace_id"),
        # Index for time-range queries (e.g., last 24 hours)
        Index("idx_execution_started", "started_at"),
        # Index for filtering by status and completion
        Index("idx_execution_status_completed", "status", "completed_at"),
        # Index for LLM cost analysis
        Index("idx_execution_provider_model", "llm_provider", "llm_model"),
    )

    def __repr__(self):
        return f"<AgentExecution(id={self.id}, agent='{self.agent_name}', status='{self.status}')>"


class AuditLog(Base):
    """Audit log model."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.utcnow(), nullable=False, index=True)
    trace_id = Column(String(100), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Event details
    event_type = Column(String(50), nullable=False, index=True)  # e.g., api_request, agent_execution, auth_attempt
    action = Column(String(100), nullable=False, index=True)  # e.g., create, read, update, delete
    resource_type = Column(String(50), nullable=True, index=True)  # e.g., user, api_key, agent
    resource_id = Column(String(100), nullable=True)

    # Request details
    ip_address = Column(String(50), nullable=True, index=True)
    user_agent = Column(String(255), nullable=True)
    endpoint = Column(String(255), nullable=True)
    method = Column(String(10), nullable=True)
    status_code = Column(Integer, nullable=True, index=True)

    # Additional data
    details = Column(JSON, nullable=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("idx_audit_timestamp", "timestamp"),
        Index("idx_audit_user_event", "user_id", "event_type"),
        Index("idx_audit_trace", "trace_id"),
        # Index for security audit queries by IP
        Index("idx_audit_ip_timestamp", "ip_address", "timestamp"),
        # Index for filtering by event type and timestamp (e.g., failed logins in last hour)
        Index("idx_audit_event_timestamp", "event_type", "timestamp"),
        # Index for filtering by status code (e.g., all 4xx/5xx errors)
        Index("idx_audit_status_timestamp", "status_code", "timestamp"),
    )

    def __repr__(self):
        return f"<AuditLog(id={self.id}, event_type='{self.event_type}', action='{self.action}')>"


class CostTracking(Base):
    """Cost tracking model for LLM usage."""

    __tablename__ = "cost_tracking"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.utcnow(), nullable=False, index=True)
    trace_id = Column(String(100), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # LLM details
    provider = Column(String(50), nullable=False, index=True)
    model = Column(String(100), nullable=False, index=True)

    # Token usage
    prompt_tokens = Column(Integer, default=0, nullable=False)
    completion_tokens = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)

    # Cost calculation
    prompt_cost = Column(Float, default=0.0, nullable=False)
    completion_cost = Column(Float, default=0.0, nullable=False)
    total_cost = Column(Float, default=0.0, nullable=False)

    # Context
    agent_name = Column(String(100), nullable=True, index=True)
    operation = Column(String(100), nullable=True)

    # Additional metadata
    cost_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_cost_timestamp", "timestamp"),
        Index("idx_cost_user_provider", "user_id", "provider"),
        Index("idx_cost_agent", "agent_name"),
        # Index for cost analysis by provider and model
        Index("idx_cost_provider_model", "provider", "model", "timestamp"),
        # Index for user cost aggregation
        Index("idx_cost_user_timestamp", "user_id", "timestamp"),
    )

    def __repr__(self):
        return f"<CostTracking(id={self.id}, provider='{self.provider}', cost={self.total_cost})>"


class SystemMetric(Base):
    """System metrics model."""

    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.utcnow(), nullable=False, index=True)

    # Metric details
    metric_name = Column(String(100), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(50), nullable=True)

    # Dimensions/Tags
    tags = Column(JSON, nullable=True)  # e.g., {"environment": "production", "service": "api"}

    # Additional data
    metric_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        # Composite index for querying metrics by name and time range
        Index("idx_metric_name_timestamp", "metric_name", "timestamp"),
        # Index for time-based cleanup operations
        Index("idx_metric_timestamp", "timestamp"),
    )

    def __repr__(self):
        return f"<SystemMetric(id={self.id}, name='{self.metric_name}', value={self.metric_value})>"


class Configuration(Base):
    """Configuration storage model."""

    __tablename__ = "configurations"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)
    is_secret = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow(), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.utcnow(), onupdate=lambda: datetime.utcnow())
    updated_by = Column(String(100), nullable=True)

    __table_args__ = (
        # Index for filtering secret configurations
        Index("idx_config_is_secret", "is_secret"),
        # Index for recently updated configurations
        Index("idx_config_updated", "updated_at"),
    )

    def __repr__(self):
        return f"<Configuration(key='{self.key}', is_secret={self.is_secret})>"
