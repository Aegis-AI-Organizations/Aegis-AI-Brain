import asyncio
import grpc
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from aegis.v2 import ping_pb2, scan_pb2, vulnerability_pb2
from grpc_services.ping import PingService
from grpc_services.scans import ScanService
from grpc_services.vulnerabilities import VulnerabilityService
from grpc_services.utils import verified_identity


class MockContext:
    def __init__(self, metadata=None):
        self._metadata = metadata or [
            ("company-id", "test-company"),
            ("user-id", "test-user"),
            ("role", "operator"),
        ]
        metadata_map = dict(self._metadata)
        if metadata_map.get("user-id") and metadata_map.get("company-id"):
            verified_identity.set(
                {
                    "user_id": metadata_map.get("user-id"),
                    "company_id": metadata_map.get("company-id"),
                    "role": metadata_map.get("role"),
                }
            )
        else:
            verified_identity.set(None)
        self.abort = MagicMock(side_effect=grpc.RpcError("Aborted"))

    def invocation_metadata(self):
        return self._metadata


@pytest.mark.asyncio
async def test_ping_service():
    servicer = PingService()
    request = ping_pb2.PingRequest()
    response = await servicer.Ping(request, MockContext())
    assert response.message == "pong"


@pytest.mark.asyncio
@patch("grpc_services.scans.get_db_connection")
async def test_scan_service_start(mock_get_db):
    mock_conn = mock_get_db.return_value
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchone.return_value = (datetime.now(),)

    temporal_client = AsyncMock()
    servicer = ScanService(temporal_client)
    request = scan_pb2.StartScanRequest(target_image="nginx:latest")
    response = await servicer.StartScan(request, MockContext())
    assert response.status == "PENDING"
    assert response.scan_id != ""
    assert response.started_at is not None


@pytest.mark.asyncio
@patch("grpc_services.scans.get_db_connection")
async def test_scan_service_status(mock_get_db):
    mock_conn = mock_get_db.return_value
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchone.return_value = (
        "COMPLETED",
        datetime.now(),
        datetime.now(),
        "nginx:latest",
        "wf-1",
    )

    temporal_client = AsyncMock()
    servicer = ScanService(temporal_client)
    request = scan_pb2.GetScanStatusRequest(scan_id="test-id")
    response = await servicer.GetScanStatus(request, MockContext())
    assert response.scan_id == "test-id"
    assert response.status == "COMPLETED"


@pytest.mark.asyncio
@patch("grpc_services.scans.get_db_connection")
async def test_scan_service_list(mock_get_db):
    mock_conn = mock_get_db.return_value
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchall.return_value = [
        ("test-id", "wf-1", "nginx", "COMPLETED", datetime.now(), None, "Company X")
    ]

    temporal_client = AsyncMock()
    servicer = ScanService(temporal_client)
    request = scan_pb2.ListScansRequest()
    response = await servicer.ListScans(request, MockContext())
    assert len(response.scans) == 1
    assert response.scans[0].scan_id == "test-id"


@pytest.mark.asyncio
@patch("grpc_services.scans.get_db_connection")
async def test_scan_service_report(mock_get_db):
    mock_conn = mock_get_db.return_value
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchone.return_value = (b"fake-pdf",)

    temporal_client = AsyncMock()
    servicer = ScanService(temporal_client)
    request = scan_pb2.GetScanReportRequest(scan_id="test-id")
    response = await servicer.GetScanReport(request, MockContext())
    assert response.pdf_data == b"fake-pdf"


@pytest.mark.asyncio
@patch("grpc_services.vulnerabilities.get_db_connection")
async def test_vulnerability_service_get(mock_get_db):
    mock_conn = mock_get_db.return_value
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchall.return_value = [
        ("v-1", "SQLi", "HIGH", "/", "desc", datetime.now())
    ]

    servicer = VulnerabilityService()
    request = vulnerability_pb2.GetVulnerabilitiesRequest(scan_id="test-id")
    response = await servicer.GetVulnerabilities(request, MockContext())
    assert len(response.vulnerabilities) == 1
    assert response.vulnerabilities[0].id == "v-1"


@pytest.mark.asyncio
@patch("grpc_services.vulnerabilities.get_db_connection")
async def test_vulnerability_service_evidences(mock_get_db):
    mock_conn = mock_get_db.return_value
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchall.return_value = [
        ("e-1", "1=1", '{"data":"test"}', datetime.now())
    ]

    servicer = VulnerabilityService()
    request = vulnerability_pb2.GetEvidencesRequest(vulnerability_id="v-1")
    response = await servicer.GetEvidences(request, MockContext())
    assert len(response.evidences) == 1
    assert response.evidences[0].id == "e-1"


@pytest.mark.asyncio
@patch("grpc_services.scans.get_db_connection")
async def test_scan_service_start_failure_compensation(mock_get_db):
    mock_conn = mock_get_db.return_value
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchone.return_value = (datetime.now(),)

    temporal_client = AsyncMock()
    temporal_client.start_workflow.side_effect = Exception("Temporal error")

    servicer = ScanService(temporal_client)
    request = scan_pb2.StartScanRequest(target_image="nginx:latest")

    context = MockContext()
    with pytest.raises(grpc.RpcError):
        await servicer.StartScan(request, context)
    # Verify compensation update was called
    assert mock_cursor.execute.call_count >= 2


@pytest.mark.asyncio
@patch("grpc_services.scans.get_db_connection")
async def test_scan_service_status_not_found(mock_get_db):
    mock_conn = mock_get_db.return_value
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchone.return_value = None

    servicer = ScanService(AsyncMock())
    request = scan_pb2.GetScanStatusRequest(scan_id="missing-id")
    context = MockContext()

    with pytest.raises(grpc.RpcError):
        await servicer.GetScanStatus(request, context)
    context.abort.assert_called_once_with(
        grpc.StatusCode.NOT_FOUND, "Scan not found or access denied"
    )


@pytest.mark.asyncio
@patch("grpc_services.scans.get_db_connection")
async def test_scan_service_watch_status(mock_get_db):
    from grpc_services.broadcaster import broadcaster

    # Mock status for watch ownership check
    mock_conn = mock_get_db.return_value
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchone.return_value = (
        "RUNNING",
        datetime.now(),
        None,
        "nginx",
        "wf-1",
    )

    servicer = ScanService(AsyncMock())
    request = scan_pb2.WatchScanStatusRequest(scan_id="test-id")

    # Simulate a background update
    async def simulate_update():
        await asyncio.sleep(0.1)
        broadcaster.broadcast("scan", ("test-id", "COMPLETED"))
        # Send a different one to check filtering
        broadcaster.broadcast("scan", ("other-id", "RUNNING"))

    asyncio.create_task(simulate_update())

    stream = servicer.WatchScanStatus(request, MockContext())
    async for response in stream:
        if response.scan_id == "ping":
            continue
        assert response.scan_id == "test-id"
        assert response.status == "COMPLETED"
        break  # Only expect one for this test
