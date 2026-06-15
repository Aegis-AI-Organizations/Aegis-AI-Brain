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

    with patch.object(
        Neo4jSandboxTopologyService, "_execute_query", return_value=rows
    ) as mock_query:
        service = Neo4jSandboxTopologyService(
            url="http://neo4j.local:7474", user="neo4j", password="secret"
        )
        topology = service.build_sandbox_topology(
            "company-1", target_ids=["container-1"]
        )

    assert mock_query.called
    assert topology == {
        "containers": [
            {
                "name": "api-v1",
                "image": "ghcr.io/acme/api:latest",
                "env": {"PUBLIC_URL": "https://app.example.test"},
                "labels": {"com.docker.compose.service": "api"},
                "networks": ["backend"],
                "ports": [{"number": 8080, "protocol": "tcp"}],
            }
        ]
    }


def test_build_sandbox_topology_uses_default_http_port_when_missing():
    with patch.object(
        Neo4jSandboxTopologyService,
        "_execute_query",
        return_value=[["id", "worker", "worker:latest", [], [], [], [], []]],
    ):
        service = Neo4jSandboxTopologyService(
            url="http://neo4j.local:7474", user="neo4j", password="secret"
        )
        topology = service.build_sandbox_topology("company-1")

    assert topology["containers"][0]["ports"] == [{"number": 80, "protocol": "tcp"}]
