"""Database connection and session management."""

from typing import Generator, Optional
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool, Pool
from loguru import logger
import time

from aiops.core.config import get_config
from aiops.core.exceptions import DatabaseError, DatabaseConnectionError as DBConnectionError


# Base class for all models
Base = declarative_base()


class DatabaseManager:
    """Manage database connections and sessions."""

    def __init__(self, database_url: Optional[str] = None):
        """Initialize database manager.

        Args:
            database_url: Database connection URL
        """
        self.database_url = database_url or self._get_database_url()
        self.engine = None
        self.SessionLocal = None

    def _get_database_url(self) -> str:
        """Get database URL from config.

        Returns:
            Database URL
        """
        config = get_config()

        # Check for explicit database URL
        if hasattr(config, "database_url") and config.database_url:
            return config.database_url

        # Build from components
        db_user = getattr(config, "database_user", "aiops")
        db_password = getattr(config, "database_password", "aiops")
        db_host = getattr(config, "database_host", "localhost")
        db_port = getattr(config, "database_port", 5432)
        db_name = getattr(config, "database_name", "aiops")

        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    def _setup_connection_pool_listeners(self):
        """Set up event listeners for connection pool monitoring."""
        # Track connection pool statistics
        pool_stats = {
            "checkouts": 0,
            "checkins": 0,
            "connects": 0,
            "disconnects": 0,
            "invalidations": 0,
        }

        @event.listens_for(Pool, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            """Log connection checkout from pool."""
            pool_stats["checkouts"] += 1
            logger.debug(
                f"Connection checked out from pool (total checkouts: {pool_stats['checkouts']})"
            )

        @event.listens_for(Pool, "checkin")
        def receive_checkin(dbapi_conn, connection_record):
            """Log connection checkin to pool."""
            pool_stats["checkins"] += 1
            logger.debug(
                f"Connection checked in to pool (total checkins: {pool_stats['checkins']})"
            )

        @event.listens_for(Pool, "connect")
        def receive_connect(dbapi_conn, connection_record):
            """Log new database connection."""
            pool_stats["connects"] += 1
            logger.info(
                f"New database connection created (total connections: {pool_stats['connects']})"
            )

        @event.listens_for(Pool, "close")
        def receive_close(dbapi_conn, connection_record):
            """Log connection close."""
            pool_stats["disconnects"] += 1
            logger.debug(
                f"Database connection closed (total disconnects: {pool_stats['disconnects']})"
            )

        @event.listens_for(Pool, "invalidate")
        def receive_invalidate(dbapi_conn, connection_record, exception):
            """Log connection invalidation."""
            pool_stats["invalidations"] += 1
            logger.warning(
                f"Connection invalidated: {exception} "
                f"(total invalidations: {pool_stats['invalidations']})"
            )

        # Store stats for later retrieval
        self._pool_stats = pool_stats

    def _setup_query_listeners(self):
        """Set up event listeners for query performance monitoring."""
        # Track slow queries
        slow_query_threshold_ms = 1000  # 1 second

        @event.listens_for(self.engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Record query start time."""
            conn.info.setdefault("query_start_time", []).append(time.time())

        @event.listens_for(self.engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Log slow queries."""
            total_time = time.time() - conn.info["query_start_time"].pop(-1)
            total_time_ms = total_time * 1000

            if total_time_ms > slow_query_threshold_ms:
                logger.warning(
                    f"Slow query detected ({total_time_ms:.2f}ms): "
                    f"{statement[:200]}..."
                )

    def get_pool_stats(self) -> dict:
        """Get connection pool statistics.

        Returns:
            Dictionary with pool statistics
        """
        if not self.engine:
            return {}

        pool = self.engine.pool
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "total_checkouts": self._pool_stats.get("checkouts", 0),
            "total_checkins": self._pool_stats.get("checkins", 0),
            "total_connections": self._pool_stats.get("connects", 0),
            "total_disconnects": self._pool_stats.get("disconnects", 0),
            "total_invalidations": self._pool_stats.get("invalidations", 0),
        }

    def init_engine(self, **kwargs):
        """Initialize database engine.

        Args:
            **kwargs: Additional engine arguments
        """
        try:
            # Get environment-based pool size
            import os
            env = os.getenv("ENVIRONMENT", "development").lower()
            is_production = env in ("production", "prod")

            # Optimized pool settings based on environment
            # Production: Larger pool for high concurrency
            # Development: Smaller pool for resource efficiency
            default_pool_size = 20 if is_production else 5
            default_max_overflow = 40 if is_production else 10

            # Default engine arguments with optimized settings
            engine_args = {
                "pool_pre_ping": True,  # Verify connections before using
                "pool_size": int(os.getenv("DB_POOL_SIZE", default_pool_size)),
                "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", default_max_overflow)),
                "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", 3600)),  # Recycle after 1 hour
                "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", 30)),  # Wait up to 30s for connection
                "echo": os.getenv("DB_ECHO", "false").lower() == "true",
                # Enable query statistics for PostgreSQL
                "echo_pool": os.getenv("DB_ECHO_POOL", "false").lower() == "true",
                # Connection arguments for better reliability
                "connect_args": {
                    "connect_timeout": 10,  # Connection timeout in seconds
                    "application_name": "aiops",  # Identify in pg_stat_activity
                    # Enable server-side prepared statements for better performance
                    "options": "-c statement_timeout=30000",  # 30 second query timeout
                },
            }

            # Log pool configuration
            logger.info(
                f"Database pool config: size={engine_args['pool_size']}, "
                f"overflow={engine_args['max_overflow']}, "
                f"timeout={engine_args['pool_timeout']}s, "
                f"recycle={engine_args['pool_recycle']}s"
            )

            # Update with custom arguments
            engine_args.update(kwargs)

            self.engine = create_engine(self.database_url, **engine_args)

            # Set up connection pool and query listeners
            self._setup_connection_pool_listeners()
            self._setup_query_listeners()

            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine,
            )

            logger.info(f"Database engine initialized: {self._safe_url()}")

        except Exception as e:
            logger.error(f"Failed to initialize database engine: {e}")
            raise DBConnectionError(
                message="Failed to initialize database connection",
                database=self._safe_url(),
            ) from e

    def _safe_url(self) -> str:
        """Get database URL with password masked.

        Returns:
            Safe database URL
        """
        if "@" in self.database_url:
            parts = self.database_url.split("@")
            creds = parts[0]
            if ":" in creds:
                user = creds.split(":")[0].split("//")[-1]
                return f"{creds.split(':')[0]}:{user}:****@{parts[1]}"
        return self.database_url

    def create_tables(self):
        """Create all database tables."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise DatabaseError(
                message="Failed to create database tables",
                operation="create_tables",
                original_error=e,
            ) from e

    def drop_tables(self):
        """Drop all database tables."""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.warning("All database tables dropped")
        except Exception as e:
            logger.error(f"Failed to drop database tables: {e}")
            raise DatabaseError(
                message="Failed to drop database tables",
                operation="drop_tables",
                original_error=e,
            ) from e

    def get_session(self) -> Session:
        """Get a new database session.

        Returns:
            SQLAlchemy session

        Raises:
            DatabaseError: If session cannot be created
        """
        if self.SessionLocal is None:
            raise DatabaseError(
                message="Database not initialized. Call init_engine() first",
                operation="get_session",
            )

        try:
            return self.SessionLocal()
        except Exception as e:
            logger.error(f"Failed to create database session: {e}")
            raise DatabaseError(
                message="Failed to create database session",
                operation="get_session",
                original_error=e,
            ) from e

    def close(self):
        """Close database connection."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed")


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def init_db(database_url: Optional[str] = None, **kwargs) -> DatabaseManager:
    """Initialize database.

    Args:
        database_url: Database connection URL
        **kwargs: Additional engine arguments

    Returns:
        DatabaseManager instance
    """
    global _db_manager

    if _db_manager is None:
        _db_manager = DatabaseManager(database_url=database_url)
        _db_manager.init_engine(**kwargs)
        _db_manager.create_tables()

    return _db_manager


def get_db() -> Generator[Session, None, None]:
    """Get database session (dependency injection).

    Yields:
        Database session
    """
    if _db_manager is None:
        raise DatabaseError(
            message="Database not initialized. Call init_db() first",
            operation="get_db",
        )

    session = _db_manager.get_session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database transaction error: {e}")
        raise DatabaseError(
            message="Database transaction failed",
            operation="transaction",
            original_error=e,
        ) from e
    finally:
        session.close()


def get_db_manager() -> DatabaseManager:
    """Get global database manager.

    Returns:
        DatabaseManager instance

    Raises:
        DatabaseError: If database not initialized
    """
    if _db_manager is None:
        raise DatabaseError(
            message="Database not initialized. Call init_db() first",
            operation="get_db_manager",
        )
    return _db_manager


def close_db():
    """Close database connection."""
    global _db_manager
    if _db_manager:
        _db_manager.close()
        _db_manager = None
