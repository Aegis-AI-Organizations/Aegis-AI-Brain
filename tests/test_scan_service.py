import pytest
from unittest.mock import MagicMock, patch
import grpc
import uuid

from grpc_services.scans import ScanService
import aegis.v2.scan_pb2 as scan_pb2


@pytest.fixture
def scan_service():
    temporal_client = MagicMock()
    service = ScanService(temporal_client)
    return service


@pytest.mark.asyncio
async def test_update_scan_status_success(scan_service):
    scan_id = str(uuid.uuid4())
    company_id = str(uuid.uuid4())
    token = "ag_test_token"

    request = scan_pb2.UpdateScanStatusRequest(scan_id=scan_id, status="COMPLETED")
    context = MagicMock()
    context.invocation_metadata.return_value = [("authorization", f"Bearer {token}")]

    with patch(
        "grpc_services.internal_auth.InternalAuthService._verify_token_db_sync"
    ) as mock_verify, patch(
        "grpc_services.scans.ScanService._get_scan_status_db"
    ) as mock_get_status, patch(
        "grpc_services.scans._execute_status_update"
    ) as mock_execute:
        mock_verify.return_value = company_id
        mock_get_status.return_value = ("PENDING", None, None, "image", "wf")

        response = await scan_service.UpdateScanStatus(request, context)

        assert response.success is True
        mock_execute.assert_called_once_with(scan_id, "COMPLETED")


@pytest.mark.asyncio
async def test_update_scan_status_unauthenticated(scan_service):
    request = scan_pb2.UpdateScanStatusRequest(scan_id="s1", status="COMPLETED")
    context = MagicMock()
    context.invocation_metadata.return_value = []  # No token

    response = await scan_service.UpdateScanStatus(request, context)

    assert response.success is False
    context.set_code.assert_called_with(grpc.StatusCode.UNAUTHENTICATED)
