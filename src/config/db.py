import logging
import psycopg
from config.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

logger = logging.getLogger(__name__)


def get_db_connection() -> psycopg.Connection:
    """Establishes a connection to the PostgreSQL database."""
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
