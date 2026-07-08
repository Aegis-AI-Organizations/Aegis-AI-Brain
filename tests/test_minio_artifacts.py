from unittest.mock import MagicMock, patch

import pytest

from activities.minio_artifacts import (
    _artifact_payload,
    download_minio_artifact,
    parse_minio_reference,
)


def test_parse_minio_reference_supports_explicit_and_default_bucket():
    assert parse_minio_reference("minio://bucket/path/file.json") == (
        "bucket",
        "path/file.json",
    )
    assert parse_minio_reference("s3://bucket/path/file.json") == (
        "bucket",
        "path/file.json",
    )
    assert parse_minio_reference("minio:path/file.json") == (
        "aegis-ingest",
        "path/file.json",
    )
    assert parse_minio_reference("nginx:latest") is None


def test_artifact_payload_maps_topology_json_to_sandbox_request():
    payload = _artifact_payload(
        "bucket",
        "target.json",
        '{"target_image":"topology:minio","topology":{"containers":[],"databaseSchemas":[],"externalMocks":[]},"preferred_endpoint_workload":"web"}',
    )

    assert payload["target_image"] == "topology:minio"
    assert payload["sandbox_request"]["preferred_endpoint_workload"] == "web"
    assert (
        payload["sandbox_request"]["topology_json"]
        == '{"containers":[],"databaseSchemas":[],"externalMocks":[]}'
    )


@pytest.mark.asyncio
async def test_download_minio_artifact_reads_object_and_returns_deployable_payload():
    response = MagicMock()
    response.read.return_value = b'{"target_image":"nginx:latest"}'
    client = MagicMock()
    client.get_object.return_value = response

    with patch("activities.minio_artifacts.Minio", return_value=client):
        payload = await download_minio_artifact("minio://bucket/target.json")

    client.get_object.assert_called_once_with("bucket", "target.json")
    response.close.assert_called_once()
    response.release_conn.assert_called_once()
    assert payload["target_image"] == "nginx:latest"
