import pytest
from unittest.mock import MagicMock, patch
import grpc
from datetime import datetime, timedelta, timezone
import hashlib
import uuid

from grpc_services.auth import AuthService
import aegis.v2.auth_pb2 as auth_pb2
import models.agent  # noqa: F401 - registers SQLAlchemy relationship targets.
from models.company import Company
from models.onboarding_invitation import OnboardingInvitation
from models.user import User, UserActivationStatus, UserRole
from models.refresh_token import RefreshToken
from utils.auth_utils import hash_password, verify_password
from utils.token_utils import hash_token


@pytest.fixture
def auth_service():
    service = AuthService()
    service._session_factory = MagicMock()
    return service


@pytest.fixture
def mock_db(auth_service):
    db = MagicMock()
    # Configure the session factory mock to return 'db' as a context manager
    auth_service._session_factory.return_value.__enter__.return_value = db
    # Ensure exceptions raised inside the with-block are propagated
    auth_service._session_factory.return_value.__exit__.return_value = False
    return db


@pytest.mark.asyncio
async def test_login_success(auth_service, mock_db):
    password = "password123"
    pwd_hash = hash_password(password)
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        password_hash=pwd_hash,
        is_active=True,
        role=UserRole.operateur,
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
        id=uuid.uuid4(),
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
async def test_login_db_error(auth_service, mock_db):
    password = "password123"
    pwd_hash = hash_password(password)
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        password_hash=pwd_hash,
        is_active=True,
        role=UserRole.operateur,
    )
    mock_db.query.return_value.filter.return_value.first.return_value = user
    mock_db.commit.side_effect = Exception("DB error")

    request = auth_pb2.LoginRequest(email="test@example.com", password=password)
    context = MagicMock()

    response = await auth_service.Login(request, context)

    context.set_code.assert_called_with(grpc.StatusCode.INTERNAL)
    mock_db.rollback.assert_called_once()
    assert response.access_token == ""


@pytest.mark.asyncio
async def test_refresh_success(auth_service, mock_db):
    user = User(id=uuid.uuid4(), email="test@example.com", role=UserRole.viewer)
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


@pytest.mark.asyncio
async def test_refresh_exception(auth_service, mock_db):
    mock_db.query.side_effect = Exception("Serious DB failure")

    request = auth_pb2.RefreshRequest(refresh_token="any")
    context = MagicMock()

    await auth_service.Refresh(request, context)
    context.set_code.assert_called_with(grpc.StatusCode.INTERNAL)


@pytest.mark.asyncio
async def test_logout_db_error(auth_service, mock_db):
    token = RefreshToken(token_hash="hash", revoked=False)
    mock_db.query.return_value.filter.return_value.first.return_value = token
    mock_db.commit.side_effect = Exception("DB commit fail")

    request = auth_pb2.LogoutRequest(refresh_token="token")
    context = MagicMock()

    response = await auth_service.Logout(request, context)
    assert response.success is False
    context.set_code.assert_called_with(grpc.StatusCode.INTERNAL)
    mock_db.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_logout_exception(auth_service, mock_db):
    mock_db.query.side_effect = Exception("Query fail")

    request = auth_pb2.LogoutRequest(refresh_token="token")
    context = MagicMock()

    response = await auth_service.Logout(request, context)
    assert response.success is False
    context.set_code.assert_called_with(grpc.StatusCode.INTERNAL)


@pytest.mark.asyncio
async def test_setup_password_success(auth_service, mock_db):
    company = Company(id=uuid.uuid4(), name="Acme Corp")
    user = User(
        id=uuid.uuid4(),
        company=company,
        company_id=company.id,
        email="owner@example.com",
        password_hash=hash_password("placeholder"),
        role=UserRole.owner,
        is_active=False,
        activation_status=UserActivationStatus.pending_activation,
    )
    invitation = OnboardingInvitation(
        user=user,
        token_hash=hash_token("aegis_inv_valid"),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = invitation

    request = auth_pb2.SetupPasswordRequest(
        invitation_token="aegis_inv_valid",
        new_password="NewStrongPassword123!",
    )
    context = MagicMock()

    with patch("grpc_services.auth.generate_opaque_token", return_value="ag_once"):
        response = await auth_service.SetupPassword(request, context)

    assert response.access_token != ""
    assert response.refresh_token != ""
    assert response.agent_token == "ag_once"
    assert company.deployment_token == hash_token("ag_once")
    assert user.is_active is True
    assert user.activation_status == UserActivationStatus.active
    assert verify_password("NewStrongPassword123!", user.password_hash)
    assert invitation.used_at is not None
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_setup_password_invalid_token(auth_service, mock_db):
    mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = None

    request = auth_pb2.SetupPasswordRequest(
        invitation_token="missing",
        new_password="NewStrongPassword123!",
    )
    context = MagicMock()

    response = await auth_service.SetupPassword(request, context)

    assert response.access_token == ""
    context.set_code.assert_called_with(grpc.StatusCode.UNAUTHENTICATED)


@pytest.mark.asyncio
async def test_setup_password_used_token(auth_service, mock_db):
    user = User(
        id=uuid.uuid4(),
        email="owner@example.com",
        password_hash=hash_password("placeholder"),
        role=UserRole.owner,
        is_active=False,
        activation_status=UserActivationStatus.pending_activation,
    )
    invitation = OnboardingInvitation(
        user=user,
        token_hash=hash_token("aegis_inv_used"),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        used_at=datetime.now(timezone.utc),
    )
    mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = invitation

    request = auth_pb2.SetupPasswordRequest(
        invitation_token="aegis_inv_used",
        new_password="NewStrongPassword123!",
    )
    context = MagicMock()

    response = await auth_service.SetupPassword(request, context)

    assert response.access_token == ""
    context.set_code.assert_called_with(grpc.StatusCode.UNAUTHENTICATED)


@pytest.mark.asyncio
async def test_setup_password_non_pending_user(auth_service, mock_db):
    company = Company(id=uuid.uuid4(), name="Acme Corp")
    user = User(
        id=uuid.uuid4(),
        company=company,
        company_id=company.id,
        email="owner@example.com",
        password_hash=hash_password("existing"),
        role=UserRole.owner,
        is_active=True,
        activation_status=UserActivationStatus.active,
    )
    invitation = OnboardingInvitation(
        user=user,
        token_hash=hash_token("aegis_inv_active"),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = invitation

    request = auth_pb2.SetupPasswordRequest(
        invitation_token="aegis_inv_active",
        new_password="NewStrongPassword123!",
    )
    context = MagicMock()

    response = await auth_service.SetupPassword(request, context)

    assert response.access_token == ""
    context.set_code.assert_called_with(grpc.StatusCode.UNAUTHENTICATED)
