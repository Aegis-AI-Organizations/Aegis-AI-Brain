import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from aegis.v2 import ping_pb2, scan_pb2, vulnerability_pb2
from grpc_server import PingService, ScanService, VulnerabilityService


@pytest.mark.asyncio
async def test_ping_service():
    servicer = PingService()
    request = ping_pb2.PingRequest()
    response = await servicer.Ping(request, None)
    assert response.message == "pong"


@pytest.mark.asyncio
@patch("grpc_server.get_db_connection")
async def test_scan_service_start(mock_get_db):
    temporal_client = AsyncMock()
    servicer = ScanService(temporal_client)
    request = scan_pb2.StartScanRequest(target_image="nginx:latest")
    response = await servicer.StartScan(request, None)
    assert response.status == "PENDING"
    assert response.scan_id != ""


@pytest.mark.asyncio
@patch("grpc_server.get_db_connection")
async def test_scan_service_status(mock_get_db):
    mock_conn = mock_get_db.return_value
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchone.return_value = ("COMPLETED", datetime.now(), datetime.now())

    temporal_client = AsyncMock()
    servicer = ScanService(temporal_client)
    request = scan_pb2.GetScanStatusRequest(scan_id="test-id")
    response = await servicer.GetScanStatus(request, None)
    assert response.scan_id == "test-id"
    assert response.status == "COMPLETED"


@pytest.mark.asyncio
@patch("grpc_server.get_db_connection")
async def test_scan_service_list(mock_get_db):
    mock_conn = mock_get_db.return_value
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchall.return_value = [
        ("test-id", "wf-1", "nginx", "COMPLETED", datetime.now(), None)
    ]

    temporal_client = AsyncMock()
    servicer = ScanService(temporal_client)
    request = scan_pb2.ListScansRequest()
    response = await servicer.ListScans(request, None)
    assert len(response.scans) == 1
    assert response.scans[0].scan_id == "test-id"


@pytest.mark.asyncio
@patch("grpc_server.get_db_connection")
async def test_scan_service_report(mock_get_db):
    mock_conn = mock_get_db.return_value
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchone.return_value = (b"fake-pdf",)

    temporal_client = AsyncMock()
    servicer = ScanService(temporal_client)
    request = scan_pb2.GetScanReportRequest(scan_id="test-id")
    response = await servicer.GetScanReport(request, None)
    assert response.pdf_data == b"fake-pdf"


@pytest.mark.asyncio
@patch("grpc_server.get_db_connection")
async def test_vulnerability_service_get(mock_get_db):
    mock_conn = mock_get_db.return_value
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchall.return_value = [
        ("v-1", "SQLi", "HIGH", "/", "desc", datetime.now())
    ]

    servicer = VulnerabilityService()
    request = vulnerability_pb2.GetVulnerabilitiesRequest(scan_id="test-id")
    response = await servicer.GetVulnerabilities(request, None)
    assert len(response.vulnerabilities) == 1
    assert response.vulnerabilities[0].id == "v-1"


@pytest.mark.asyncio
@patch("grpc_server.get_db_connection")
async def test_vulnerability_service_evidences(mock_get_db):
    mock_conn = mock_get_db.return_value
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchall.return_value = [
        ("e-1", "1=1", '{"data":"test"}', datetime.now())
    ]

    servicer = VulnerabilityService()
    request = vulnerability_pb2.GetEvidencesRequest(vulnerability_id="v-1")
    response = await servicer.GetEvidences(request, None)
    assert len(response.evidences) == 1
    assert response.evidences[0].id == "e-1"
