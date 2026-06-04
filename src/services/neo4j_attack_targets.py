import base64
import json
import logging
from dataclasses import dataclass
from typing import Any
from urllib import error, request

from config.config import NEO4J_DATABASE, NEO4J_PASSWORD, NEO4J_URL, NEO4J_USER

logger = logging.getLogger("aegis_brain.neo4j_attack_targets")

CRITICAL_KEYWORDS = [
    "db",
    "database",
    "postgres",
    "mysql",
    "mariadb",
    "mongo",
    "redis",
    "elastic",
    "kibana",
    "vault",
    "rabbit",
    "queue",
    "cache",
    "admin",
]


@dataclass(frozen=True)
class AttackTarget:
    entry_id: str
    entry_name: str
    entry_path: str
    target_id: str
    target_name: str
    target_namespace: str
    target_kind: str
    target_path: str
    path_length: int
    criticality: int
    score: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "entry_name": self.entry_name,
            "entry_path": self.entry_path,
            "target_id": self.target_id,
            "target_name": self.target_name,
            "target_namespace": self.target_namespace,
            "target_kind": self.target_kind,
            "target_path": self.target_path,
            "path_length": self.path_length,
            "criticality": self.criticality,
            "score": self.score,
        }


class Neo4jAttackTargetService:
    def __init__(
        self,
        url: str = NEO4J_URL,
        user: str = NEO4J_USER,
        password: str = NEO4J_PASSWORD,
        database: str = NEO4J_DATABASE,
    ):
        self.url = url.rstrip("/")
        self.user = user
        self.password = password
        self.database = database

    def _auth_header(self) -> str:
        raw = f"{self.user}:{self.password}".encode("utf-8")
        return "Basic " + base64.b64encode(raw).decode("ascii")

    def _execute_query(self, cypher: str, parameters: dict[str, Any]) -> list[dict[str, Any]]:
        payload = {
            "statements": [
                {
                    "statement": cypher,
                    "parameters": parameters,
                }
            ]
        }
        req = request.Request(
            f"{self.url}/db/{self.database}/tx/commit",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": self._auth_header(),
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=15) as response:
                body = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Neo4j query failed with HTTP {exc.code}: {detail}") from exc
        except Exception as exc:
            raise RuntimeError(f"Neo4j query failed: {exc}") from exc

        if body.get("errors"):
            messages = [
                f"{item.get('code', 'unknown')}: {item.get('message', 'unknown error')}"
                for item in body["errors"]
            ]
            raise RuntimeError(f"Neo4j execution errors: {'; '.join(messages)}")

        results = body.get("results", [])
        if not results:
            return []

        rows = results[0].get("data", [])
        return [row.get("row", []) for row in rows]

    def identify_attack_targets(
        self, company_id: str, agent_id: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        company_id = company_id.strip()
        if not company_id:
            return []

        cypher = """
        MATCH (entry:Route)
        WHERE entry.companyId = $company_id
          AND ($agent_id IS NULL OR entry.agentId = $agent_id)
          AND (
            coalesce(entry.publishedPort, 0) IN [80, 443]
            OR coalesce(entry.sourcePort, 0) IN [80, 443]
            OR toLower(coalesce(entry.protocol, "")) IN ["http", "https"]
          )
        MATCH (target:Route)
        WHERE target.companyId = $company_id
          AND ($agent_id IS NULL OR target.agentId = $agent_id)
          AND entry.id <> target.id
          AND (
            coalesce(target.publishedPort, 0) IN [80, 443, 8080, 8443]
            OR coalesce(target.sourcePort, 0) IN [80, 443, 8080, 8443]
            OR toLower(coalesce(target.targetKind, "")) IN ["service", "container", "pod", "database"]
            OR any(keyword IN $critical_keywords WHERE
              toLower(coalesce(target.targetName, "")) CONTAINS keyword
              OR toLower(coalesce(target.sourceName, "")) CONTAINS keyword
              OR toLower(coalesce(target.path, "")) CONTAINS keyword
              OR toLower(coalesce(target.host, "")) CONTAINS keyword
            )
          )
        MATCH p = shortestPath((entry)-[:ROUTE_FROM|:ROUTE_TO*..8]-(target))
        WHERE p IS NOT NULL
        RETURN
          entry.id AS entry_id,
          entry.sourceName AS entry_name,
          coalesce(entry.path, "/") AS entry_path,
          target.id AS target_id,
          target.targetName AS target_name,
          coalesce(target.targetNamespace, "") AS target_namespace,
          coalesce(target.targetKind, "") AS target_kind,
          coalesce(target.path, "/") AS target_path,
          length(p) AS path_length,
          CASE
            WHEN toLower(coalesce(target.targetName, "")) CONTAINS "postgres"
              OR toLower(coalesce(target.targetName, "")) CONTAINS "mysql"
              OR toLower(coalesce(target.targetName, "")) CONTAINS "mariadb"
              OR toLower(coalesce(target.targetName, "")) CONTAINS "mongo"
              THEN 100
            WHEN toLower(coalesce(target.targetName, "")) CONTAINS "redis"
              OR toLower(coalesce(target.targetName, "")) CONTAINS "elastic"
              OR toLower(coalesce(target.targetName, "")) CONTAINS "kibana"
              THEN 90
            WHEN toLower(coalesce(target.targetName, "")) CONTAINS "admin"
              OR toLower(coalesce(target.path, "")) CONTAINS "admin"
              THEN 80
            ELSE 60
          END AS criticality
        ORDER BY path_length ASC, criticality DESC, entry_path ASC
        LIMIT $limit
        """

        query_params: dict[str, Any] = {
            "company_id": company_id,
            "critical_keywords": CRITICAL_KEYWORDS,
            "limit": max(1, int(limit)),
        }
        if agent_id:
            query_params["agent_id"] = agent_id.strip()

        logger.info(
            "Querying Neo4j for attack targets company_id=%s agent_id=%s limit=%s",
            company_id,
            agent_id,
            limit,
        )
        rows = self._execute_query(cypher, query_params)

        targets: list[AttackTarget] = []
        seen: set[tuple[str, str, str]] = set()
        for row in rows:
            if len(row) < 10:
                continue

            (
                entry_id,
                entry_name,
                entry_path,
                target_id,
                target_name,
                target_namespace,
                target_kind,
                target_path,
                path_length,
                criticality,
            ) = row[:10]

            normalized_target_path = self._normalize_path(target_path or entry_path)
            key = (
                str(target_id),
                str(target_namespace),
                normalized_target_path,
            )
            if key in seen:
                continue
            seen.add(key)

            score = int(criticality) * 100 - int(path_length)
            targets.append(
                AttackTarget(
                    entry_id=str(entry_id),
                    entry_name=str(entry_name or ""),
                    entry_path=self._normalize_path(entry_path),
                    target_id=str(target_id),
                    target_name=str(target_name or ""),
                    target_namespace=str(target_namespace or ""),
                    target_kind=str(target_kind or ""),
                    target_path=normalized_target_path,
                    path_length=int(path_length),
                    criticality=int(criticality),
                    score=score,
                )
            )

        targets.sort(key=lambda item: (-item.score, item.path_length, item.target_name))
        logger.info("Neo4j attack target selection returned %d target(s)", len(targets))
        return [target.as_dict() for target in targets[: max(1, int(limit))]]

    @staticmethod
    def _normalize_path(value: Any) -> str:
        path = str(value or "/").strip()
        if not path:
            return "/"
        if not path.startswith("/"):
            path = "/" + path
        return path


def identify_attack_targets(
    company_id: str, agent_id: str | None = None, limit: int = 10
) -> list[dict[str, Any]]:
    return Neo4jAttackTargetService().identify_attack_targets(
        company_id=company_id, agent_id=agent_id, limit=limit
    )
