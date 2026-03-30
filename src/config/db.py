import logging
from typing import Generator

import psycopg
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config.config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER

logger = logging.getLogger(__name__)

# SQLAlchemy standard setup
# Using psycopg as the driver for SQLAlchemy to match existing dependency
DB_URL = f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

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
