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
        Neo4jSandboxTopologyService,
        "_execute_query",
        side_effect=[rows, route_rows, []],
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
        side_effect=[[["id", "worker", "worker:latest", [], [], [], [], []]], [], []],
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
        Neo4jSandboxTopologyService,
        "_execute_query",
        side_effect=[rows, route_rows, []],
    ):
        service = Neo4jSandboxTopologyService(
            url="http://neo4j.local:7474", user="neo4j", password="secret"
        )
        topology = service.build_sandbox_topology("company-1")

    assert topology["routes"] == [{"source": "api", "target": "postgres"}]


def test_build_sandbox_topology_loads_database_schemas_for_route_selected_containers():
    rows = [
        [
            "company:agent:web-graph-id",
            "portfolio.web",
            "portfolio-web:latest",
            [],
            [],
            [],
            ["8080:tcp:::8080:docker"],
            [],
            "",
            "",
            "web-raw-id",
            "portfolio.web",
        ],
        [
            "company:agent:db-graph-id",
            "portfolio.db",
            "postgres:16",
            [],
            [],
            [],
            ["5432:tcp:::5432:docker"],
            [],
            "",
            "",
            "db-raw-id",
            "portfolio.db",
        ],
    ]
    route_rows = [["portfolio.web", "portfolio.db", "compose"]]
    schema_rows = [
        [
            "postgres",
            "portfolio-db",
            5432,
            "portfolio",
            "portfolio",
            "db-raw-id",
            "portfolio.db",
        ]
    ]

    with patch.object(
        Neo4jSandboxTopologyService,
        "_execute_query",
        side_effect=[rows, route_rows, schema_rows],
    ) as mock_query:
        service = Neo4jSandboxTopologyService(
            url="http://neo4j.local:7474", user="neo4j", password="secret"
        )
        topology = service.build_sandbox_topology("company-1", target_ids=["route-1"])

    database_call = mock_query.call_args_list[2]
    database_cypher = database_call.args[0]
    database_parameters = database_call.args[1]
    assert "$target_ids" not in database_cypher
    assert database_parameters["source_container_ids"] == [
        "company:agent:db-graph-id",
        "company:agent:web-graph-id",
        "db-raw-id",
        "web-raw-id",
    ]
    assert database_parameters["source_container_names"] == [
        "portfolio-db",
        "portfolio-web",
        "portfolio.db",
        "portfolio.web",
    ]
    assert topology["databaseSchemas"] == [
        {
            "engine": "postgres",
            "host": "portfolio-db",
            "port": 5432,
            "databaseName": "portfolio",
            "username": "portfolio",
            "sourceContainerId": "db-raw-id",
            "sourceContainerName": "portfolio.db",
        }
    ]
    db_container = next(
        item
        for item in topology["containers"]
        if item["id"] == "company:agent:db-graph-id"
    )
    assert db_container == {
        "id": "company:agent:db-graph-id",
        "name": "portfolio-db",
        "image": "postgres:16",
        "env": {},
        "labels": {},
        "networks": [],
        "ports": [{"number": 5432, "protocol": "tcp"}],
    }
    assert all(
        key in {"id", "name", "image", "env", "labels", "networks", "ports"}
        for container in topology["containers"]
        for key in container
    )
