import pytest
from unittest.mock import MagicMock, patch
import grpc
import uuid

from grpc_services.internal_auth import InternalAuthService
import aegis.v2.internal_auth_pb2 as internal_auth_pb2
from models.company import Company


@pytest.fixture
def auth_service():
    service = InternalAuthService()
    service._session_factory = MagicMock()
    return service


@pytest.fixture
def mock_db(auth_service):
    db = MagicMock()
    auth_service._session_factory.return_value.__enter__.return_value = db
    auth_service._session_factory.return_value.__exit__.return_value = False
    return db


@pytest.mark.asyncio
async def test_verify_token_success(auth_service, mock_db):
    company_id = uuid.uuid4()
    mock_company = Company(id=company_id, deployment_token="valid-token", is_active=True)
    
    mock_db.query.return_value.filter.return_value.first.return_value = mock_company

    request = internal_auth_pb2.VerifyTokenRequest(token="valid-token")
    context = MagicMock()

    response = await auth_service.VerifyToken(request, context)

    assert response.valid is True
    assert response.tenant_id == str(company_id)


@pytest.mark.asyncio
async def test_verify_token_invalid(auth_service, mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None

    request = internal_auth_pb2.VerifyTokenRequest(token="invalid-token")
    context = MagicMock()

    response = await auth_service.VerifyToken(request, context)

    assert response.valid is False
    assert response.tenant_id == ""


@pytest.mark.asyncio
async def test_verify_token_inactive_company(auth_service, mock_db):
    company_id = uuid.uuid4()
    mock_company = Company(id=company_id, deployment_token="inactive-token", is_active=False)
    
    # The current implementation filters by is_active=True in the query, 
    # so first() will return None if filtered in query, or we can mock the behavior.
    mock_db.query.return_value.filter.return_value.first.return_value = None

    request = internal_auth_pb2.VerifyTokenRequest(token="inactive-token")
    context = MagicMock()

    response = await auth_service.VerifyToken(request, context)

    assert response.valid is False


@pytest.mark.asyncio
async def test_verify_token_empty_request(auth_service):
    request = internal_auth_pb2.VerifyTokenRequest(token="")
    context = MagicMock()

    response = await auth_service.VerifyToken(request, context)

    assert response.valid is False


@pytest.mark.asyncio
async def test_verify_token_db_error(auth_service, mock_db):
    mock_db.query.side_effect = Exception("DB Connection Error")

    request = internal_auth_pb2.VerifyTokenRequest(token="any-token")
    context = MagicMock()

    response = await auth_service.VerifyToken(request, context)

    assert response.valid is False
    context.set_code.assert_called_with(grpc.StatusCode.INTERNAL)
