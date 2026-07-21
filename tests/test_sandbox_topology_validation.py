import pytest

from services.sandbox_topology_validation import (
    SandboxTopologyValidationError,
    validate_sandbox_topology_request,
)


def test_validate_sandbox_topology_request_accepts_formal_contract():
    validate_sandbox_topology_request(
        {
            "scan_id": "scan-1",
            "topology": {
                "containers": [
                    {
                        "name": "web",
                        "image": "nginx:latest",
                        "ports": [{"number": 80, "protocol": "tcp"}],
                    }
                ],
                "databaseSchemas": [],
                "externalMocks": [
                    {
                        "host": "api.example.test",
                        "routes": [
                            {
                                "method": "GET",
                                "path": "/health",
                                "status": 200,
                                "headers": {"X-Mock": "true"},
                                "body": "{}",
                                "latency": "250ms",
                            }
                        ],
                    }
                ],
            },
        }
    )


def test_validate_sandbox_topology_request_accepts_workloads_contract():
    validate_sandbox_topology_request(
        {
            "scan_id": "scan-1",
            "topology": {
                "workloads": [
                    {
                        "name": "api",
                        "image": "ghcr.io/aegis/api:latest",
                        "ports": [{"number": 8080, "protocol": "tcp"}],
                        "depends_on": ["postgres"],
                    }
                ],
                "databaseSchemas": [
                    {
                        "engine": "postgresql",
                        "host": "postgres",
                        "port": 5432,
                        "databaseName": "app",
                        "tables": [
                            {
                                "name": "users",
                                "columns": [
                                    {
                                        "name": "id",
                                        "data_type": "integer",
                                        "primary_key": True,
                                    }
                                ],
                            }
                        ],
                    }
                ],
                "externalMocks": [],
            },
        }
    )


def test_validate_sandbox_topology_request_rejects_malformed_topology():
    with pytest.raises(SandboxTopologyValidationError) as exc_info:
        validate_sandbox_topology_request(
            {
                "scan_id": "scan-1",
                "topology_json": '{"containers":[{"name":"web","image":"nginx","ports":[{"number":"80"}]}],"databaseSchemas":[],"externalMocks":[]}',
            }
        )

    assert "Invalid sandbox topology" in str(exc_info.value)
    assert "containers.0.ports.0.number" in str(exc_info.value)


def test_validate_sandbox_topology_request_rejects_missing_required_fields():
    with pytest.raises(SandboxTopologyValidationError) as exc_info:
        validate_sandbox_topology_request(
            {
                "scan_id": "scan-1",
                "topology": {"containers": []},
            }
        )

    assert "databaseSchemas" in str(exc_info.value)
