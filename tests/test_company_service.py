import pytest
from unittest.mock import MagicMock, patch
import grpc
import uuid
import asyncio

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


@pytest.mark.asyncio
async def test_onboard_company_success(company_service, mock_db):
    with patch("grpc_services.company.Company") as mock_company_cls, patch(
        "grpc_services.company.User"
    ) as mock_user_cls:
        mock_company = MagicMock()
        mock_company.id = uuid.uuid4()
        mock_company.name = "New Co"
        mock_company_cls.return_value = mock_company

        mock_owner = MagicMock()
        mock_owner.id = uuid.uuid4()
        mock_user_cls.return_value = mock_owner

        request = company_pb2.OnboardCompanyRequest(
            company_name="New Co",
            owner_name="Owner",
            owner_email="owner@test.com",
            owner_password="password",
        )
        context = MagicMock()

        response = await company_service.OnboardCompany(request, context)

        assert response.company_id == str(mock_company.id)
        assert response.owner_id == str(mock_owner.id)
        assert response.deployment_token != ""
        mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_watch_teams_success(company_service):
    from grpc_services.broadcaster import broadcaster

    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {"user_id": str(uuid.uuid4()), "role": "superadmin"}

        request = company_pb2.WatchTeamsRequest()
        context = MagicMock()

        # We need to simulate the queue and its response
        async def mock_stream():
            # Trigger an update in background
            async def trigger():
                await asyncio.sleep(0.1)
                broadcaster.broadcast("team", ("COMPANY_CREATED", "c1", "Company 1"))

            asyncio.create_task(trigger())

            stream = company_service.WatchTeams(request, context)
            async for resp in stream:
                yield resp
                break

        responses = []
        async for r in mock_stream():
            responses.append(r)

        assert len(responses) == 1
        assert responses[0].event_type == "COMPANY_CREATED"
        assert responses[0].entity_id == "c1"


@pytest.mark.asyncio
async def test_create_user_success(company_service, mock_db):
    with patch("grpc_services.company.User") as mock_user_cls:
        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_user_cls.return_value = mock_user

        # Mock metadata for hijacking
        mock_context = MagicMock()
        mock_context.invocation_metadata.return_value = [
            ("x-action", "create-user"),
            ("x-user-password", "pass123"),
            ("x-user-role", "admin"),
            ("x-company-id", str(uuid.uuid4())),
        ]

        with patch("grpc_services.utils.get_identity") as mock_get_id:
            mock_get_id.return_value = {
                "user_id": str(uuid.uuid4()),
                "role": "superadmin",
            }

            request = company_pb2.CreateCompanyRequest(
                name="New User", owner_email="user@test.com"
            )

            response = await company_service.CreateCompany(request, mock_context)

            assert response.id == str(mock_user.id)
            mock_db.commit.assert_called_once()
