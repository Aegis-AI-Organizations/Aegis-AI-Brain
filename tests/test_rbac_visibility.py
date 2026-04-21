import pytest
from unittest.mock import MagicMock, patch
import uuid

from grpc_services.company import CompanyService
from grpc_services.scans import ScanService
import aegis.v2.company_pb2 as company_pb2
import aegis.v2.scan_pb2 as scan_pb2
from models.company import Company
from models.user import User


@pytest.fixture
def company_service():
    service = CompanyService()
    service._session_factory = MagicMock()
    return service


@pytest.fixture
def scan_service():
    service = ScanService(temporal_client=MagicMock())
    return service


@pytest.fixture
def mock_db(company_service):
    db = MagicMock()
    company_service._session_factory.return_value.__enter__.return_value = db
    company_service._session_factory.return_value.__exit__.return_value = False
    return db


@pytest.mark.asyncio
async def test_list_companies_owner_visibility(company_service, mock_db):
    owner_company_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    owner = User(id=owner_id, email="owner@test.com", company_id=owner_company_id)

    # Mock company returned by DB
    c1 = Company(id=owner_company_id, name="Owner Co", owner=owner, members=[])

    # Mocking the query chain for list-companies
    mock_db.query.return_value.options.return_value.filter.return_value.all.return_value = [
        c1
    ]

    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {
            "user_id": str(owner_id),
            "role": "owner",
            "company_id": str(owner_company_id),
        }

        # x-action: list-companies
        metadata = (("x-action", "list-companies"),)
        request = company_pb2.ListCompaniesRequest()
        context = MagicMock()
        context.invocation_metadata.return_value = metadata

        response = await company_service.ListCompanies(request, context)

        # Check response
        assert len(response.companies) == 1
        assert response.companies[0].name == "Owner Co"

        # Verify filter was called with the correct company_id
        # The chain is db.query(Company).options(...).filter(Company.id == company_id)
        mock_db.query.return_value.options.return_value.filter.assert_called_once()
        filter_args = mock_db.query.return_value.options.return_value.filter.call_args[
            0
        ][0]
        # Check that it filters by ID
        assert "id =" in str(filter_args)


@pytest.mark.asyncio
async def test_list_users_owner_visibility(company_service, mock_db):
    owner_company_id = uuid.uuid4()
    owner_id = uuid.uuid4()

    # Mock users returned by DB
    u1 = User(
        id=uuid.uuid4(),
        name="User 1",
        email="u1@test.com",
        company_id=owner_company_id,
        role="viewer",
    )

    # Mock query chain for list-users
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
        u1
    ]

    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {
            "user_id": str(owner_id),
            "role": "owner",
            "company_id": str(owner_company_id),
        }

        # x-action: list-users, x-company-id matches owner's
        metadata = (("x-action", "list-users"), ("x-company-id", str(owner_company_id)))
        request = company_pb2.ListCompaniesRequest()
        context = MagicMock()
        context.invocation_metadata.return_value = metadata

        response = await company_service.ListCompanies(request, context)

        assert len(response.companies) == 1
        assert response.companies[0].name == "User 1"
        mock_db.query.return_value.filter.assert_called_once()


@pytest.mark.asyncio
async def test_list_scans_superadmin_visibility(scan_service):
    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {"user_id": str(uuid.uuid4()), "role": "superadmin"}

        # Mock DB results
        mock_scans = [
            (str(uuid.uuid4()), "workflow-1", "image:latest", "COMPLETED", None, None)
        ]

        with patch.object(
            scan_service, "_list_scans_db", return_value=mock_scans
        ) as mock_db_list:
            request = scan_pb2.ListScansRequest()
            context = MagicMock()

            response = await scan_service.ListScans(request, context)

            assert len(response.scans) == 1
            # Verify called with None company_id for superadmin
            mock_db_list.assert_called_once_with(None)


@pytest.mark.asyncio
async def test_list_scans_restricted_visibility(scan_service):
    company_id = str(uuid.uuid4())
    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {
            "user_id": str(uuid.uuid4()),
            "role": "operateur",
            "company_id": company_id,
        }

        with patch.object(
            scan_service, "_list_scans_db", return_value=[]
        ) as mock_db_list:
            request = scan_pb2.ListScansRequest()
            context = MagicMock()

            await scan_service.ListScans(request, context)

            # Verify called with company_id for restricted role
            mock_db_list.assert_called_once_with(company_id)
