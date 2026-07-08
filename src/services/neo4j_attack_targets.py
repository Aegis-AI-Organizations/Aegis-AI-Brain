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
    image: str
    image_version: str
    image_hash: str
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
            "image": self.image,
            "image_version": self.image_version,
            "image_hash": self.image_hash,
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

    def _execute_query(
        self, cypher: str, parameters: dict[str, Any]
    ) -> list[dict[str, Any]]:
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
            raise RuntimeError(
                f"Neo4j query failed with HTTP {exc.code}: {detail}"
            ) from exc
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
        self,
        company_id: str,
        agent_id: str | None = None,
        target_ids: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        company_id = company_id.strip()
        if not company_id:
            return []

        normalized_target_ids = sorted(
            {target_id.strip() for target_id in target_ids or [] if target_id.strip()}
        )
        agent_entry_filter = ""
        agent_target_filter = ""
        selected_target_filter = ""
        query_params: dict[str, Any] = {
            "company_id": company_id,
            "critical_keywords": CRITICAL_KEYWORDS,
            "limit": max(1, int(limit)),
        }
        normalized_agent_id = agent_id.strip() if agent_id else ""
        if normalized_agent_id:
            agent_entry_filter = "AND entry.agentId = $agent_id"
            agent_target_filter = "AND target.agentId = $agent_id"
            query_params["agent_id"] = normalized_agent_id
        if normalized_target_ids:
            query_params["target_ids"] = normalized_target_ids
            selected_target_filter = """
          AND (
            target.id IN $target_ids
            OR target.rawId IN $target_ids
            OR target.targetName IN $target_ids
            OR target.sourceName IN $target_ids
            OR EXISTS {
              MATCH (c:Container)
              WHERE c.companyId = $company_id
                AND (c.id IN $target_ids OR c.rawId IN $target_ids OR c.name IN $target_ids)
                AND (
                  target.targetName = c.name
                  OR target.sourceName = c.name
                  OR target.targetName = c.rawId
                  OR target.sourceName = c.rawId
                )
            }
          )
            """

        cypher = """
        MATCH (entry:Route)
        WHERE entry.companyId = $company_id
          {agent_entry_filter}
          AND (
            coalesce(entry.publishedPort, 0) IN [80, 443]
            OR coalesce(entry.sourcePort, 0) IN [80, 443]
            OR toLower(coalesce(entry.protocol, "")) IN ["http", "https"]
          )
        MATCH (target:Route)
        WHERE target.companyId = $company_id
          {agent_target_filter}
          {selected_target_filter}
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
        MATCH p = shortestPath((entry)-[:ROUTE_FROM|ROUTE_TO*..8]-(target))
        WHERE p IS NOT NULL
        OPTIONAL MATCH (target_container:Container)
        WHERE target_container.companyId = $company_id
          AND (
            target.targetName = target_container.name
            OR target.sourceName = target_container.name
            OR target.targetName = target_container.rawId
            OR target.sourceName = target_container.rawId
          )
        RETURN
          entry.id AS entry_id,
          entry.sourceName AS entry_name,
          coalesce(entry.path, "/") AS entry_path,
          target.id AS target_id,
          target.targetName AS target_name,
          coalesce(target.targetNamespace, "") AS target_namespace,
          coalesce(target.targetKind, "") AS target_kind,
          coalesce(target.path, "/") AS target_path,
          coalesce(target_container.image, "") AS image,
          coalesce(target_container.imageVersion, "") AS image_version,
          coalesce(target_container.imageHash, target_container.imageSha256, "") AS image_hash,
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
        """.format(
            agent_entry_filter=agent_entry_filter,
            agent_target_filter=agent_target_filter,
            selected_target_filter=selected_target_filter,
        )

        logger.info(
            "Querying Neo4j for attack targets company_id=%s agent_id=%s selected_targets=%d limit=%s",
            company_id,
            agent_id,
            len(normalized_target_ids),
            limit,
        )
        rows = self._execute_query(cypher, query_params)
        if not rows and normalized_target_ids:
            logger.info(
                "Neo4j path target selection returned no rows; trying direct selected route lookup"
            )
            rows = self._execute_query(
                self._direct_selected_targets_query(agent_target_filter),
                query_params,
            )

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
            ) = row[:8]
            if len(row) >= 13:
                image, image_version, image_hash, path_length, criticality = row[8:13]
            else:
                image = ""
                image_version = ""
                image_hash = ""
                path_length, criticality = row[8:10]

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
                    image=str(image or ""),
                    image_version=str(image_version or ""),
                    image_hash=str(image_hash or ""),
                    path_length=int(path_length),
                    criticality=int(criticality),
                    score=score,
                )
            )

        targets.sort(key=lambda item: (-item.score, item.path_length, item.target_name))
        for target in targets[: max(1, int(limit))]:
            if target.image_version or target.image_hash:
                logger.info(
                    "Targeted %s (%s)",
                    target.image_version or target.image or target.target_name,
                    target.image_hash or "unknown hash",
                )
        logger.info("Neo4j attack target selection returned %d target(s)", len(targets))
        return [target.as_dict() for target in targets[: max(1, int(limit))]]

    @staticmethod
    def _direct_selected_targets_query(agent_target_filter: str) -> str:
        return """
        MATCH (target:Route)
        WHERE target.companyId = $company_id
          __AGENT_TARGET_FILTER__
          AND (
            target.id IN $target_ids
            OR target.rawId IN $target_ids
            OR target.targetName IN $target_ids
            OR target.sourceName IN $target_ids
            OR EXISTS {
              MATCH (c:Container)
              WHERE c.companyId = $company_id
                AND (c.id IN $target_ids OR c.rawId IN $target_ids OR c.name IN $target_ids)
                AND (
                  target.targetName = c.name
                  OR target.sourceName = c.name
                  OR target.targetName = c.rawId
                  OR target.sourceName = c.rawId
                )
            }
          )
        OPTIONAL MATCH (target_container:Container)
        WHERE target_container.companyId = $company_id
          AND (
            target.targetName = target_container.name
            OR target.sourceName = target_container.name
            OR target.targetName = target_container.rawId
            OR target.sourceName = target_container.rawId
          )
        RETURN
          target.id AS entry_id,
          coalesce(target.sourceName, target.targetName, "") AS entry_name,
          coalesce(target.path, "/") AS entry_path,
          target.id AS target_id,
          coalesce(target.targetName, target.sourceName, "") AS target_name,
          coalesce(target.targetNamespace, target.sourceNamespace, "") AS target_namespace,
          coalesce(target.targetKind, target.sourceKind, "") AS target_kind,
          coalesce(target.path, "/") AS target_path,
          coalesce(target_container.image, "") AS image,
          coalesce(target_container.imageVersion, "") AS image_version,
          coalesce(target_container.imageHash, target_container.imageSha256, "") AS image_hash,
          0 AS path_length,
          CASE
            WHEN toLower(coalesce(target.targetName, target.sourceName, "")) CONTAINS "postgres"
              OR toLower(coalesce(target.targetName, target.sourceName, "")) CONTAINS "mysql"
              OR toLower(coalesce(target.targetName, target.sourceName, "")) CONTAINS "mariadb"
              OR toLower(coalesce(target.targetName, target.sourceName, "")) CONTAINS "mongo"
              THEN 100
            WHEN toLower(coalesce(target.targetName, target.sourceName, "")) CONTAINS "redis"
              OR toLower(coalesce(target.targetName, target.sourceName, "")) CONTAINS "elastic"
              OR toLower(coalesce(target.targetName, target.sourceName, "")) CONTAINS "kibana"
              THEN 90
            WHEN toLower(coalesce(target.targetName, target.sourceName, "")) CONTAINS "admin"
              OR toLower(coalesce(target.path, "")) CONTAINS "admin"
              THEN 80
            ELSE 60
          END AS criticality
        ORDER BY criticality DESC, target_path ASC
        LIMIT $limit
        """.replace("__AGENT_TARGET_FILTER__", agent_target_filter)

    @staticmethod
    def _normalize_path(value: Any) -> str:
        path = str(value or "/").strip()
        if not path:
            return "/"
        if not path.startswith("/"):
            path = "/" + path
        return path


def identify_attack_targets(
    company_id: str,
    agent_id: str | None = None,
    target_ids: list[str] | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    return Neo4jAttackTargetService().identify_attack_targets(
        company_id=company_id,
        agent_id=agent_id,
        target_ids=target_ids,
        limit=limit,
    )
