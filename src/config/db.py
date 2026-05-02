import logging
from typing import Generator

import psycopg
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker

from config.config import (
    DB_HOST,
    DB_NAME,
    DB_PASSWORD,
    DB_PORT,
    DB_USER,
    SQLALCHEMY_ECHO,
)

logger = logging.getLogger(__name__)

_engine = None
_SessionLocal = None


def _build_db_url() -> URL:
    """Builds the SQLAlchemy DB URL securely."""
    if not DB_PASSWORD:
        logger.error("POSTGRES_PASSWORD is not set in environment or config")
        raise EnvironmentError(
            "POSTGRES_PASSWORD is required for database session initialization. "
            "Please check your environment variables or Infisical secrets."
        )

    return URL.create(
        drivername="postgresql+psycopg",
        username=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=int(DB_PORT) if DB_PORT else 5432,
        database=DB_NAME,
    )


def get_engine():
    """Lazily initializes and returns the SQLAlchemy engine with a connection pool."""
    global _engine
    if _engine is None:
        db_url = _build_db_url()
        _engine = create_engine(
            db_url,
            echo=SQLALCHEMY_ECHO,
            pool_size=20,          # Maintain up to 20 idle connections
            max_overflow=10,       # Allow up to 10 extra connections during bursts
            pool_timeout=30,       # Wait 30s for a connection from the pool
            pool_recycle=1800,     # Recycle connections every 30 minutes
            pool_pre_ping=True,    # Verify connection health before use
        )
    return _engine


def get_session_factory():
    """Lazily initializes and returns the session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


def get_db_connection() -> psycopg.Connection:
    """Establishes a raw connection to the PostgreSQL database (legacy)."""
    if not DB_PASSWORD:
        raise ValueError(
            "POSTGRES_PASSWORD environment variable is not set; "
            "database password must be provided via environment variables."
        )

    try:
        conn = psycopg.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            connect_timeout=5,
        )
        return conn
    except Exception as e:
        logger.error(
            "Failed to connect to database host=%s port=%s db=%s user=%s: %s",
            DB_HOST,
            DB_PORT,
            DB_NAME,
            DB_USER,
            e,
        )
        raise ConnectionError("Database connection failed") from e


def get_session() -> Generator[Session, None, None]:
    """Dependency for providing a SQLAlchemy session."""
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
