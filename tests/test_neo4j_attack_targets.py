from unittest.mock import patch

from services.neo4j_attack_targets import Neo4jAttackTargetService


def test_identify_attack_targets_orders_and_normalizes_paths():
    rows = [
        [
            "entry-2",
            "public-web-2",
            "",
            "target-2",
            "redis-cache",
            "cache-ns",
            "service",
            "metrics",
            1,
            90,
        ],
        [
            "entry-1",
            "public-web-1",
            "/",
            "target-1",
            "postgres-db",
            "db-ns",
            "service",
            "admin",
            2,
            100,
        ],
    ]

    with patch.object(
        Neo4jAttackTargetService, "_execute_query", return_value=rows
    ) as mock_query:
        service = Neo4jAttackTargetService(
            url="http://neo4j.local:7474", user="neo4j", password="secret"
        )
        targets = service.identify_attack_targets("company-1")

    assert mock_query.called
    assert len(targets) == 2
    assert targets[0]["target_name"] == "postgres-db"
    assert targets[0]["target_path"] == "/admin"
    assert targets[0]["path_length"] == 2
    assert targets[1]["target_name"] == "redis-cache"
    assert targets[1]["target_path"] == "/metrics"


def test_identify_attack_targets_uses_valid_shortest_path_relationship_syntax():
    captured = {}

    def fake_execute_query(cypher, parameters):
        captured["cypher"] = cypher
        captured["parameters"] = parameters
        return []

    with patch.object(
        Neo4jAttackTargetService, "_execute_query", side_effect=fake_execute_query
    ):
        service = Neo4jAttackTargetService(
            url="http://neo4j.local:7474", user="neo4j", password="secret"
        )
        targets = service.identify_attack_targets("company-1", agent_id="agent-1")

    assert targets == []
    assert "[:ROUTE_FROM|ROUTE_TO*..8]" in captured["cypher"]
    assert "[:ROUTE_FROM|:ROUTE_TO*..8]" not in captured["cypher"]
    assert captured["parameters"]["company_id"] == "company-1"
    assert captured["parameters"]["agent_id"] == "agent-1"


def test_identify_attack_targets_sends_null_agent_id_when_missing():
    captured = {}

    def fake_execute_query(cypher, parameters):
        captured["parameters"] = parameters
        return []

    with patch.object(
        Neo4jAttackTargetService, "_execute_query", side_effect=fake_execute_query
    ):
        service = Neo4jAttackTargetService(
            url="http://neo4j.local:7474", user="neo4j", password="secret"
        )
        service.identify_attack_targets("company-1")

    assert "agent_id" in captured["parameters"]
    assert captured["parameters"]["agent_id"] is None
