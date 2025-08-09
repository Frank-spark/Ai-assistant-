"""Database connection and session management for Reflex Executive Assistant."""

from typing import Generator, Optional
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError
import structlog

from ..config import get_settings
from .models import Base

logger = structlog.get_logger(__name__)

# Global engine and session factory
_engine: Optional[object] = None
_session_factory: Optional[object] = None


def get_database_url() -> str:
    """Get the database URL from settings."""
    settings = get_settings()
    return settings.postgres_url


def create_database_engine():
    """Create and configure the database engine."""
    global _engine
    
    if _engine is not None:
        return _engine
    
    settings = get_settings()
    database_url = get_database_url()
    
    # Engine configuration
    engine_kwargs = {
        "poolclass": QueuePool,
        "pool_size": settings.postgres_pool_size,
        "max_overflow": settings.postgres_max_overflow,
        "pool_pre_ping": True,
        "pool_recycle": 3600,  # Recycle connections after 1 hour
        "echo": settings.debug,  # Log SQL queries in debug mode
    }
    
    try:
        _engine = create_engine(database_url, **engine_kwargs)
        
        # Add connection event listeners
        @event.listens_for(_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set SQLite pragmas for better performance (if using SQLite)."""
            if "sqlite" in database_url:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA cache_size=10000")
                cursor.execute("PRAGMA temp_store=MEMORY")
                cursor.close()
        
        @event.listens_for(_engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """Log connection checkout."""
            logger.debug("Database connection checked out")
        
        @event.listens_for(_engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """Log connection checkin."""
            logger.debug("Database connection checked in")
        
        logger.info(
            "Database engine created successfully",
            pool_size=settings.postgres_pool_size,
            max_overflow=settings.postgres_max_overflow
        )
        
        return _engine
        
    except Exception as e:
        logger.error(
            "Failed to create database engine",
            error=str(e),
            database_url=database_url
        )
        raise


def get_engine():
    """Get the database engine, creating it if necessary."""
    if _engine is None:
        create_database_engine()
    return _engine


def create_session_factory():
    """Create the session factory."""
    global _session_factory
    
    if _session_factory is not None:
        return _session_factory
    
    engine = get_engine()
    
    # Session configuration
    session_kwargs = {
        "bind": engine,
        "autoflush": False,
        "autocommit": False,
        "expire_on_commit": False,
    }
    
    _session_factory = sessionmaker(**session_kwargs)
    
    logger.info("Database session factory created successfully")
    return _session_factory


def get_session_factory():
    """Get the session factory, creating it if necessary."""
    if _session_factory is None:
        create_session_factory()
    return _session_factory


def get_scoped_session():
    """Get a scoped session factory for thread-local sessions."""
    session_factory = get_session_factory()
    return scoped_session(session_factory)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Get a database session with automatic cleanup."""
    session_factory = get_session_factory()
    session = session_factory()
    
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(
            "Database session error, rolling back",
            error=str(e),
            error_type=type(e).__name__
        )
        raise
    finally:
        session.close()


def create_tables():
    """Create all database tables."""
    try:
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(
            "Failed to create database tables",
            error=str(e),
            error_type=type(e).__name__
        )
        raise


def drop_tables():
    """Drop all database tables."""
    try:
        engine = get_engine()
        Base.metadata.drop_all(bind=engine)
        logger.info("Database tables dropped successfully")
    except Exception as e:
        logger.error(
            "Failed to drop database tables",
            error=str(e),
            error_type=type(e).__name__
        )
        raise


def check_database_connection() -> bool:
    """Check if the database connection is working."""
    try:
        with get_db_session() as session:
            # Try to execute a simple query
            session.execute("SELECT 1")
            logger.debug("Database connection check successful")
            return True
    except Exception as e:
        logger.error(
            "Database connection check failed",
            error=str(e),
            error_type=type(e).__name__
        )
        return False


def get_database_info() -> dict:
    """Get information about the database connection."""
    try:
        engine = get_engine()
        with engine.connect() as connection:
            # Get database version
            result = connection.execute("SELECT version()")
            version = result.scalar()
            
            # Get current database name
            result = connection.execute("SELECT current_database()")
            database_name = result.scalar()
            
            # Get connection pool info
            pool = engine.pool
            pool_info = {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": pool.invalid(),
            }
            
            return {
                "version": version,
                "database_name": database_name,
                "pool_info": pool_info,
                "url": str(engine.url).replace(
                    get_settings().postgres_url.split("@")[0].split(":")[-1],
                    "***"
                ) if "@" in get_settings().postgres_url else "***"
            }
            
    except Exception as e:
        logger.error(
            "Failed to get database info",
            error=str(e),
            error_type=type(e).__name__
        )
        return {"error": str(e)}


def close_database_connections():
    """Close all database connections."""
    global _engine, _session_factory
    
    try:
        if _engine:
            _engine.dispose()
            _engine = None
            logger.info("Database engine disposed")
        
        if _session_factory:
            _session_factory = None
            logger.info("Database session factory cleared")
            
    except Exception as e:
        logger.error(
            "Error closing database connections",
            error=str(e),
            error_type=type(e).__name__
        )


# Health check function
def is_database_healthy() -> bool:
    """Check if the database is healthy and accessible."""
    return check_database_connection()


# Cleanup on application shutdown
import atexit
atexit.register(close_database_connections) 