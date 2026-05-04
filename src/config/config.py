import logging
import os

TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "localhost:7233")
TEMPORAL_NAMESPACE = os.getenv("TEMPORAL_NAMESPACE", "default")
GRPC_PORT = os.getenv("GRPC_PORT", "50051")
BRAIN_TASK_QUEUE = os.getenv("BRAIN_TASK_QUEUE", "BRAIN_TASK_QUEUE")

# gRPC TLS Configuration
TLS_ENABLE = os.getenv("BRAIN_TLS_ENABLE", "false").lower() == "true"
TLS_CA_CERT = os.getenv("BRAIN_TLS_CA_CERT", "/etc/brain/certs/ca.crt")
TLS_SERVER_CERT = os.getenv("BRAIN_TLS_SERVER_CERT", "/etc/brain/certs/tls.crt")
TLS_SERVER_KEY = os.getenv("BRAIN_TLS_SERVER_KEY", "/etc/brain/certs/tls.key")

# Database Configuration
_DB_HOST_ENV = os.getenv("DB_HOST", "localhost:5432")
DB_HOST = _DB_HOST_ENV
DB_PORT = "5432"

if _DB_HOST_ENV and ":" in _DB_HOST_ENV:
    DB_HOST, DB_PORT = _DB_HOST_ENV.split(":", 1)

DB_NAME = os.getenv("POSTGRES_DB", "aegis_db")
DB_USER = os.getenv("POSTGRES_USER", "aegis_admin")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")

# Redis Configuration
_REDIS_HOST_ENV = os.getenv("REDIS_HOST", "localhost:6379")
REDIS_HOST = _REDIS_HOST_ENV
REDIS_PORT = "6379"
if ":" in _REDIS_HOST_ENV:
    REDIS_HOST, REDIS_PORT = _REDIS_HOST_ENV.split(":", 1)
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

# SQL Engine Debugging
SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", "False").lower() == "true"

# Authentication
JWT_SECRET = os.getenv("JWT_SECRET")

# MinIO Configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
MINIO_INGEST_BUCKET = os.getenv("MINIO_INGEST_BUCKET", "aegis-ingest")

# In production, we strictly require JWT_SECRET for security.
if not JWT_SECRET:
    _ENV = os.getenv("ENV", "").lower()
    _DEBUG = os.getenv("DEBUG", "").lower() == "true"
    _CI = os.getenv("CI", "").lower() == "true"
    _TESTING = "pytest" in os.getenv("PYTEST_CURRENT_TEST", "") or _CI

    if _ENV == "dev" or _DEBUG or _TESTING:
        # Developers should set this in their .env file (see .env.example)
        # We only allow it to be missing here if we are in a lower environment.
        JWT_SECRET = "insecure-dev-secret-only"
        logging.getLogger(__name__).warning(
            "JWT_SECRET not set. Using default insecure secret for development."
        )
    else:
        raise RuntimeError("JWT_SECRET must be set in production environments.")
