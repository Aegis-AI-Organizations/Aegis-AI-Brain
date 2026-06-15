import base64
import json
import logging
import re
from typing import Any
from urllib import error, request

from config.config import NEO4J_DATABASE, NEO4J_PASSWORD, NEO4J_URL, NEO4J_USER

logger = logging.getLogger("aegis_brain.neo4j_sandbox_topology")


class Neo4jSandboxTopologyService:
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

    def build_sandbox_topology(
        self, company_id: str, target_ids: list[str] | None = None
    ) -> dict[str, Any]:
        company_id = company_id.strip()
        if not company_id:
            return {"containers": []}

        normalized_ids = sorted(
            {target_id.strip() for target_id in target_ids or [] if target_id.strip()}
        )
        parameters: dict[str, Any] = {"company_id": company_id}
        target_filter = ""
        if normalized_ids:
            parameters["target_ids"] = normalized_ids
            target_filter = """
              AND (
                c.id IN $target_ids
                OR c.rawId IN $target_ids
                OR c.name IN $target_ids
                OR EXISTS {
                  MATCH (r:Route)
                  WHERE r.companyId = $company_id
                    AND r.id IN $target_ids
                    AND (
                      r.targetName = c.name
                      OR r.sourceName = c.name
                      OR r.targetName = c.rawId
                      OR r.sourceName = c.rawId
                    )
                }
              )
            """

        cypher = """
        MATCH (c:Container)
        WHERE c.companyId = $company_id
          AND coalesce(c.image, "") <> ""
          {target_filter}
        RETURN
          c.id AS id,
          coalesce(c.name, c.rawId, c.id) AS name,
          c.image AS image,
          coalesce(c.env, []) AS env,
          coalesce(c.labels, []) AS labels,
          coalesce(c.networks, []) AS networks,
          coalesce(c.ports, []) AS ports,
          coalesce(c.exposedPorts, []) AS exposed_ports
        ORDER BY name ASC
        LIMIT 30
        """.format(target_filter=target_filter)

        logger.info(
            "Building sandbox topology from Neo4j company_id=%s selected_targets=%d",
            company_id,
            len(normalized_ids),
        )
        rows = self._execute_query(cypher, parameters)
        containers = [self._row_to_container(row) for row in rows if len(row) >= 8]
        containers = [container for container in containers if container.get("image")]

        logger.info(
            "Neo4j sandbox topology contains %d container workload(s)",
            len(containers),
        )
        return {"containers": containers}

    def _auth_header(self) -> str:
        raw = f"{self.user}:{self.password}".encode("utf-8")
        return "Basic " + base64.b64encode(raw).decode("ascii")

    def _execute_query(
        self, cypher: str, parameters: dict[str, Any]
    ) -> list[list[Any]]:
        payload = {"statements": [{"statement": cypher, "parameters": parameters}]}
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
                f"Neo4j topology query failed with HTTP {exc.code}: {detail}"
            ) from exc
        except Exception as exc:
            raise RuntimeError(f"Neo4j topology query failed: {exc}") from exc

        if body.get("errors"):
            messages = [
                f"{item.get('code', 'unknown')}: {item.get('message', 'unknown error')}"
                for item in body["errors"]
            ]
            raise RuntimeError(
                f"Neo4j topology execution errors: {'; '.join(messages)}"
            )

        results = body.get("results", [])
        if not results:
            return []
        return [row.get("row", []) for row in results[0].get("data", [])]

    def _row_to_container(self, row: list[Any]) -> dict[str, Any]:
        container_id, name, image, env, labels, networks, ports, exposed_ports = row[:8]
        parsed_ports = self._parse_ports(exposed_ports) or self._parse_ports(ports)
        if not parsed_ports:
            parsed_ports = [{"number": 80, "protocol": "tcp"}]

        return {
            "id": str(container_id or ""),
            "name": self._sanitize_name(str(name or "container")),
            "image": str(image or ""),
            "env": self._parse_env(env),
            "labels": self._parse_env(labels),
            "networks": self._parse_networks(networks),
            "ports": parsed_ports,
        }

    @staticmethod
    def _sanitize_name(value: str) -> str:
        name = re.sub(r"[^a-z0-9-]+", "-", value.strip().lower())
        name = re.sub(r"-+", "-", name).strip("-")
        return name[:54] or "container"

    @staticmethod
    def _parse_env(value: Any) -> dict[str, str]:
        if isinstance(value, dict):
            return {str(key): str(item) for key, item in value.items() if str(key)}
        if not isinstance(value, list):
            return {}

        env: dict[str, str] = {}
        for item in value:
            if isinstance(item, str) and "=" in item:
                key, env_value = item.split("=", 1)
                key = key.strip()
                if key:
                    env[key] = env_value
        return env

    @staticmethod
    def _parse_ports(value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []

        ports: list[dict[str, Any]] = []
        seen: set[int] = set()
        for item in value:
            port_number: int | None = None
            protocol = "tcp"

            if isinstance(item, dict):
                raw_number = (
                    item.get("number")
                    or item.get("container_port")
                    or item.get("containerPort")
                    or item.get("port")
                )
                protocol = str(item.get("protocol") or "tcp").lower()
                try:
                    port_number = int(raw_number)
                except (TypeError, ValueError):
                    port_number = None
            elif isinstance(item, str):
                parts = item.split(":")
                try:
                    port_number = int(parts[0])
                except (IndexError, ValueError):
                    port_number = None
                if len(parts) > 1 and parts[1]:
                    protocol = parts[1].lower()

            if not port_number or port_number in seen:
                continue
            seen.add(port_number)
            ports.append({"number": port_number, "protocol": protocol})
        return ports

    @staticmethod
    def _parse_networks(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        networks = sorted({str(item).strip() for item in value if str(item).strip()})
        return networks


def build_sandbox_topology(
    company_id: str, target_ids: list[str] | None = None
) -> dict[str, Any]:
    return Neo4jSandboxTopologyService().build_sandbox_topology(
        company_id=company_id,
        target_ids=target_ids,
    )
