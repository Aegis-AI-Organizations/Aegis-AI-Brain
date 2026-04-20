import pytest
from unittest.mock import MagicMock, patch
import grpc
import uuid

from grpc_services.auth import AuthService
import aegis.v2.auth_pb2 as auth_pb2
from models.user import User


@pytest.fixture
def auth_service():
    service = AuthService()
    service._session_factory = MagicMock()
    return service


@pytest.fixture
def mock_db(auth_service):
    db = MagicMock()
    auth_service._session_factory.return_value.__enter__.return_value = db
    auth_service._session_factory.return_value.__exit__.return_value = False
    return db


@pytest.mark.asyncio
async def test_update_profile_success(auth_service, mock_db):
    user_id = str(uuid.uuid4())
    user = User(id=user_id, name="Old Name")
    mock_db.query.return_value.filter.return_value.first.return_value = user

    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {"user_id": user_id, "role": "operator"}

        request = auth_pb2.UpdateProfileRequest(name="New Name")
        context = MagicMock()

        response = await auth_service.UpdateProfile(request, context)

        assert response.success is True
        assert user.name == "New Name"
        mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_email_conflict(auth_service, mock_db):
    user_id = str(uuid.uuid4())
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        User(id=uuid.uuid4(), email="existing@test.com"),  # Conflict check
        User(id=user_id, email="old@test.com"),  # User lookup
    ]

    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {"user_id": user_id, "role": "operator"}

        request = auth_pb2.UpdateEmailRequest(new_email="existing@test.com")
        context = MagicMock()

        response = await auth_service.UpdateEmail(request, context)

        assert response.success is False
        context.set_code.assert_called_with(grpc.StatusCode.ALREADY_EXISTS)


@pytest.mark.asyncio
async def test_update_password_invalid_old(auth_service, mock_db):
    from utils.auth_utils import hash_password

    user_id = str(uuid.uuid4())
    user = User(id=user_id, password_hash=hash_password("correct_password"))
    mock_db.query.return_value.filter.return_value.first.return_value = user

    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {"user_id": user_id, "role": "operator"}

        request = auth_pb2.UpdatePasswordRequest(
            old_password="wrong_password", new_password="new"
        )
        context = MagicMock()

        response = await auth_service.UpdatePassword(request, context)

        assert response.success is False
        context.set_code.assert_called_with(grpc.StatusCode.UNAUTHENTICATED)
