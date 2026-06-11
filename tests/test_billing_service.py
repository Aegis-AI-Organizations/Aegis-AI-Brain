import pytest
from unittest.mock import MagicMock, patch
import grpc
import uuid

from grpc_services.billing import BillingService, can_adjust_tokens
import aegis.v2.billing_pb2 as billing_pb2


@pytest.fixture
def billing_service():
    service = BillingService()
    service._session_factory = MagicMock()
    return service


@pytest.fixture
def mock_db(billing_service):
    db = MagicMock()
    billing_service._session_factory.return_value.__enter__.return_value = db
    billing_service._session_factory.return_value.__exit__.return_value = False
    return db


@pytest.mark.asyncio
async def test_get_balance_success(billing_service, mock_db):
    company_id = str(uuid.uuid4())
    mock_company = MagicMock()
    mock_company.id = company_id
    mock_company.token_balance = 500
    mock_db.query.return_value.filter.return_value.first.return_value = mock_company

    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {
            "user_id": "u1",
            "company_id": company_id,
            "role": "owner",
        }

        request = billing_pb2.GetBalanceRequest(company_id=company_id)
        context = MagicMock()

        response = await billing_service.GetBalance(request, context)
        assert response.balance == 500
        assert response.company_id == company_id


@pytest.mark.asyncio
async def test_get_balance_unauthorized_cross_tenant(billing_service, mock_db):
    my_company_id = str(uuid.uuid4())
    other_company_id = str(uuid.uuid4())

    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {
            "user_id": "u1",
            "company_id": my_company_id,
            "role": "owner",
        }

        request = billing_pb2.GetBalanceRequest(company_id=other_company_id)
        context = MagicMock()

        await billing_service.GetBalance(request, context)
        context.set_code.assert_called_with(grpc.StatusCode.PERMISSION_DENIED)


@pytest.mark.asyncio
async def test_get_ledger_success(billing_service, mock_db):
    company_id = str(uuid.uuid4())
    mock_entry = MagicMock()
    mock_entry.id = uuid.uuid4()
    mock_entry.company_id = company_id
    mock_entry.amount = -50
    mock_entry.reason = "Scan cost"
    mock_entry.scan_id = uuid.uuid4()
    from datetime import datetime

    mock_entry.created_at = datetime.now()

    mock_query = mock_db.query.return_value.filter.return_value
    mock_query.count.return_value = 1
    mock_query.order_by.return_value.limit.return_value.offset.return_value.all.return_value = [
        mock_entry
    ]

    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {
            "user_id": "u1",
            "company_id": company_id,
            "role": "owner",
        }

        request = billing_pb2.GetLedgerRequest(
            company_id=company_id, limit=10, offset=0
        )
        context = MagicMock()

        response = await billing_service.GetLedger(request, context)
        assert response.total == 1
        assert len(response.entries) == 1
        assert response.entries[0].amount == -50
        assert response.entries[0].reason == "Scan cost"


def test_can_adjust_tokens_allows_own_scan_consumption():
    identity = {"user_id": "u1", "company_id": "company-1", "role": "owner"}

    assert can_adjust_tokens(identity, "company-1", -35)


def test_can_adjust_tokens_rejects_cross_tenant_consumption():
    identity = {"user_id": "u1", "company_id": "company-1", "role": "owner"}

    assert not can_adjust_tokens(identity, "company-2", -35)


def test_can_adjust_tokens_rejects_client_credit_adjustment():
    identity = {"user_id": "u1", "company_id": "company-1", "role": "owner"}

    assert not can_adjust_tokens(identity, "company-1", 35)


def test_can_adjust_tokens_allows_billing_roles():
    identity = {"user_id": "u1", "company_id": "company-1", "role": "superadmin"}

    assert can_adjust_tokens(identity, "company-2", 35)
