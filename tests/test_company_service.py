import pytest
from unittest.mock import MagicMock, patch
import grpc
import uuid

from grpc_services.company import CompanyService
import aegis.v2.company_pb2 as company_pb2
from models.company import Company
from models.user import User


@pytest.fixture
def company_service():
    service = CompanyService()
    service._session_factory = MagicMock()
    return service


@pytest.fixture
def mock_db(company_service):
    db = MagicMock()
    company_service._session_factory.return_value.__enter__.return_value = db
    company_service._session_factory.return_value.__exit__.return_value = False
    return db


@pytest.mark.asyncio
async def test_create_company_success(company_service, mock_db):
    owner_id = uuid.uuid4()
    owner = User(id=owner_id, email="owner@test.com")
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        owner,  # Owner lookup
        None,  # Name check
    ]

    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {"user_id": str(uuid.uuid4()), "role": "superadmin"}

        request = company_pb2.CreateCompanyRequest(
            name="New Co", owner_email="owner@test.com"
        )
        context = MagicMock()

        response = await company_service.CreateCompany(request, context)

        assert response.name == "New Co"
        mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_company_unauthorized(company_service, mock_db):
    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {"user_id": str(uuid.uuid4()), "role": "operator"}

        request = company_pb2.CreateCompanyRequest(
            name="Forbidden", owner_email="any@test.com"
        )
        context = MagicMock()

        await company_service.CreateCompany(request, context)
        context.set_code.assert_called_with(grpc.StatusCode.PERMISSION_DENIED)


@pytest.mark.asyncio
async def test_list_companies_superadmin_only(company_service, mock_db):
    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {"user_id": str(uuid.uuid4()), "role": "viewer"}

        request = company_pb2.ListCompaniesRequest()
        context = MagicMock()

        await company_service.ListCompanies(request, context)
        context.set_code.assert_called_with(grpc.StatusCode.PERMISSION_DENIED)


@pytest.mark.asyncio
async def test_list_companies_success(company_service, mock_db):
    owner = User(id=uuid.uuid4(), email="owner@test.com")
    c1 = Company(id=uuid.uuid4(), name="C1", owner=owner, members=[])
    mock_db.query.return_value.options.return_value.all.return_value = [c1]

    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {"user_id": str(uuid.uuid4()), "role": "superadmin"}

        request = company_pb2.ListCompaniesRequest()
        context = MagicMock()

        response = await company_service.ListCompanies(request, context)

        assert len(response.companies) == 1
        assert response.companies[0].name == "C1"
