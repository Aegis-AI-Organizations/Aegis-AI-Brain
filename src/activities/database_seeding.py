import json
import logging
import os
import ssl
from dataclasses import dataclass
from typing import Any
from urllib import error, request

import psycopg
from temporalio import activity

logger = logging.getLogger("aegis_brain.database_seeding")

SEED_FLAG = "aegis-flag-1234"
SERVICE_ACCOUNT_TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"
SERVICE_ACCOUNT_CA_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"


@dataclass(frozen=True)
class DatabaseTarget:
    name: str
    host: str
    port: int
    database: str
    user: str
    password: str


def _kubernetes_namespace(scan_id: str) -> str:
    return f"aegis-war-room-{scan_id.strip()}"


def _kubernetes_api_base() -> str:
    host = os.getenv("KUBERNETES_SERVICE_HOST", "kubernetes.default.svc")
    port = os.getenv("KUBERNETES_SERVICE_PORT_HTTPS") or os.getenv(
        "KUBERNETES_SERVICE_PORT", "443"
    )
    return f"https://{host}:{port}"


def _read_service_account_token() -> str:
    with open(SERVICE_ACCOUNT_TOKEN_PATH, encoding="utf-8") as token_file:
        return token_file.read().strip()


def _ssl_context() -> ssl.SSLContext:
    if os.path.exists(SERVICE_ACCOUNT_CA_PATH):
        return ssl.create_default_context(cafile=SERVICE_ACCOUNT_CA_PATH)
    return ssl.create_default_context()


def _kubernetes_get(path: str) -> dict[str, Any]:
    req = request.Request(
        _kubernetes_api_base() + path,
        headers={"Authorization": f"Bearer {_read_service_account_token()}"},
        method="GET",
    )
    try:
        with request.urlopen(req, timeout=15, context=_ssl_context()) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Kubernetes API GET {path} failed: HTTP {exc.code}: {detail}"
        ) from exc


def _env_from_container(container: dict[str, Any]) -> dict[str, str]:
    env: dict[str, str] = {}
    for item in container.get("env") or []:
        name = str(item.get("name") or "").strip()
        if not name or "value" not in item:
            continue
        env[name] = str(item.get("value") or "")
    return env


def _pod_matches_selector(pod: dict[str, Any], selector: dict[str, str]) -> bool:
    labels = pod.get("metadata", {}).get("labels") or {}
    return bool(selector) and all(labels.get(key) == value for key, value in selector.items())


def _is_postgres_candidate(service: dict[str, Any], pods: list[dict[str, Any]]) -> bool:
    service_name = str(service.get("metadata", {}).get("name") or "").lower()
    if any(keyword in service_name for keyword in ("postgres", "postgresql", "pg")):
        return True
    for pod in pods:
        for container in pod.get("spec", {}).get("containers") or []:
            image = str(container.get("image") or "").lower()
            env = _env_from_container(container)
            if "postgres" in image or any(key.startswith("POSTGRES_") for key in env):
                return True
    return False


def _service_port(service: dict[str, Any]) -> int:
    ports = service.get("spec", {}).get("ports") or []
    for port in ports:
        name = str(port.get("name") or "").lower()
        if port.get("port") == 5432 or "postgres" in name or name in {"pg", "pgsql"}:
            return int(port.get("port") or 5432)
    return int(ports[0].get("port") or 5432) if ports else 5432


def _postgres_credentials(pods: list[dict[str, Any]]) -> tuple[str, str, str]:
    for pod in pods:
        for container in pod.get("spec", {}).get("containers") or []:
            env = _env_from_container(container)
            if any(key.startswith("POSTGRES_") for key in env):
                return (
                    env.get("POSTGRES_DB") or env.get("POSTGRES_DATABASE") or "postgres",
                    env.get("POSTGRES_USER") or "postgres",
                    env.get("POSTGRES_PASSWORD") or "postgres",
                )
    return "postgres", "postgres", "postgres"


def discover_postgres_targets(scan_id: str) -> list[DatabaseTarget]:
    namespace = _kubernetes_namespace(scan_id)
    services = _kubernetes_get(f"/api/v1/namespaces/{namespace}/services").get("items") or []
    pods = _kubernetes_get(f"/api/v1/namespaces/{namespace}/pods").get("items") or []
    targets: list[DatabaseTarget] = []

    for service in services:
        service_name = str(service.get("metadata", {}).get("name") or "").strip()
        if not service_name:
            continue
        selector = service.get("spec", {}).get("selector") or {}
        matching_pods = [pod for pod in pods if _pod_matches_selector(pod, selector)]
        if not _is_postgres_candidate(service, matching_pods):
            continue
        database, user, password = _postgres_credentials(matching_pods)
        targets.append(
            DatabaseTarget(
                name=service_name,
                host=f"{service_name}.{namespace}.svc.cluster.local",
                port=_service_port(service),
                database=database,
                user=user,
                password=password,
            )
        )
    return targets


def seed_postgres_target(target: DatabaseTarget) -> None:
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        seed_flag TEXT NOT NULL
    );
    """
    insert_sql = """
    INSERT INTO users (email, password, role, seed_flag)
    VALUES
        ('admin@company.com', 'password123', 'admin', %(seed_flag)s),
        ('analyst@company.com', 'password123', 'user', %(seed_flag)s),
        ('billing@company.com', 'password123', 'user', %(seed_flag)s)
    ON CONFLICT (email) DO UPDATE SET
        password = EXCLUDED.password,
        role = EXCLUDED.role,
        seed_flag = EXCLUDED.seed_flag;
    """
    with psycopg.connect(
        host=target.host,
        port=target.port,
        dbname=target.database,
        user=target.user,
        password=target.password,
        connect_timeout=10,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(create_table_sql)
            cur.execute(insert_sql, {"seed_flag": SEED_FLAG})
        conn.commit()


@activity.defn(name="SeedTargetDatabases")
async def seed_target_databases(scan_id: str) -> dict:
    namespace = _kubernetes_namespace(scan_id)
    logger.info("Seeding target databases in namespace=%s", namespace)
    targets = discover_postgres_targets(scan_id)
    seeded: list[str] = []
    failures: list[dict[str, str]] = []

    for target in targets:
        try:
            seed_postgres_target(target)
            seeded.append(target.name)
            logger.info("Seeded PostgreSQL database service=%s host=%s", target.name, target.host)
        except Exception as exc:
            logger.exception("Failed to seed PostgreSQL database service=%s", target.name)
            failures.append({"service": target.name, "error": str(exc)})

    if failures:
        raise RuntimeError(f"database seeding failed in {namespace}: {failures}")

    return {
        "namespace": namespace,
        "seeded": seeded,
        "seeded_count": len(seeded),
        "seed_flag": SEED_FLAG,
    }
