import os
import psycopg
import logging

logger = logging.getLogger(__name__)


def get_db_connection() -> psycopg.Connection:
    """Establishes a connection to the PostgreSQL database."""
    host = os.getenv("DB_HOST", "localhost:5432")

    port = "5432"
    if host and ":" in host:
        host, port = host.split(":", 1)

    dbname = os.getenv("POSTGRES_DB", "aegis_db")
    user = os.getenv("POSTGRES_USER", "aegis_admin")
    password = os.getenv("POSTGRES_PASSWORD")
    if not password:
        raise ValueError(
            "POSTGRES_PASSWORD environment variable is not set; "
            "database password must be provided via environment variables."
        )

    try:
        conn = psycopg.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            connect_timeout=5,
        )
        return conn
    except Exception as e:
        logger.error(
            "Failed to connect to database host=%s port=%s db=%s user=%s: %s",
            host,
            port,
            dbname,
            user,
            e,
        )
        raise ConnectionError("Database connection failed") from e
