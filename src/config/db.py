import os
import psycopg
from typing import Optional


def get_db_connection() -> Optional[psycopg.Connection]:
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
            host=host, port=port, dbname=dbname, user=user, password=password
        )
        return conn
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        return None
