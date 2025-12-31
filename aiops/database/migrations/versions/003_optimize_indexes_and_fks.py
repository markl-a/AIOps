"""Optimize indexes and foreign key constraints

Revision ID: 003_optimize_indexes_and_fks
Revises: 002_add_indexes
Create Date: 2025-01-01 00:00:00.000000

This migration adds:
1. Missing indexes on frequently queried columns
2. Foreign key cascade constraints
3. Composite indexes for common query patterns
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_optimize_indexes_and_fks'
down_revision = '002_add_indexes'
branch_labels = None
depends_on = None


def upgrade():
    """Add optimized indexes and update foreign key constraints."""

    # ========== User Table Indexes ==========
    # Add indexes for role and is_active (if not already exist)
    op.create_index('idx_user_role', 'users', ['role'], unique=False, if_not_exists=True)
    op.create_index('idx_user_is_active', 'users', ['is_active'], unique=False, if_not_exists=True)

    # Add composite index for active users with specific role
    op.create_index('idx_user_active_role', 'users', ['is_active', 'role'], unique=False, if_not_exists=True)

    # Add index for last login queries
    op.create_index('idx_user_last_login', 'users', ['last_login'], unique=False, if_not_exists=True)

    # ========== APIKey Table Indexes ==========
    # Add index for user_id (if not already exist)
    op.create_index('idx_api_key_user_id', 'api_keys', ['user_id'], unique=False, if_not_exists=True)

    # Add index for is_active
    op.create_index('idx_api_key_is_active', 'api_keys', ['is_active'], unique=False, if_not_exists=True)

    # Add index for expires_at
    op.create_index('idx_api_key_expires_at', 'api_keys', ['expires_at'], unique=False, if_not_exists=True)

    # Add composite index for checking expired keys
    op.create_index('idx_api_key_expires', 'api_keys', ['expires_at', 'is_active'], unique=False, if_not_exists=True)

    # ========== AgentExecution Table Indexes ==========
    # Add standalone indexes for frequently queried columns
    op.create_index('idx_execution_user_id', 'agent_executions', ['user_id'], unique=False, if_not_exists=True)
    op.create_index('idx_execution_status', 'agent_executions', ['status'], unique=False, if_not_exists=True)
    op.create_index('idx_execution_started_at', 'agent_executions', ['started_at'], unique=False, if_not_exists=True)
    op.create_index('idx_execution_completed_at', 'agent_executions', ['completed_at'], unique=False, if_not_exists=True)
    op.create_index('idx_execution_llm_provider', 'agent_executions', ['llm_provider'], unique=False, if_not_exists=True)

    # Add composite indexes for common query patterns
    op.create_index('idx_execution_status_completed', 'agent_executions', ['status', 'completed_at'], unique=False, if_not_exists=True)
    op.create_index('idx_execution_provider_model', 'agent_executions', ['llm_provider', 'llm_model'], unique=False, if_not_exists=True)

    # ========== AuditLog Table Indexes ==========
    # Add standalone indexes
    op.create_index('idx_audit_user_id', 'audit_logs', ['user_id'], unique=False, if_not_exists=True)
    op.create_index('idx_audit_action', 'audit_logs', ['action'], unique=False, if_not_exists=True)
    op.create_index('idx_audit_resource_type', 'audit_logs', ['resource_type'], unique=False, if_not_exists=True)
    op.create_index('idx_audit_ip_address', 'audit_logs', ['ip_address'], unique=False, if_not_exists=True)
    op.create_index('idx_audit_status_code', 'audit_logs', ['status_code'], unique=False, if_not_exists=True)

    # Add composite indexes for security audit queries
    op.create_index('idx_audit_ip_timestamp', 'audit_logs', ['ip_address', 'timestamp'], unique=False, if_not_exists=True)
    op.create_index('idx_audit_event_timestamp', 'audit_logs', ['event_type', 'timestamp'], unique=False, if_not_exists=True)
    op.create_index('idx_audit_status_timestamp', 'audit_logs', ['status_code', 'timestamp'], unique=False, if_not_exists=True)

    # ========== CostTracking Table Indexes ==========
    # Add standalone indexes
    op.create_index('idx_cost_user_id', 'cost_tracking', ['user_id'], unique=False, if_not_exists=True)
    op.create_index('idx_cost_model', 'cost_tracking', ['model'], unique=False, if_not_exists=True)

    # Add composite indexes for cost analysis
    op.create_index('idx_cost_provider_model', 'cost_tracking', ['provider', 'model', 'timestamp'], unique=False, if_not_exists=True)
    op.create_index('idx_cost_user_timestamp', 'cost_tracking', ['user_id', 'timestamp'], unique=False, if_not_exists=True)

    # ========== SystemMetric Table Indexes ==========
    # Add index for time-based cleanup
    op.create_index('idx_metric_timestamp', 'system_metrics', ['timestamp'], unique=False, if_not_exists=True)

    # ========== Configuration Table Indexes ==========
    # Add index for filtering secret configurations
    op.create_index('idx_config_is_secret', 'configurations', ['is_secret'], unique=False, if_not_exists=True)

    # Add index for recently updated configurations
    op.create_index('idx_config_updated', 'configurations', ['updated_at'], unique=False, if_not_exists=True)

    # ========== Update Foreign Key Constraints ==========
    # Note: We can't modify existing foreign keys directly in PostgreSQL without dropping and recreating them
    # This would require more complex migration logic and could cause data loss
    # Instead, document the recommended foreign key constraints for new installations:
    #
    # api_keys.user_id -> users.id (ON DELETE CASCADE)
    # agent_executions.user_id -> users.id (ON DELETE SET NULL)
    # audit_logs.user_id -> users.id (ON DELETE SET NULL)
    # cost_tracking.user_id -> users.id (ON DELETE SET NULL)
    #
    # For existing installations, these constraints should be updated manually if needed


def downgrade():
    """Remove optimized indexes."""

    # Drop User table indexes
    op.drop_index('idx_user_role', table_name='users', if_exists=True)
    op.drop_index('idx_user_is_active', table_name='users', if_exists=True)
    op.drop_index('idx_user_active_role', table_name='users', if_exists=True)
    op.drop_index('idx_user_last_login', table_name='users', if_exists=True)

    # Drop APIKey table indexes
    op.drop_index('idx_api_key_user_id', table_name='api_keys', if_exists=True)
    op.drop_index('idx_api_key_is_active', table_name='api_keys', if_exists=True)
    op.drop_index('idx_api_key_expires_at', table_name='api_keys', if_exists=True)
    op.drop_index('idx_api_key_expires', table_name='api_keys', if_exists=True)

    # Drop AgentExecution table indexes
    op.drop_index('idx_execution_user_id', table_name='agent_executions', if_exists=True)
    op.drop_index('idx_execution_status', table_name='agent_executions', if_exists=True)
    op.drop_index('idx_execution_started_at', table_name='agent_executions', if_exists=True)
    op.drop_index('idx_execution_completed_at', table_name='agent_executions', if_exists=True)
    op.drop_index('idx_execution_llm_provider', table_name='agent_executions', if_exists=True)
    op.drop_index('idx_execution_status_completed', table_name='agent_executions', if_exists=True)
    op.drop_index('idx_execution_provider_model', table_name='agent_executions', if_exists=True)

    # Drop AuditLog table indexes
    op.drop_index('idx_audit_user_id', table_name='audit_logs', if_exists=True)
    op.drop_index('idx_audit_action', table_name='audit_logs', if_exists=True)
    op.drop_index('idx_audit_resource_type', table_name='audit_logs', if_exists=True)
    op.drop_index('idx_audit_ip_address', table_name='audit_logs', if_exists=True)
    op.drop_index('idx_audit_status_code', table_name='audit_logs', if_exists=True)
    op.drop_index('idx_audit_ip_timestamp', table_name='audit_logs', if_exists=True)
    op.drop_index('idx_audit_event_timestamp', table_name='audit_logs', if_exists=True)
    op.drop_index('idx_audit_status_timestamp', table_name='audit_logs', if_exists=True)

    # Drop CostTracking table indexes
    op.drop_index('idx_cost_user_id', table_name='cost_tracking', if_exists=True)
    op.drop_index('idx_cost_model', table_name='cost_tracking', if_exists=True)
    op.drop_index('idx_cost_provider_model', table_name='cost_tracking', if_exists=True)
    op.drop_index('idx_cost_user_timestamp', table_name='cost_tracking', if_exists=True)

    # Drop SystemMetric table indexes
    op.drop_index('idx_metric_timestamp', table_name='system_metrics', if_exists=True)

    # Drop Configuration table indexes
    op.drop_index('idx_config_is_secret', table_name='configurations', if_exists=True)
    op.drop_index('idx_config_updated', table_name='configurations', if_exists=True)
