from unittest.mock import MagicMock, patch

from activities.database_seeding import (
    SEED_FLAG,
    DatabaseTarget,
    discover_postgres_targets,
    seed_postgres_target,
)


def test_discover_postgres_targets_from_kubernetes_services_and_pods():
    services = {
        "items": [
            {
                "metadata": {"name": "postgres"},
                "spec": {
                    "selector": {"app": "postgres"},
                    "ports": [{"name": "postgres", "port": 5432}],
                },
            },
            {
                "metadata": {"name": "api"},
                "spec": {"selector": {"app": "api"}, "ports": [{"port": 80}]},
            },
        ]
    }
    pods = {
        "items": [
            {
                "metadata": {"labels": {"app": "postgres"}},
                "spec": {
                    "containers": [
                        {
                            "image": "postgres:16",
                            "env": [
                                {"name": "POSTGRES_DB", "value": "appdb"},
                                {"name": "POSTGRES_USER", "value": "appuser"},
                                {"name": "POSTGRES_PASSWORD", "value": "secret"},
                            ],
                        }
                    ]
                },
            }
        ]
    }

    with patch(
        "activities.database_seeding._kubernetes_get", side_effect=[services, pods]
    ):
        targets = discover_postgres_targets("scan-1")

    assert targets == [
        DatabaseTarget(
            name="postgres",
            host="postgres.aegis-war-room-scan-1.svc.cluster.local",
            port=5432,
            database="appdb",
            user="appuser",
            password="secret",
        )
    ]


def test_seed_postgres_target_executes_standard_seed_ddl():
    conn = MagicMock()
    cursor = MagicMock()
    conn.__enter__.return_value = conn
    conn.cursor.return_value.__enter__.return_value = cursor
    target = DatabaseTarget(
        name="postgres",
        host="postgres.aegis-war-room-scan-1.svc.cluster.local",
        port=5432,
        database="postgres",
        user="postgres",
        password="postgres",
    )

    with patch(
        "activities.database_seeding.psycopg.connect", return_value=conn
    ) as connect:
        seed_postgres_target(target)

    connect.assert_called_once()
    create_call = cursor.execute.call_args_list[0].args
    insert_call = cursor.execute.call_args_list[1].args
    assert "CREATE TABLE IF NOT EXISTS users" in create_call[0]
    assert "admin@company.com" in insert_call[0]
    assert insert_call[1] == {"seed_flag": SEED_FLAG}
    conn.commit.assert_called_once()
