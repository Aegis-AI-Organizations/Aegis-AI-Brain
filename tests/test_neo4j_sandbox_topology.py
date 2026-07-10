from unittest.mock import patch

from services.neo4j_sandbox_topology import Neo4jSandboxTopologyService


def test_build_sandbox_topology_maps_containers_to_deployer_payload():
    rows = [
        [
            "company:agent:container-1",
            "api.v1",
            "ghcr.io/acme/api:latest",
            ["PUBLIC_URL=https://app.example.test"],
            ["com.docker.compose.service=api"],
            ["backend"],
            ["8080:tcp:::8080:docker"],
            [],
        ]
    ]
    route_rows = [["api.v1", "postgres", "docker_compose"]]

    with patch.object(
        Neo4jSandboxTopologyService, "_execute_query", side_effect=[rows, route_rows]
    ) as mock_query:
        service = Neo4jSandboxTopologyService(
            url="http://neo4j.local:7474", user="neo4j", password="secret"
        )
        topology = service.build_sandbox_topology(
            "company-1", target_ids=["container-1"]
        )

    assert mock_query.called
    cypher = mock_query.call_args_list[0].args[0]
    assert "r.rawId IN $target_ids" in cypher
    assert "r.targetName IN $target_ids" in cypher
    assert "r.sourceName IN $target_ids" in cypher
    assert topology == {
        "containers": [
            {
                "id": "company:agent:container-1",
                "name": "api-v1",
                "image": "ghcr.io/acme/api:latest",
                "env": {"PUBLIC_URL": "https://app.example.test"},
                "labels": {"com.docker.compose.service": "api"},
                "networks": ["backend"],
                "ports": [{"number": 8080, "protocol": "tcp"}],
            }
        ],
        "routes": [],
        "databaseSchemas": [],
        "externalMocks": [],
    }


def test_build_sandbox_topology_uses_default_http_port_when_missing():
    with patch.object(
        Neo4jSandboxTopologyService,
        "_execute_query",
        side_effect=[[["id", "worker", "worker:latest", [], [], [], [], []]], []],
    ):
        service = Neo4jSandboxTopologyService(
            url="http://neo4j.local:7474", user="neo4j", password="secret"
        )
        topology = service.build_sandbox_topology("company-1")

    assert topology["containers"][0]["ports"] == [{"number": 80, "protocol": "tcp"}]


def test_build_sandbox_topology_includes_known_workload_routes():
    rows = [
        ["api-id", "api", "api:latest", [], [], [], [], []],
        ["db-id", "postgres", "postgres:16", [], [], [], [], []],
    ]
    route_rows = [["api", "postgres", "compose"]]

    with patch.object(
        Neo4jSandboxTopologyService, "_execute_query", side_effect=[rows, route_rows]
    ):
        service = Neo4jSandboxTopologyService(
            url="http://neo4j.local:7474", user="neo4j", password="secret"
        )
        topology = service.build_sandbox_topology("company-1")

    assert topology["routes"] == [{"source": "api", "target": "postgres"}]
