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
