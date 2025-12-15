"""Add performance indexes for database optimization.

Revision ID: 002_add_indexes
Revises: 001_initial
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_add_indexes'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade():
    """Add performance indexes."""

    # ==================== Agent Executions Indexes ====================

    # Index for agent type queries (commonly filtered)
    op.create_index(
        'idx_agent_exec_agent_name_status',
        'agent_executions',
        ['agent_name', 'status'],
        postgresql_concurrently=True,
    )

    # Index for time-based queries
    op.create_index(
        'idx_agent_exec_started_at',
        'agent_executions',
        ['started_at'],
        postgresql_concurrently=True,
    )

    # Composite index for user activity queries
    op.create_index(
        'idx_agent_exec_user_started',
        'agent_executions',
        ['user_id', 'started_at'],
        postgresql_concurrently=True,
    )

    # Index for cost analysis queries
    op.create_index(
        'idx_agent_exec_llm_cost',
        'agent_executions',
        ['llm_provider', 'llm_model', 'llm_cost'],
        postgresql_concurrently=True,
    )

    # ==================== Audit Logs Indexes ====================

    # Index for audit log queries by action
    op.create_index(
        'idx_audit_action_timestamp',
        'audit_logs',
        ['action', 'timestamp'],
        postgresql_concurrently=True,
    )

    # Index for resource queries
    op.create_index(
        'idx_audit_resource',
        'audit_logs',
        ['resource_type', 'resource_id'],
        postgresql_concurrently=True,
    )

    # Index for IP-based analysis
    op.create_index(
        'idx_audit_ip_timestamp',
        'audit_logs',
        ['ip_address', 'timestamp'],
        postgresql_concurrently=True,
    )

    # ==================== Cost Tracking Indexes ====================

    # Index for date range queries
    op.create_index(
        'idx_cost_date_range',
        'cost_tracking',
        ['timestamp', 'provider'],
        postgresql_concurrently=True,
    )

    # Index for model cost analysis
    op.create_index(
        'idx_cost_model_analysis',
        'cost_tracking',
        ['model', 'total_cost'],
        postgresql_concurrently=True,
    )

    # Composite index for user cost queries
    op.create_index(
        'idx_cost_user_timestamp',
        'cost_tracking',
        ['user_id', 'timestamp'],
        postgresql_concurrently=True,
    )

    # ==================== System Metrics Indexes ====================

    # Index for metric queries with tags
    op.create_index(
        'idx_metrics_name_time',
        'system_metrics',
        ['metric_name', 'timestamp'],
        postgresql_concurrently=True,
    )

    # Partial index for recent metrics (last 24 hours)
    # Note: This uses a specific timestamp, adjust as needed
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_metrics_recent
        ON system_metrics (metric_name, timestamp DESC)
        WHERE timestamp > NOW() - INTERVAL '24 hours'
    """)

    # ==================== API Keys Indexes ====================

    # Index for key expiration queries
    op.create_index(
        'idx_api_keys_expires',
        'api_keys',
        ['expires_at'],
        postgresql_where=sa.text('is_active = true'),
        postgresql_concurrently=True,
    )

    # ==================== Users Indexes ====================

    # Index for login queries
    op.create_index(
        'idx_users_login',
        'users',
        ['email', 'is_active'],
        postgresql_concurrently=True,
    )

    # Index for role-based queries
    op.create_index(
        'idx_users_role',
        'users',
        ['role', 'is_active'],
        postgresql_concurrently=True,
    )


def downgrade():
    """Remove performance indexes."""

    # Agent Executions
    op.drop_index('idx_agent_exec_agent_name_status', table_name='agent_executions')
    op.drop_index('idx_agent_exec_started_at', table_name='agent_executions')
    op.drop_index('idx_agent_exec_user_started', table_name='agent_executions')
    op.drop_index('idx_agent_exec_llm_cost', table_name='agent_executions')

    # Audit Logs
    op.drop_index('idx_audit_action_timestamp', table_name='audit_logs')
    op.drop_index('idx_audit_resource', table_name='audit_logs')
    op.drop_index('idx_audit_ip_timestamp', table_name='audit_logs')

    # Cost Tracking
    op.drop_index('idx_cost_date_range', table_name='cost_tracking')
    op.drop_index('idx_cost_model_analysis', table_name='cost_tracking')
    op.drop_index('idx_cost_user_timestamp', table_name='cost_tracking')

    # System Metrics
    op.drop_index('idx_metrics_name_time', table_name='system_metrics')
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_metrics_recent")

    # API Keys
    op.drop_index('idx_api_keys_expires', table_name='api_keys')

    # Users
    op.drop_index('idx_users_login', table_name='users')
    op.drop_index('idx_users_role', table_name='users')
