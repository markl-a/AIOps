"""Database connection and session management."""

from typing import Generator, Optional
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from loguru import logger

from aiops.core.config import get_config
from aiops.core.exceptions import DatabaseError, ConnectionError as DBConnectionError


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

    def init_engine(self, **kwargs):
        """Initialize database engine.

        Args:
            **kwargs: Additional engine arguments
        """
        try:
            # Default engine arguments
            engine_args = {
                "pool_pre_ping": True,  # Verify connections before using
                "pool_size": 10,
                "max_overflow": 20,
                "pool_recycle": 3600,  # Recycle connections after 1 hour
                "echo": False,
            }

            # Update with custom arguments
            engine_args.update(kwargs)

            self.engine = create_engine(self.database_url, **engine_args)

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
