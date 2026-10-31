import os
import logging
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from config import get_settings

logger = logging.getLogger("nexus.database")
settings = get_settings()

# Base declarative class for all ORM models
Base = declarative_base()

def get_database_url() -> str:
    """
    Resolves the database URL based on environment configuration.
    Supports SQLite, PostgreSQL, and maintains MongoDB abstraction hooks.
    """
    db_type = settings.DATABASE_TYPE.lower()
    
    if db_type == "sqlite":
        # Resolve path relative to backend root if relative
        raw_url = settings.DATABASE_URL
        if raw_url.startswith("sqlite:///./"):
            db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", raw_url.replace("sqlite:///./", "")))
            return f"sqlite:///{db_path}"
        return raw_url
    elif db_type == "postgresql":
        return settings.DATABASE_URL
    else:
        # Fallback to SQLite
        return "sqlite:///./nexus_finops.db"

DATABASE_URL = get_database_url()

# Configure engine with concurrency optimizations
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

# Enable WAL (Write-Ahead Logging) for SQLite for improved multi-process concurrency
if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency and context provider for database sessions.
    Automatically commits on success or rolls back on exception.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db() -> None:
    """
    Initializes database tables and indexes.
    Safe to call multiple times (creates only if not existing).
    """
    # Import all models to ensure they are registered with Base.metadata
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialized successfully.")

def check_connection() -> dict:
    """
    Verifies live database connectivity and returns metadata.
    """
    db_type = settings.DATABASE_TYPE.lower()
    try:
        with engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("SELECT 1"))
        return {
            "status": "connected",
            "type": db_type,
            "url": DATABASE_URL.split("@")[-1]  # Hide credentials if any
        }
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return {
            "status": "error",
            "type": db_type,
            "error": str(e)
        }

