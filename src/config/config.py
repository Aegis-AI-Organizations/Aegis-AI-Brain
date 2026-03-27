import os

TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "localhost:7233")
GRPC_PORT = os.getenv("GRPC_PORT", "50051")
BRAIN_TASK_QUEUE = os.getenv("BRAIN_TASK_QUEUE", "BRAIN_TASK_QUEUE")

# Database Configuration
_DB_HOST_ENV = os.getenv("DB_HOST", "localhost:5432")
DB_HOST = _DB_HOST_ENV
DB_PORT = "5432"

if _DB_HOST_ENV and ":" in _DB_HOST_ENV:
    DB_HOST, DB_PORT = _DB_HOST_ENV.split(":", 1)

DB_NAME = os.getenv("POSTGRES_DB", "aegis_db")
DB_USER = os.getenv("POSTGRES_USER", "aegis_admin")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
