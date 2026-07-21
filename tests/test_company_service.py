import pytest
from unittest.mock import MagicMock, patch, AsyncMock, ANY
import grpc
import uuid
import asyncio

from grpc_services.company import CompanyService
import aegis.v2.company_pb2 as company_pb2
from models.company import Company
import models.agent  # noqa: F401 - registers SQLAlchemy relationship targets.
from models.onboarding_invitation import OnboardingInvitation
from models.user import User, UserActivationStatus, UserRole
from utils.token_utils import hash_token

VALID_AGENT_TOKEN = "ag_0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefg"


@pytest.fixture
def company_service():
    service = CompanyService(email_service=MagicMock())
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
    with patch("grpc_services.company.Company") as mock_company_cls:
        owner_id = uuid.uuid4()
        owner = User(id=owner_id, email="owner@test.com")
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            owner,  # Owner lookup
            None,  # Name check
        ]

        mock_company = MagicMock()
        mock_company.id = uuid.uuid4()
        mock_company.name = "New Co"
        mock_company.owner_id = owner_id
        mock_company_cls.return_value = mock_company

        with patch("grpc_services.utils.get_identity") as mock_get_id:
            mock_get_id.return_value = {
                "user_id": str(uuid.uuid4()),
                "role": "superadmin",
            }

            request = company_pb2.CreateCompanyRequest(
                name="New Co", owner_email="owner@test.com"
            )
            context = MagicMock()
            context.peer.return_value = "127.0.0.1"

            response = await company_service.CreateCompany(request, context)

            assert response.name == "New Co"
            assert mock_db.commit.call_count == 2


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
    c1 = Company(id=uuid.uuid4(), name="C1", owner_id=owner.id, owner=owner, members=[])
    mock_db.query.return_value.options.return_value.all.return_value = [c1]

    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {"user_id": str(uuid.uuid4()), "role": "superadmin"}

        request = company_pb2.ListCompaniesRequest()
        context = MagicMock()

        response = await company_service.ListCompanies(request, context)

        assert len(response.companies) == 1
        assert response.companies[0].name == "C1"
        assert response.companies[0].member_count == 1


def test_company_summary_includes_current_company_metadata(company_service):
    owner = User(id=uuid.uuid4(), email="owner@test.com", avatar_url="avatar.png")
    company = Company(
        id=uuid.uuid4(),
        name="Tenant Corp",
        owner_id=owner.id,
        owner=owner,
        members=[],
        org_size="ORGANIZATION_SIZE_11_50",
        org_type="ORGANIZATION_TYPE_SOFTWARE_DEVELOPMENT",
        token_balance=42,
    )

    summary = company_service._company_summary(company)

    assert summary.id == str(company.id)
    assert summary.name == "Tenant Corp"
    assert summary.owner_email == "owner@test.com"
    assert summary.member_count == 1
    assert summary.avatar_url == "avatar.png"
    assert summary.org_size == company_pb2.ORGANIZATION_SIZE_11_50
    assert summary.org_type == company_pb2.ORGANIZATION_TYPE_SOFTWARE_DEVELOPMENT
    assert summary.token_balance == 42


def test_update_current_company_db_sync(company_service, mock_db):
    company = Company(
        id=uuid.uuid4(),
        name="Old Name",
        owner=User(id=uuid.uuid4(), email="owner@test.com"),
        members=[],
    )
    mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = company

    summary, error = company_service._update_current_company_db_sync(
        str(company.id),
        "New Name",
        company_pb2.ORGANIZATION_SIZE_51_200,
        company_pb2.ORGANIZATION_TYPE_FINANCIAL_SERVICES,
    )

    assert error is None
    assert company.name == "New Name"
    assert company.org_size == "ORGANIZATION_SIZE_51_200"
    assert company.org_type == "ORGANIZATION_TYPE_FINANCIAL_SERVICES"
    assert summary.name == "New Name"
    assert summary.org_size == company_pb2.ORGANIZATION_SIZE_51_200
    assert summary.org_type == company_pb2.ORGANIZATION_TYPE_FINANCIAL_SERVICES
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(company)


@pytest.mark.asyncio
async def test_owner_updates_current_company(company_service, mock_db):
    company_id = str(uuid.uuid4())
    summary = company_pb2.CompanySummary(id=company_id, name="New Name")
    context = MagicMock()
    context.invocation_metadata.return_value = [
        ("x-action", "update-current-company"),
    ]

    identity = {
        "user_id": str(uuid.uuid4()),
        "company_id": company_id,
        "role": "owner",
    }

    with patch("asyncio.to_thread", return_value=(summary, None)), patch(
        "grpc_services.utils.get_identity", return_value=identity
    ):
        response = await company_service.CreateCompany(
            company_pb2.CreateCompanyRequest(
                name="New Name",
                org_size=company_pb2.ORGANIZATION_SIZE_2_10,
                org_type=company_pb2.ORGANIZATION_TYPE_RETAIL,
            ),
            context,
        )

    assert response.id == company_id
    assert response.name == "New Name"
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_onboard_company_success(company_service, mock_db):
    with patch("grpc_services.company.Company") as mock_company_cls, patch(
        "grpc_services.company.User"
    ) as mock_user_cls, patch(
        "grpc_services.company.generate_opaque_token",
        return_value="aegis_inv_raw-token",
    ), patch(
        "grpc_services.company.send_onboarding_invitation_email",
        return_value=True,
    ) as mock_send_invitation:
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
        )
        context = MagicMock()
        context.abort = AsyncMock()

        # Ensure existence checks return None
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch("grpc_services.utils.get_identity") as mock_get_id:
            mock_get_id.return_value = {
                "user_id": str(uuid.uuid4()),
                "role": "superadmin",
            }
            response = await company_service.OnboardCompany(request, context)

        assert response.company_id == str(mock_company.id)
        assert response.owner_id == str(mock_owner.id)
        assert response.deployment_token == ""
        company_kwargs = mock_company_cls.call_args.kwargs
        assert "deployment_token" not in company_kwargs
        mock_user_cls.assert_called_once()
        owner_kwargs = mock_user_cls.call_args.kwargs
        assert owner_kwargs["role"] == UserRole.owner
        assert owner_kwargs["is_active"] is False
        assert (
            owner_kwargs["activation_status"] == UserActivationStatus.pending_activation
        )
        assert owner_kwargs["password_hash"]
        invitation = next(
            call.args[0]
            for call in mock_db.add.call_args_list
            if isinstance(call.args[0], OnboardingInvitation)
        )
        assert invitation.user_id == mock_owner.id
        assert invitation.token_hash == hash_token("aegis_inv_raw-token")
        assert invitation.token_hash != "aegis_inv_raw-token"
        assert invitation.expires_at is not None
        mock_send_invitation.assert_called_once_with(
            owner_email="owner@test.com",
            owner_name="Owner",
            company_name="New Co",
            invitation_token="aegis_inv_raw-token",
            email_service=ANY,
        )
        assert mock_db.commit.call_count == 2


@pytest.mark.asyncio
async def test_rotate_agent_token_success_for_owner(company_service, mock_db):
    company_id = str(uuid.uuid4())
    company = Company(id=uuid.UUID(company_id), name="Tenant")
    mock_db.query.return_value.filter.return_value.first.return_value = company

    with patch("grpc_services.utils.get_identity") as mock_get_id, patch(
        "grpc_services.company.generate_agent_token",
        return_value=VALID_AGENT_TOKEN,
    ):
        mock_get_id.return_value = {
            "user_id": str(uuid.uuid4()),
            "role": "owner",
            "company_id": company_id,
        }

        response = await company_service.RotateAgentToken(
            company_pb2.RotateAgentTokenRequest(), MagicMock()
        )

    assert response.agent_token == VALID_AGENT_TOKEN
    assert company.deployment_token == hash_token(VALID_AGENT_TOKEN)
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_rotate_agent_token_denies_cross_company_owner(company_service):
    company_id = str(uuid.uuid4())
    other_company_id = str(uuid.uuid4())
    context = MagicMock()

    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {
            "user_id": str(uuid.uuid4()),
            "role": "owner",
            "company_id": company_id,
        }

        response = await company_service.RotateAgentToken(
            company_pb2.RotateAgentTokenRequest(company_id=other_company_id),
            context,
        )

    assert response.agent_token == ""
    context.set_code.assert_called_with(grpc.StatusCode.PERMISSION_DENIED)


@pytest.mark.asyncio
async def test_revoke_agent_token_success_for_owner(company_service, mock_db):
    company_id = str(uuid.uuid4())
    company = Company(
        id=uuid.UUID(company_id),
        name="Tenant",
        deployment_token=hash_token(VALID_AGENT_TOKEN),
    )
    mock_db.query.return_value.filter.return_value.first.return_value = company

    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {
            "user_id": str(uuid.uuid4()),
            "role": "owner",
            "company_id": company_id,
        }

        response = await company_service.RevokeAgentToken(
            company_pb2.RevokeAgentTokenRequest(), MagicMock()
        )

    assert response.success is True
    assert company.deployment_token is None
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_revoke_agent_token_returns_not_found(company_service, mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None
    context = MagicMock()

    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {
            "user_id": str(uuid.uuid4()),
            "role": "admin",
            "company_id": str(uuid.uuid4()),
        }

        response = await company_service.RevokeAgentToken(
            company_pb2.RevokeAgentTokenRequest(), context
        )

    assert response.success is False
    context.set_code.assert_called_with(grpc.StatusCode.NOT_FOUND)


@pytest.mark.asyncio
async def test_watch_company_updates_success(company_service):
    from grpc_services.broadcaster import broadcaster

    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {"user_id": str(uuid.uuid4()), "role": "superadmin"}

        request = company_pb2.WatchCompanyUpdatesRequest()
        context = MagicMock()

        # We need to simulate the queue and its response
        async def mock_stream():
            # Trigger an update in background
            async def trigger():
                await asyncio.sleep(0.1)
                # Broadcast payload: (event, company_id, entity_id, entity_name)
                broadcaster.broadcast(
                    "team", ("COMPANY_CREATED", "c1", "c1", "Company 1")
                )

            asyncio.create_task(trigger())

            stream = company_service.WatchCompanyUpdates(request, context)
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
        company_id = uuid.uuid4()
        company = Company(id=company_id, name="Acme Corp")

        # Mock metadata for hijacking
        mock_context = MagicMock()
        mock_context.abort = AsyncMock()
        mock_context.invocation_metadata.return_value = [
            ("x-action", "create-user"),
            ("x-user-role", "admin"),
            ("x-company-id", str(company_id)),
        ]

        # Ensure user doesn't exist, then resolve target company.
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            None,
            company,
        ]

        with (
            patch("grpc_services.utils.get_identity") as mock_get_id,
            patch(
                "grpc_services.company.generate_opaque_token",
                return_value="aegis_inv_user-token",
            ),
            patch(
                "grpc_services.company.send_user_invitation_email"
            ) as mock_send_invite,
        ):
            mock_get_id.return_value = {
                "user_id": str(uuid.uuid4()),
                "role": "superadmin",
            }

            request = company_pb2.CreateCompanyRequest(
                name="New User", owner_email="user@test.com"
            )

            response = await company_service.CreateCompany(request, mock_context)

            assert response.id == str(mock_user.id)
            assert mock_db.commit.call_count == 2
            assert mock_user_cls.call_args.kwargs["is_active"] is False
            assert (
                mock_user_cls.call_args.kwargs["activation_status"]
                == UserActivationStatus.pending_activation
            )
            mock_send_invite.assert_called_once_with(
                user_email="user@test.com",
                user_name="New User",
                company_name="Acme Corp",
                invitation_token="aegis_inv_user-token",
                email_service=company_service.email_service,
            )


def test_list_users_includes_all_company_owners(company_service, mock_db):
    company_id = uuid.uuid4()
    owner_one = User(
        id=uuid.uuid4(),
        company_id=company_id,
        name="Owner One",
        email="owner-one@test.com",
        password_hash="hash",
        role=UserRole.owner,
        is_active=True,
    )
    owner_two = User(
        id=uuid.uuid4(),
        company_id=company_id,
        name="Owner Two",
        email="owner-two@test.com",
        password_hash="hash",
        role=UserRole.owner,
        is_active=True,
    )
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
        owner_one,
        owner_two,
    ]

    users = company_service._list_entities_db_sync(
        action="list-users",
        company_id=str(company_id),
    )

    assert [user.name for user in users] == ["Owner One", "Owner Two"]
    assert [user.deployment_token for user in users] == ["owner", "owner"]
    assert [user.org_type for user in users] == [
        company_pb2.ORGANIZATION_TYPE_OTHER,
        company_pb2.ORGANIZATION_TYPE_OTHER,
    ]


def test_list_users_marks_inactive_collaborators(company_service, mock_db):
    company_id = uuid.uuid4()
    inactive_user = User(
        id=uuid.uuid4(),
        company_id=company_id,
        name="Inactive User",
        email="inactive@test.com",
        password_hash="hash",
        role=UserRole.viewer,
        is_active=False,
    )
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
        inactive_user,
    ]

    users = company_service._list_entities_db_sync(
        action="list-users",
        company_id=str(company_id),
    )

    assert users[0].org_type == company_pb2.ORGANIZATION_TYPE_UNSPECIFIED


@pytest.mark.parametrize(
    ("request_company_id", "identity", "expected_code", "expected_message"),
    [
        (
            "",
            {"role": "viewer", "company_id": "company-1"},
            grpc.StatusCode.PERMISSION_DENIED,
            "Insufficient permissions",
        ),
        (
            "",
            {"role": "owner", "company_id": ""},
            grpc.StatusCode.PERMISSION_DENIED,
            "Missing company scope",
        ),
        (
            "company-2",
            {"role": "owner", "company_id": "company-1"},
            grpc.StatusCode.PERMISSION_DENIED,
            "Cannot manage another company's collaborators",
        ),
        (
            "",
            {"role": "superadmin", "company_id": ""},
            grpc.StatusCode.INVALID_ARGUMENT,
            "Missing company_id",
        ),
    ],
)
def test_resolve_user_management_company_id_rejects_invalid_scope(
    company_service,
    request_company_id,
    identity,
    expected_code,
    expected_message,
):
    company_id, code, message = company_service._resolve_user_management_company_id(
        request_company_id, identity
    )

    assert company_id is None
    assert code == expected_code
    assert message == expected_message


def test_validate_managed_user_role_rejects_unknown_role(company_service):
    role, error = company_service._validate_managed_user_role(
        "unknown-role", {"role": "superadmin"}
    )

    assert role is None
    assert error == "Invalid role"


@pytest.mark.asyncio
async def test_owner_updates_tenant_user_role(company_service, mock_db):
    company_id = uuid.uuid4()
    target_user_id = uuid.uuid4()
    target_user = User(
        id=target_user_id,
        company_id=company_id,
        name="Viewer",
        email="viewer@test.com",
        password_hash="hash",
        role=UserRole.viewer,
    )
    mock_db.query.return_value.filter.return_value.first.return_value = target_user

    context = MagicMock()
    context.peer.return_value = "127.0.0.1"
    context.invocation_metadata.return_value = [
        ("x-action", "update-user-role"),
        ("x-user-role", "operateur"),
        ("x-company-id", str(company_id)),
    ]

    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {
            "user_id": str(uuid.uuid4()),
            "role": "owner",
            "company_id": str(company_id),
        }

        response = await company_service.CreateCompany(
            company_pb2.CreateCompanyRequest(name=str(target_user_id)), context
        )

    assert response.id == str(target_user_id)
    assert target_user.role == UserRole.operateur
    assert mock_db.commit.call_count == 2


@pytest.mark.asyncio
async def test_owner_cannot_assign_internal_role(company_service):
    company_id = uuid.uuid4()
    context = MagicMock()
    context.invocation_metadata.return_value = [
        ("x-action", "update-user-role"),
        ("x-user-role", "admin"),
        ("x-company-id", str(company_id)),
    ]

    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {
            "user_id": str(uuid.uuid4()),
            "role": "owner",
            "company_id": str(company_id),
        }

        await company_service.CreateCompany(
            company_pb2.CreateCompanyRequest(name=str(uuid.uuid4())), context
        )

    context.set_code.assert_called_with(grpc.StatusCode.PERMISSION_DENIED)
    context.set_details.assert_called_with("Owners cannot assign internal roles")


@pytest.mark.asyncio
async def test_billing_client_role_is_no_longer_assignable(company_service):
    company_id = uuid.uuid4()
    context = MagicMock()
    context.invocation_metadata.return_value = [
        ("x-action", "update-user-role"),
        ("x-user-role", "billing_client"),
        ("x-company-id", str(company_id)),
    ]

    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {
            "user_id": str(uuid.uuid4()),
            "role": "superadmin",
            "company_id": str(company_id),
        }

        await company_service.CreateCompany(
            company_pb2.CreateCompanyRequest(name=str(uuid.uuid4())), context
        )

    context.set_code.assert_called_with(grpc.StatusCode.INVALID_ARGUMENT)
    context.set_details.assert_called_with(
        "Billing client role is no longer assignable"
    )


@pytest.mark.asyncio
async def test_owner_cannot_update_own_role(company_service):
    company_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    context = MagicMock()
    context.invocation_metadata.return_value = [
        ("x-action", "update-user-role"),
        ("x-user-role", "viewer"),
        ("x-company-id", str(company_id)),
    ]

    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {
            "user_id": str(owner_id),
            "role": "owner",
            "company_id": str(company_id),
        }

        await company_service.CreateCompany(
            company_pb2.CreateCompanyRequest(name=str(owner_id)), context
        )

    context.set_code.assert_called_with(grpc.StatusCode.PERMISSION_DENIED)
    context.set_details.assert_called_with("Cannot update your own role")


@pytest.mark.asyncio
async def test_owner_deactivates_tenant_user(company_service, mock_db):
    company_id = uuid.uuid4()
    target_user_id = uuid.uuid4()
    target_user = User(
        id=target_user_id,
        company_id=company_id,
        name="Viewer",
        email="viewer@test.com",
        password_hash="hash",
        role=UserRole.viewer,
    )
    mock_db.query.return_value.filter.return_value.first.return_value = target_user

    context = MagicMock()
    context.peer.return_value = "127.0.0.1"
    context.invocation_metadata.return_value = [
        ("x-action", "deactivate-user"),
        ("x-company-id", str(company_id)),
    ]

    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {
            "user_id": str(uuid.uuid4()),
            "role": "owner",
            "company_id": str(company_id),
        }

        response = await company_service.CreateCompany(
            company_pb2.CreateCompanyRequest(name=str(target_user_id)), context
        )

    assert response.id == str(target_user_id)
    assert target_user.is_active is False
    assert mock_db.commit.call_count == 2


@pytest.mark.asyncio
async def test_owner_deactivates_another_owner(company_service, mock_db):
    company_id = uuid.uuid4()
    requester_id = uuid.uuid4()
    target_owner_id = uuid.uuid4()
    target_owner = User(
        id=target_owner_id,
        company_id=company_id,
        name="Other Owner",
        email="other-owner@test.com",
        password_hash="hash",
        role=UserRole.owner,
    )
    mock_db.query.return_value.filter.return_value.first.return_value = target_owner

    context = MagicMock()
    context.peer.return_value = "127.0.0.1"
    context.invocation_metadata.return_value = [
        ("x-action", "deactivate-user"),
        ("x-company-id", str(company_id)),
    ]

    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {
            "user_id": str(requester_id),
            "role": "owner",
            "company_id": str(company_id),
        }

        response = await company_service.CreateCompany(
            company_pb2.CreateCompanyRequest(name=str(target_owner_id)), context
        )

    assert response.id == str(target_owner_id)
    assert target_owner.is_active is False
    assert mock_db.commit.call_count == 2


@pytest.mark.asyncio
async def test_superadmin_deactivates_company_owner_linked_by_owner_id(
    company_service, mock_db
):
    company_id = uuid.uuid4()
    target_owner_id = uuid.uuid4()
    target_owner = User(
        id=target_owner_id,
        company_id=None,
        name="Company Owner",
        email="owner@test.com",
        password_hash="hash",
        role=UserRole.owner,
        is_active=True,
    )
    mock_db.query.return_value.filter.return_value.first.return_value = target_owner

    context = MagicMock()
    context.peer.return_value = "127.0.0.1"
    context.invocation_metadata.return_value = [
        ("x-action", "set-user-active"),
        ("x-user-active", "false"),
        ("x-company-id", str(company_id)),
    ]

    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {
            "user_id": str(uuid.uuid4()),
            "role": "superadmin",
            "company_id": "",
        }

        response = await company_service.CreateCompany(
            company_pb2.CreateCompanyRequest(name=str(target_owner_id)), context
        )

    assert response.id == str(target_owner_id)
    assert target_owner.is_active is False
    assert mock_db.commit.call_count == 2


@pytest.mark.asyncio
async def test_owner_reactivates_tenant_user(company_service, mock_db):
    company_id = uuid.uuid4()
    target_user_id = uuid.uuid4()
    target_user = User(
        id=target_user_id,
        company_id=company_id,
        name="Viewer",
        email="viewer@test.com",
        password_hash="hash",
        role=UserRole.viewer,
        is_active=False,
    )
    mock_db.query.return_value.filter.return_value.first.return_value = target_user

    context = MagicMock()
    context.peer.return_value = "127.0.0.1"
    context.invocation_metadata.return_value = [
        ("x-action", "set-user-active"),
        ("x-user-active", "true"),
        ("x-company-id", str(company_id)),
    ]

    with patch("grpc_services.utils.get_identity") as mock_get_id:
        mock_get_id.return_value = {
            "user_id": str(uuid.uuid4()),
            "role": "owner",
            "company_id": str(company_id),
        }

        response = await company_service.CreateCompany(
            company_pb2.CreateCompanyRequest(name=str(target_user_id)), context
        )

    assert response.id == str(target_user_id)
    assert target_user.is_active is True
    assert mock_db.commit.call_count == 2
