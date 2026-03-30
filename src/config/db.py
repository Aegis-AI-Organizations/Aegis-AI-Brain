import logging
from typing import Generator

import psycopg
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker

from config.config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER

logger = logging.getLogger(__name__)


def _build_db_url() -> URL:
    """Builds the SQLAlchemy DB URL securely."""
    if not DB_PASSWORD:
        logger.error("DB_PASSWORD is not set in environment or config")
        raise EnvironmentError(
            "DB_PASSWORD is required for database connection. "
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


DB_URL = _build_db_url()
engine = create_engine(DB_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
