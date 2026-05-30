import pytest
import uuid
from unittest.mock import MagicMock, patch
from grpc_services.company import CompanyService
from grpc_services.auth import AuthService, AuthErrorCode
from aegis.v2 import company_pb2, auth_pb2


@pytest.mark.asyncio
async def test_company_search_with_query():
    service = CompanyService(email_service=MagicMock())

    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {"user_id": str(uuid.uuid4()), "role": "superadmin"}

        with patch.object(
            service, "_list_entities_db_sync", return_value=[]
        ) as mock_db:
            request = company_pb2.ListCompaniesRequest()
            context = MagicMock()
            context.invocation_metadata.return_value = [("x-query", "test-search")]

            await service.ListCompanies(request, context)

            mock_db.assert_called_once()
            args = mock_db.call_args[0]
            assert args[0] == "test-search"


@pytest.mark.asyncio
async def test_auth_update_profile_success():
    service = AuthService()

    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {"user_id": str(uuid.uuid4()), "role": "operator"}

        with patch.object(
            service, "_update_profile_db_sync", return_value=AuthErrorCode.SUCCESS
        ) as mock_db:
            request = auth_pb2.UpdateProfileRequest(
                name="New Name", avatar_url="http://new.avatar"
            )
            context = MagicMock()

            response = await service.UpdateProfile(request, context)
            assert response.success is True
            mock_db.assert_called_once()


@pytest.mark.asyncio
async def test_auth_update_email_success():
    service = AuthService()

    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {"user_id": str(uuid.uuid4()), "role": "operator"}

        with patch.object(
            service, "_update_email_db_sync", return_value=AuthErrorCode.SUCCESS
        ) as mock_db:
            request = auth_pb2.UpdateEmailRequest(new_email="new@example.com")
            context = MagicMock()

            response = await service.UpdateEmail(request, context)
            assert response.success is True
            mock_db.assert_called_once()


@pytest.mark.asyncio
async def test_auth_update_password_success():
    service = AuthService()

    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {"user_id": str(uuid.uuid4()), "role": "operator"}

        with patch.object(
            service, "_update_password_db_sync", return_value=AuthErrorCode.SUCCESS
        ) as mock_db:
            request = auth_pb2.UpdatePasswordRequest(
                old_password="old", new_password="new"
            )
            context = MagicMock()

            response = await service.UpdatePassword(request, context)
            assert response.success is True
            mock_db.assert_called_once()


@pytest.mark.asyncio
async def test_auth_remove_avatar_success():
    service = AuthService()

    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {"user_id": str(uuid.uuid4()), "role": "operator"}

        with patch.object(
            service, "_remove_avatar_db_sync", return_value=AuthErrorCode.SUCCESS
        ) as mock_db:
            request = auth_pb2.RemoveAvatarRequest()
            context = MagicMock()

            response = await service.RemoveAvatar(request, context)
            assert response.success is True
            mock_db.assert_called_once()


@pytest.mark.asyncio
async def test_company_list_owner_visibility():
    service = CompanyService(email_service=MagicMock())
    company_id = str(uuid.uuid4())

    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {
            "user_id": str(uuid.uuid4()),
            "role": "owner",
            "company_id": company_id,
        }

        with patch.object(
            service, "_list_entities_db_sync", return_value=[]
        ) as mock_db:
            request = company_pb2.ListCompaniesRequest()
            context = MagicMock()
            context.invocation_metadata.return_value = [("x-action", "list-companies")]

            await service.ListCompanies(request, context)

            mock_db.assert_called_once()
            assert mock_db.call_args[0][2] == company_id
