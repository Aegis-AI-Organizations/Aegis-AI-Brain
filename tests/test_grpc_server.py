import pytest
from aegis.v1 import ping_pb2, scan_pb2
from grpc_server import PingService, ScanService


@pytest.mark.asyncio
async def test_ping_service():
    servicer = PingService()
    request = ping_pb2.PingRequest()
    response = await servicer.Ping(request, None)
    assert response.message == "pong"


@pytest.mark.asyncio
async def test_scan_service_start():
    servicer = ScanService()
    request = scan_pb2.StartScanRequest(target_image="nginx:latest")
    response = await servicer.StartScan(request, None)
    assert response.scan_id == "proto-scan-id"
    assert response.status == "PENDING"


@pytest.mark.asyncio
async def test_scan_service_status():
    servicer = ScanService()
    request = scan_pb2.GetScanStatusRequest(scan_id="test-id")
    response = await servicer.GetScanStatus(request, None)
    assert response.scan_id == "test-id"
    assert response.status == "COMPLETED"
