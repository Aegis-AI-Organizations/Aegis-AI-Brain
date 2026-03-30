import pytest
from unittest.mock import MagicMock
import grpc
from datetime import datetime, timedelta, timezone
import hashlib

from grpc_services.auth import AuthService
import aegis.v2.auth_pb2 as auth_pb2
from models.user import User
from models.refresh_token import RefreshToken
from utils.auth_utils import hash_password


@pytest.fixture
def auth_service():
    service = AuthService()
    service.session_factory = MagicMock()
    return service


@pytest.fixture
def mock_db(auth_service):
    db = MagicMock()
    auth_service.session_factory.return_value.__enter__.return_value = db
    return db


@pytest.mark.asyncio
async def test_login_success(auth_service, mock_db):
    password = "password123"
    pwd_hash = hash_password(password)
    user = User(
        id=1,
        email="test@example.com",
        password_hash=pwd_hash,
        is_active=True,
        role="user",
    )
    mock_db.query.return_value.filter.return_value.first.return_value = user

    request = auth_pb2.LoginRequest(email="test@example.com", password=password)
    context = MagicMock()

    response = await auth_service.Login(request, context)

    assert response.access_token != ""
    assert response.refresh_token != ""
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_login_invalid_credentials(auth_service, mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None

    request = auth_pb2.LoginRequest(email="wrong@example.com", password="any")
    context = MagicMock()

    response = await auth_service.Login(request, context)

    context.set_code.assert_called_with(grpc.StatusCode.UNAUTHENTICATED)
    assert response.access_token == ""


@pytest.mark.asyncio
async def test_login_inactive_user(auth_service, mock_db):
    user = User(
        id=1,
        email="test@example.com",
        password_hash=hash_password("pw"),
        is_active=False,
    )
    mock_db.query.return_value.filter.return_value.first.return_value = user

    request = auth_pb2.LoginRequest(email="test@example.com", password="pw")
    context = MagicMock()

    await auth_service.Login(request, context)
    context.set_code.assert_called_with(grpc.StatusCode.PERMISSION_DENIED)


@pytest.mark.asyncio
async def test_refresh_success(auth_service, mock_db):
    user = User(id=1, email="test@example.com", role="user")
    token = RefreshToken(
        token_hash=hashlib.sha256("valid_token".encode()).hexdigest(),
        user=user,
        revoked=False,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    mock_db.query.return_value.filter.return_value.first.return_value = token

    request = auth_pb2.RefreshRequest(refresh_token="valid_token")
    context = MagicMock()

    response = await auth_service.Refresh(request, context)
    assert response.access_token != ""


@pytest.mark.asyncio
async def test_refresh_revoked_token(auth_service, mock_db):
    token = RefreshToken(
        revoked=True, expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    mock_db.query.return_value.filter.return_value.first.return_value = token

    request = auth_pb2.RefreshRequest(refresh_token="revoked_token")
    context = MagicMock()

    await auth_service.Refresh(request, context)
    context.set_code.assert_called_with(grpc.StatusCode.UNAUTHENTICATED)


@pytest.mark.asyncio
async def test_logout(auth_service, mock_db):
    token = RefreshToken(token_hash="hash", revoked=False)
    mock_db.query.return_value.filter.return_value.first.return_value = token

    request = auth_pb2.LogoutRequest(refresh_token="token")
    context = MagicMock()

    response = await auth_service.Logout(request, context)
    assert response.success is True
    assert token.revoked is True
    mock_db.commit.assert_called_once()
