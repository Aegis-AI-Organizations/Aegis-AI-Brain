import logging
import asyncio
import enum
import grpc
from datetime import datetime, timedelta, timezone

import aegis.v2.company_pb2 as company_pb2
import aegis.v2.company_pb2_grpc as company_pb2_grpc
from config.db import get_session_factory
from models.company import Company
from models.onboarding_invitation import OnboardingInvitation
from models.user import User, UserRole, UserActivationStatus
from sqlalchemy import String, or_, select
from sqlalchemy.orm import joinedload
from grpc_services.utils import with_identity
from .broadcaster import broadcaster
from utils.auth_utils import hash_password
from utils.email_utils import (
    send_onboarding_invitation_email,
    send_user_invitation_email,
)
from services.email_service import EmailService, create_email_service
from utils.token_utils import generate_agent_token, generate_opaque_token, hash_token
from models.audit_log import AuditLog
import uuid
import json

logger = logging.getLogger(__name__)
ONBOARDING_INVITATION_TTL_HOURS = 72

ORG_SIZE_BY_STORAGE = {
    "ORGANIZATION_SIZE_1": company_pb2.ORGANIZATION_SIZE_1,
    "ORGANIZATION_SIZE_2_10": company_pb2.ORGANIZATION_SIZE_2_10,
    "ORGANIZATION_SIZE_11_50": company_pb2.ORGANIZATION_SIZE_11_50,
    "ORGANIZATION_SIZE_51_200": company_pb2.ORGANIZATION_SIZE_51_200,
    "ORGANIZATION_SIZE_201_500": company_pb2.ORGANIZATION_SIZE_201_500,
    "ORGANIZATION_SIZE_501_1000": company_pb2.ORGANIZATION_SIZE_501_1000,
    "ORGANIZATION_SIZE_1001_5000": company_pb2.ORGANIZATION_SIZE_1001_5000,
    "ORGANIZATION_SIZE_5001_10000": company_pb2.ORGANIZATION_SIZE_5001_10000,
    "ORGANIZATION_SIZE_10001_PLUS": company_pb2.ORGANIZATION_SIZE_10001_PLUS,
}

ORG_TYPE_BY_STORAGE = {
    "ORGANIZATION_TYPE_IT_SERVICES_AND_CONSULTING": company_pb2.ORGANIZATION_TYPE_IT_SERVICES_AND_CONSULTING,
    "ORGANIZATION_TYPE_SOFTWARE_DEVELOPMENT": company_pb2.ORGANIZATION_TYPE_SOFTWARE_DEVELOPMENT,
    "ORGANIZATION_TYPE_FINANCIAL_SERVICES": company_pb2.ORGANIZATION_TYPE_FINANCIAL_SERVICES,
    "ORGANIZATION_TYPE_HOSPITALS_AND_HEALTH_CARE": company_pb2.ORGANIZATION_TYPE_HOSPITALS_AND_HEALTH_CARE,
    "ORGANIZATION_TYPE_RETAIL": company_pb2.ORGANIZATION_TYPE_RETAIL,
    "ORGANIZATION_TYPE_GOVERNMENT_ADMINISTRATION": company_pb2.ORGANIZATION_TYPE_GOVERNMENT_ADMINISTRATION,
    "ORGANIZATION_TYPE_MANUFACTURING": company_pb2.ORGANIZATION_TYPE_MANUFACTURING,
    "ORGANIZATION_TYPE_OTHER": company_pb2.ORGANIZATION_TYPE_OTHER,
}

ORG_SIZE_STORAGE_BY_VALUE = {value: key for key, value in ORG_SIZE_BY_STORAGE.items()}
ORG_TYPE_STORAGE_BY_VALUE = {value: key for key, value in ORG_TYPE_BY_STORAGE.items()}


class CompanyCreateError(enum.Enum):
    SUCCESS = 0
    OWNER_NOT_FOUND = 1
    NAME_EXISTS = 2
    DB_ERROR = 3


class CompanyService(company_pb2_grpc.CompanyServiceServicer):
    """CompanyService handles company creation and administrative listing."""

    def __init__(self, email_service: EmailService | None = None):
        self._session_factory = None
        self.email_service = email_service or create_email_service()

    @property
    def session_factory(self):
        if self._session_factory is None:
            self._session_factory = get_session_factory()
        return self._session_factory

    def _resolve_agent_token_company_id(self, request_company_id: str, identity):
        role = identity["role"]
        allowed_roles = ["superadmin", "admin", "owner"]
        if role not in allowed_roles:
            return None, grpc.StatusCode.PERMISSION_DENIED, "Insufficient permissions"

        identity_company_id = str(identity.get("company_id") or "")
        if role == "owner":
            if not identity_company_id:
                return None, grpc.StatusCode.PERMISSION_DENIED, "Missing company scope"
            if request_company_id and request_company_id != identity_company_id:
                return (
                    None,
                    grpc.StatusCode.PERMISSION_DENIED,
                    "Cannot manage another company token",
                )
            return identity_company_id, None, None

        target_company_id = request_company_id or identity_company_id
        if not target_company_id:
            return None, grpc.StatusCode.INVALID_ARGUMENT, "Missing company_id"
        return target_company_id, None, None

    def _resolve_user_management_company_id(self, request_company_id: str, identity):
        role = identity["role"]
        allowed_roles = ["superadmin", "admin", "owner"]
        if role not in allowed_roles:
            return None, grpc.StatusCode.PERMISSION_DENIED, "Insufficient permissions"

        identity_company_id = str(identity.get("company_id") or "")
        if role == "owner":
            if not identity_company_id:
                return None, grpc.StatusCode.PERMISSION_DENIED, "Missing company scope"
            if request_company_id and request_company_id != identity_company_id:
                return (
                    None,
                    grpc.StatusCode.PERMISSION_DENIED,
                    "Cannot manage another company's collaborators",
                )
            return identity_company_id, None, None

        target_company_id = request_company_id or identity_company_id
        if not target_company_id:
            return None, grpc.StatusCode.INVALID_ARGUMENT, "Missing company_id"
        return target_company_id, None, None

    def _resolve_current_company_id(self, identity):
        role = identity["role"]
        allowed_roles = ["superadmin", "admin", "owner"]
        if role not in allowed_roles:
            return None, grpc.StatusCode.PERMISSION_DENIED, "Insufficient permissions"

        company_id = str(identity.get("company_id") or "")
        if not company_id:
            return None, grpc.StatusCode.PERMISSION_DENIED, "Missing company scope"
        return company_id, None, None

    def _validate_managed_user_role(self, role: str, identity):
        try:
            user_role = UserRole(role)
        except ValueError:
            return None, "Invalid role"

        if user_role == UserRole.billing_client:
            return None, "Billing client role is no longer assignable"

        if identity["role"] == "owner":
            allowed_tenant_roles = {
                UserRole.owner,
                UserRole.operateur,
                UserRole.viewer,
            }
            if user_role not in allowed_tenant_roles:
                return None, "Owners cannot assign internal roles"

        return user_role, None

    def _company_summary(self, company: Company):
        owner_email = company.owner.email if company.owner else ""
        owner_id = str(company.owner_id) if company.owner_id else ""
        members = list(company.members or [])
        member_count = len(members)
        if owner_id and all(str(m.id) != owner_id for m in members):
            member_count += 1

        summary_kwargs = {
            "id": str(company.id),
            "name": company.name,
            "owner_id": owner_id,
            "owner_email": owner_email,
            "member_count": member_count,
            "deployment_token": "",
            "avatar_url": company.owner.avatar_url if company.owner else "",
            "org_size": ORG_SIZE_BY_STORAGE.get(
                company.org_size or "",
                company_pb2.ORGANIZATION_SIZE_UNSPECIFIED,
            ),
            "org_type": ORG_TYPE_BY_STORAGE.get(
                company.org_type or "",
                company_pb2.ORGANIZATION_TYPE_UNSPECIFIED,
            ),
            "token_balance": company.token_balance or 0,
        }
        return company_pb2.CompanySummary(**summary_kwargs)

    def _update_current_company_db_sync(self, company_id, name, org_size, org_type):
        with self.session_factory() as db:
            company = (
                db.query(Company)
                .options(joinedload(Company.owner), joinedload(Company.members))
                .filter(Company.id == company_id)
                .first()
            )
            if not company:
                return None, "Company not found"

            if name:
                company.name = name
            if org_size != company_pb2.ORGANIZATION_SIZE_UNSPECIFIED:
                company.org_size = ORG_SIZE_STORAGE_BY_VALUE.get(org_size)
            if org_type != company_pb2.ORGANIZATION_TYPE_UNSPECIFIED:
                company.org_type = ORG_TYPE_STORAGE_BY_VALUE.get(org_type)

            db.commit()
            db.refresh(company)
            broadcaster.broadcast(
                "team",
                ("COMPANY_UPDATED", str(company.id), str(company.id), company.name),
            )
            return self._company_summary(company), None

    def _create_company_db_sync(self, name: str, owner_email: str):
        with self.session_factory() as db:
            # 1. Verify owner exists
            owner = db.query(User).filter(User.email == owner_email).first()
            if not owner:
                return None, CompanyCreateError.OWNER_NOT_FOUND

            # 2. Check if company name already exists
            existing = db.query(Company).filter(Company.name == name).first()
            if existing:
                return None, CompanyCreateError.NAME_EXISTS

            try:
                new_company = Company(name=name, owner_id=owner.id)
                db.add(new_company)
                db.flush()  # Get ID

                # Update user's company_id
                owner.company_id = new_company.id

                db.commit()
                # Broadcast company creation
                broadcaster.broadcast(
                    "team",
                    (
                        "COMPANY_CREATED",
                        str(new_company.id),
                        str(new_company.id),
                        new_company.name,
                    ),
                )
                return new_company, CompanyCreateError.SUCCESS
            except Exception:
                db.rollback()
                logger.exception("Failed to create company")
                return None, CompanyCreateError.DB_ERROR

    def _onboard_company_db_sync(
        self,
        company_name: str,
        owner_name: str,
        owner_email: str,
    ):
        with self.session_factory() as db:
            # 1. Check if email already exists
            existing_user = db.query(User).filter(User.email == owner_email).first()
            if existing_user:
                return None, None, None, None, "User already exists with this email"

            # 2. Check if company name already exists
            existing_company = (
                db.query(Company).filter(Company.name == company_name).first()
            )
            if existing_company:
                return None, None, None, None, "Company already exists with this name"

            try:
                # 3. Create Company. The agent deployment token is generated later
                # during owner activation so the customer can see it exactly once.
                new_company = Company(name=company_name)
                db.add(new_company)
                db.flush()  # Get ID

                # 4. Create Owner User in a pending state.
                # Placeholder keeps password_hash non-null until setup-password replaces it.
                placeholder_password = uuid.uuid4().hex
                new_owner = User(
                    name=owner_name,
                    email=owner_email,
                    password_hash=hash_password(placeholder_password),
                    role=UserRole.owner,
                    company_id=new_company.id,
                    is_active=False,
                    activation_status=UserActivationStatus.pending_activation,
                )
                db.add(new_owner)
                db.flush()  # Get Owner ID

                # 5. Generate first-login invitation token.
                invitation_token = generate_opaque_token("aegis_inv_")
                invitation = OnboardingInvitation(
                    user_id=new_owner.id,
                    token_hash=hash_token(invitation_token),
                    expires_at=datetime.now(timezone.utc)
                    + timedelta(hours=ONBOARDING_INVITATION_TTL_HOURS),
                )
                db.add(invitation)

                # 6. Link Owner back to Company
                new_company.owner_id = new_owner.id

                db.commit()
                # Broadcast company creation
                broadcaster.broadcast(
                    "team",
                    (
                        "COMPANY_CREATED",
                        str(new_company.id),
                        str(new_company.id),
                        new_company.name,
                    ),
                )
                return (
                    str(new_company.id),
                    str(new_owner.id),
                    "",
                    invitation_token,
                    None,
                )
            except Exception as e:
                db.rollback()
                logger.exception("Failed to onboard company")
                return None, None, None, None, f"Database error: {str(e)}"

    @with_identity(verified_only=True)
    async def OnboardCompany(
        self, request: company_pb2.OnboardCompanyRequest, context, identity
    ) -> company_pb2.OnboardCompanyResponse:
        allowed_roles = ["superadmin", "admin", "commercial"]
        if identity["role"] not in allowed_roles:
            context.set_code(grpc.StatusCode.PERMISSION_DENIED)
            context.set_details("Only Aegis administrators or commercial can onboard")
            return company_pb2.OnboardCompanyResponse()

        res = await asyncio.to_thread(
            self._onboard_company_db_sync,
            request.company_name,
            request.owner_name,
            request.owner_email,
        )

        company_id, owner_id, token, invitation_token, error = res

        if error:
            if "already exists" in error:
                context.set_code(grpc.StatusCode.ALREADY_EXISTS)
            else:
                context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(error)
            return company_pb2.OnboardCompanyResponse()

        # Log the action in AuditLog
        try:
            with self.session_factory() as db:
                audit = AuditLog(
                    user_id=identity["user_id"],
                    company_id=identity.get("company_id"),
                    action="ONBOARD_COMPANY",
                    target_type="COMPANY",
                    target_id=company_id,
                    ip_address=context.peer(),
                    details={
                        "company_name": request.company_name,
                        "owner_email": request.owner_email,
                        "invitation_generated": bool(invitation_token),
                    },
                )
                db.add(audit)
                db.commit()
        except Exception:
            logger.exception("Failed to log audit for onboarding")

        try:
            await asyncio.to_thread(
                send_onboarding_invitation_email,
                owner_email=request.owner_email,
                owner_name=request.owner_name,
                company_name=request.company_name,
                invitation_token=invitation_token,
                email_service=self.email_service,
            )
        except Exception:
            logger.exception(
                "Failed to send onboarding invitation email to %s",
                request.owner_email,
            )

        return company_pb2.OnboardCompanyResponse(
            company_id=company_id, owner_id=owner_id, deployment_token=token
        )

    def _rotate_agent_token_db_sync(self, company_id: str):
        with self.session_factory() as db:
            company = db.query(Company).filter(Company.id == company_id).first()
            if not company:
                return None, "not_found"

            try:
                agent_token = generate_agent_token()
                company.deployment_token = hash_token(agent_token)
                db.commit()
                return agent_token, None
            except Exception as exc:
                db.rollback()
                logger.exception("Failed to rotate agent token")
                return None, str(exc)

    def _revoke_agent_token_db_sync(self, company_id: str):
        with self.session_factory() as db:
            company = db.query(Company).filter(Company.id == company_id).first()
            if not company:
                return False, "not_found"

            try:
                company.deployment_token = None
                db.commit()
                return True, None
            except Exception as exc:
                db.rollback()
                logger.exception("Failed to revoke agent token")
                return False, str(exc)

    @with_identity(verified_only=True)
    async def RotateAgentToken(
        self, request: company_pb2.RotateAgentTokenRequest, context, identity
    ) -> company_pb2.RotateAgentTokenResponse:
        company_id, status_code, details = self._resolve_agent_token_company_id(
            request.company_id, identity
        )
        if status_code:
            context.set_code(status_code)
            context.set_details(details)
            return company_pb2.RotateAgentTokenResponse()

        token, error = await asyncio.to_thread(
            self._rotate_agent_token_db_sync, company_id
        )
        if error:
            context.set_code(
                grpc.StatusCode.NOT_FOUND
                if error == "not_found"
                else grpc.StatusCode.INTERNAL
            )
            context.set_details("Company not found" if error == "not_found" else error)
            return company_pb2.RotateAgentTokenResponse()

        return company_pb2.RotateAgentTokenResponse(agent_token=token)

    @with_identity(verified_only=True)
    async def RevokeAgentToken(
        self, request: company_pb2.RevokeAgentTokenRequest, context, identity
    ) -> company_pb2.RevokeAgentTokenResponse:
        company_id, status_code, details = self._resolve_agent_token_company_id(
            request.company_id, identity
        )
        if status_code:
            context.set_code(status_code)
            context.set_details(details)
            return company_pb2.RevokeAgentTokenResponse()

        success, error = await asyncio.to_thread(
            self._revoke_agent_token_db_sync, company_id
        )
        if error:
            context.set_code(
                grpc.StatusCode.NOT_FOUND
                if error == "not_found"
                else grpc.StatusCode.INTERNAL
            )
            context.set_details("Company not found" if error == "not_found" else error)
            return company_pb2.RevokeAgentTokenResponse(success=False)

        return company_pb2.RevokeAgentTokenResponse(success=success)

    def _list_entities_db_sync(
        self,
        search_query: str = "",
        action: str = "list-companies",
        company_id: str = "",
    ):
        with self.session_factory() as db:
            if action == "list-users":
                # User search logic
                query = db.query(User)
                if company_id:
                    owner_id_subquery = select(Company.owner_id).where(
                        Company.id == company_id
                    )
                    query = query.filter(
                        or_(
                            User.company_id == company_id,
                            User.id == owner_id_subquery.scalar_subquery(),
                        )
                    )
                if search_query:
                    query = query.filter(
                        (User.name.ilike(f"%{search_query}%"))
                        | (User.email.ilike(f"%{search_query}%"))
                        | (User.id.cast(String).ilike(f"%{search_query}%"))
                    )
                users = query.order_by(User.name.asc()).all()
                result = []
                for u in users:
                    summary_kwargs = {
                        "id": str(u.id),
                        "name": u.name,
                        "owner_id": str(u.company_id) if u.company_id else "",
                        "owner_email": u.email,
                        "deployment_token": u.role
                        if isinstance(u.role, str)
                        else u.role.value,
                        "member_count": 0,
                        "org_type": 8 if u.is_active else 0,
                    }
                    # Defensive check for proto field existence
                    if hasattr(company_pb2.CompanySummary, "avatar_url"):
                        summary_kwargs["avatar_url"] = u.avatar_url or ""

                    result.append(company_pb2.CompanySummary(**summary_kwargs))
                return result
            else:
                # Company search logic
                query = db.query(Company).options(
                    joinedload(Company.owner), joinedload(Company.members)
                )
                if company_id:
                    query = query.filter(Company.id == company_id)
                if search_query:
                    query = query.filter(
                        (Company.name.ilike(f"%{search_query}%"))
                        | (Company.members.any(User.name.ilike(f"%{search_query}%")))
                        | (Company.members.any(User.email.ilike(f"%{search_query}%")))
                        | (Company.id.cast(String).ilike(f"%{search_query}%"))
                    )
                companies = query.all()

                # Sort: Aegis AI first
                companies.sort(key=lambda x: 0 if x.name == "Aegis AI" else 1)

                result = []
                for c in companies:
                    result.append(self._company_summary(c))
                return result

    @with_identity(verified_only=True)
    async def ListCompanies(
        self, request: company_pb2.ListCompaniesRequest, context, identity
    ) -> company_pb2.ListCompaniesResponse:
        # Check metadata for search and action
        metadata = dict(context.invocation_metadata())
        search_query = metadata.get("x-query", "")
        action = metadata.get("x-action", "list-companies")
        company_id = metadata.get("x-company-id", "")

        # RBAC: Only admin/superadmin/commercial can search everything
        # Owners can only search their own company users or see their own company
        allowed_roles = ["superadmin", "admin", "commercial"]
        if identity["role"] not in allowed_roles:
            user_company_id = str(identity.get("company_id", ""))
            if action == "list-users" and company_id == user_company_id:
                pass  # Allowed
            elif action == "list-companies":
                # Force visibility to their own company only
                company_id = user_company_id
                if not company_id:
                    context.set_code(grpc.StatusCode.PERMISSION_DENIED)
                    return company_pb2.ListCompaniesResponse()
            else:
                context.set_code(grpc.StatusCode.PERMISSION_DENIED)
                return company_pb2.ListCompaniesResponse()

        try:
            entities = await asyncio.to_thread(
                self._list_entities_db_sync, search_query, action, company_id
            )
            return company_pb2.ListCompaniesResponse(companies=entities)
        except Exception:
            logger.exception(f"Failed to execute action {action}")
            context.set_code(grpc.StatusCode.INTERNAL)
            return company_pb2.ListCompaniesResponse()

    def _create_user_db_sync(self, name, email, role, company_id):
        with self.session_factory() as db:
            # Check if email exists
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                return None, None, None, "Email already in use"

            company = db.query(Company).filter(Company.id == company_id).first()
            if not company:
                return None, None, None, "Company not found"

            try:
                user_role = UserRole(role)
            except ValueError:
                return None, None, None, "Invalid role"

            try:
                placeholder_password = uuid.uuid4().hex
                new_user = User(
                    name=name,
                    email=email,
                    password_hash=hash_password(placeholder_password),
                    role=user_role,
                    company_id=company_id,
                    is_active=False,
                    activation_status=UserActivationStatus.pending_activation,
                )
                db.add(new_user)
                db.flush()

                invitation_token = generate_opaque_token("aegis_inv_")
                invitation = OnboardingInvitation(
                    user_id=new_user.id,
                    token_hash=hash_token(invitation_token),
                    expires_at=datetime.now(timezone.utc)
                    + timedelta(hours=ONBOARDING_INVITATION_TTL_HOURS),
                )
                db.add(invitation)
                db.commit()
                # Broadcast user creation
                broadcaster.broadcast(
                    "team", ("USER_CREATED", str(company_id), str(new_user.id), name)
                )
                return str(new_user.id), invitation_token, company.name, None
            except Exception as e:
                db.rollback()
                return None, None, None, str(e)

    def _update_user_role_db_sync(self, user_id, role, company_id, identity):
        requester_id = str(identity.get("user_id") or "")
        if requester_id and requester_id == str(user_id):
            return None, "Cannot update your own role"

        with self.session_factory() as db:
            user_role, role_error = self._validate_managed_user_role(role, identity)
            if role_error:
                return None, role_error

            owner_id_subquery = select(Company.owner_id).where(Company.id == company_id)
            user = (
                db.query(User)
                .filter(
                    User.id == user_id,
                    or_(
                        User.company_id == company_id,
                        User.id == owner_id_subquery.scalar_subquery(),
                    ),
                )
                .first()
            )
            if not user:
                return None, "User not found"

            user.role = user_role
            db.commit()
            broadcaster.broadcast(
                "team", ("USER_UPDATED", str(company_id), str(user.id), user.name or "")
            )
            return str(user.id), None

    def _set_user_active_db_sync(self, user_id, company_id, identity, is_active):
        requester_id = str(identity.get("user_id") or "")
        if requester_id and requester_id == str(user_id):
            return None, "Cannot change your own account status"

        with self.session_factory() as db:
            owner_id_subquery = select(Company.owner_id).where(Company.id == company_id)
            user = (
                db.query(User)
                .filter(
                    User.id == user_id,
                    or_(
                        User.company_id == company_id,
                        User.id == owner_id_subquery.scalar_subquery(),
                    ),
                )
                .first()
            )
            if not user:
                return None, "User not found"

            user.is_active = is_active
            db.commit()
            event_type = "USER_REACTIVATED" if is_active else "USER_DEACTIVATED"
            broadcaster.broadcast(
                "team",
                (event_type, str(company_id), str(user.id), user.name or ""),
            )
            return str(user.id), None

    def _deactivate_user_db_sync(self, user_id, company_id, identity):
        return self._set_user_active_db_sync(user_id, company_id, identity, False)

    @with_identity(verified_only=True)
    async def CreateCompany(
        self, request: company_pb2.CreateCompanyRequest, context, identity
    ) -> company_pb2.CreateCompanyResponse:
        metadata = dict(context.invocation_metadata())
        action = metadata.get("x-action", "create-company")

        if action == "update-current-company":
            company_id, status_code, details = self._resolve_current_company_id(
                identity
            )
            if status_code:
                context.set_code(status_code)
                context.set_details(details)
                return company_pb2.CreateCompanyResponse()

            summary, error = await asyncio.to_thread(
                self._update_current_company_db_sync,
                company_id,
                request.name.strip(),
                request.org_size,
                request.org_type,
            )

            if error:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(error)
                return company_pb2.CreateCompanyResponse()

            try:
                with self.session_factory() as db:
                    audit = AuditLog(
                        user_id=identity["user_id"],
                        company_id=company_id,
                        action="UPDATE_CURRENT_COMPANY",
                        target_type="COMPANY",
                        target_id=company_id,
                        ip_address=context.peer(),
                        details={
                            "name": request.name,
                            "org_size": ORG_SIZE_STORAGE_BY_VALUE.get(
                                request.org_size, ""
                            ),
                            "org_type": ORG_TYPE_STORAGE_BY_VALUE.get(
                                request.org_type, ""
                            ),
                        },
                    )
                    db.add(audit)
                    db.commit()
            except Exception:
                logger.exception("Failed to log audit for current company update")

            return company_pb2.CreateCompanyResponse(id=summary.id, name=summary.name)

        if action in {"update-user-role", "deactivate-user", "set-user-active"}:
            company_id, status_code, details = self._resolve_user_management_company_id(
                metadata.get("x-company-id", ""), identity
            )
            if status_code:
                context.set_code(status_code)
                context.set_details(details)
                return company_pb2.CreateCompanyResponse()

            user_id = request.name
            if not user_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Missing user_id")
                return company_pb2.CreateCompanyResponse()

            if action == "update-user-role":
                updated_id, error = await asyncio.to_thread(
                    self._update_user_role_db_sync,
                    user_id,
                    metadata.get("x-user-role", ""),
                    company_id,
                    identity,
                )
                audit_action = "UPDATE_USER_ROLE"
            elif action == "set-user-active":
                requested_status = metadata.get("x-user-active", "").lower()
                if requested_status not in {"true", "false"}:
                    context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                    context.set_details("Missing or invalid x-user-active")
                    return company_pb2.CreateCompanyResponse()

                updated_id, error = await asyncio.to_thread(
                    self._set_user_active_db_sync,
                    user_id,
                    company_id,
                    identity,
                    requested_status == "true",
                )
                audit_action = (
                    "REACTIVATE_USER"
                    if requested_status == "true"
                    else "DEACTIVATE_USER"
                )
            else:
                updated_id, error = await asyncio.to_thread(
                    self._deactivate_user_db_sync, user_id, company_id, identity
                )
                audit_action = "DEACTIVATE_USER"

            if error:
                context.set_code(
                    grpc.StatusCode.NOT_FOUND
                    if error == "User not found"
                    else grpc.StatusCode.PERMISSION_DENIED
                    if error.startswith("Cannot") or error.startswith("Owners cannot")
                    else grpc.StatusCode.INVALID_ARGUMENT
                )
                context.set_details(error)
                return company_pb2.CreateCompanyResponse()

            try:
                with self.session_factory() as db:
                    audit = AuditLog(
                        user_id=identity["user_id"],
                        company_id=company_id,
                        action=audit_action,
                        target_type="USER",
                        target_id=updated_id,
                        ip_address=context.peer(),
                        details={
                            "company_id": company_id,
                            "role": metadata.get("x-user-role", ""),
                        },
                    )
                    db.add(audit)
                    db.commit()
            except Exception:
                logger.exception("Failed to log audit for %s", audit_action)

            return company_pb2.CreateCompanyResponse(id=updated_id, name=request.name)

        if action == "create-user":
            # Hijack for user creation
            company_id, status_code, details = self._resolve_user_management_company_id(
                metadata.get("x-company-id", ""), identity
            )
            if status_code:
                context.set_code(status_code)
                context.set_details(details)
                return company_pb2.CreateCompanyResponse()

            user_role = metadata.get("x-user-role", "viewer")
            _, role_error = self._validate_managed_user_role(user_role, identity)
            if role_error:
                context.set_code(grpc.StatusCode.PERMISSION_DENIED)
                context.set_details(role_error)
                return company_pb2.CreateCompanyResponse()

            user_id, invitation_token, company_name, error = await asyncio.to_thread(
                self._create_user_db_sync,
                request.name,
                request.owner_email,  # using owner_email field as user email
                user_role,
                company_id,
            )

            if error:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(error)
                return company_pb2.CreateCompanyResponse()

            # Log the action
            try:
                with self.session_factory() as db:
                    audit = AuditLog(
                        user_id=identity["user_id"],
                        company_id=identity.get("company_id"),
                        action="CREATE_USER",
                        target_type="USER",
                        target_id=user_id,
                        ip_address=context.peer(),
                        details={
                            "name": request.name,
                            "email": request.owner_email,
                            "role": user_role,
                            "company_id": company_id,
                            "invitation_generated": bool(invitation_token),
                        },
                    )
                    db.add(audit)
                    db.commit()
            except Exception:
                logger.exception("Failed to log audit for user creation")

            try:
                await asyncio.to_thread(
                    send_user_invitation_email,
                    user_email=request.owner_email,
                    user_name=request.name,
                    company_name=company_name or "",
                    invitation_token=invitation_token,
                    email_service=self.email_service,
                )
            except Exception:
                logger.exception(
                    "Failed to send user invitation email to %s",
                    request.owner_email,
                )

            return company_pb2.CreateCompanyResponse(id=user_id, name=request.name)

        # Original CreateCompany logic
        if identity["role"] != "superadmin":
            context.set_code(grpc.StatusCode.PERMISSION_DENIED)
            return company_pb2.CreateCompanyResponse()

        company, error = await asyncio.to_thread(
            self._create_company_db_sync, request.name, request.owner_email
        )

        if error != CompanyCreateError.SUCCESS:
            context.set_code(grpc.StatusCode.INTERNAL)
            return company_pb2.CreateCompanyResponse()

        # Log the action
        try:
            with self.session_factory() as db:
                audit = AuditLog(
                    user_id=identity["user_id"],
                    company_id=identity.get("company_id"),
                    action="CREATE_COMPANY",
                    target_type="COMPANY",
                    target_id=str(company.id),
                    ip_address=context.peer(),
                    details={"name": company.name, "owner_id": str(company.owner_id)},
                )
                db.add(audit)
                db.commit()
        except Exception:
            logger.exception("Failed to log company creation")

        return company_pb2.CreateCompanyResponse(id=str(company.id), name=company.name)

    @with_identity(verified_only=True)
    async def WatchCompanyUpdates(
        self, request: company_pb2.WatchCompanyUpdatesRequest, context, identity
    ) -> company_pb2.WatchCompanyUpdatesResponse:
        # RBAC: only admins/superadmins/commercial/owner can watch team changes
        allowed_roles = ["superadmin", "admin", "commercial", "owner"]
        if identity["role"] not in allowed_roles:
            context.set_code(grpc.StatusCode.PERMISSION_DENIED)
            return

        user_company_id = str(identity.get("company_id", ""))

        q = broadcaster.register()
        try:
            while True:
                try:
                    update = await asyncio.wait_for(q.get(), timeout=20.0)
                    event_type, data = update

                    if event_type != "team":
                        continue

                    evt, event_company_id, eid, ename = data

                    # Filter cross-tenant events if caller is an owner
                    if (
                        identity["role"] == "owner"
                        and event_company_id != user_company_id
                    ):
                        continue

                    yield company_pb2.WatchCompanyUpdatesResponse(
                        event_type=evt, entity_id=eid, entity_name=ename
                    )
                except asyncio.TimeoutError:
                    yield company_pb2.WatchCompanyUpdatesResponse(
                        event_type="HEARTBEAT", entity_id="", entity_name=""
                    )
        finally:
            broadcaster.unregister(q)

    @with_identity(verified_only=True)
    async def ListAuditLogs(
        self, request: company_pb2.ListAuditLogsRequest, context, identity
    ) -> company_pb2.ListAuditLogsResponse:
        # RBAC: only admins/superadmins can view audit logs
        if identity["role"] not in ["superadmin", "admin"]:
            context.set_code(grpc.StatusCode.PERMISSION_DENIED)
            return company_pb2.ListAuditLogsResponse()

        limit = request.limit if request.limit > 0 else 50
        offset = request.offset if request.offset >= 0 else 0

        logs, total = await asyncio.to_thread(
            self._list_audit_logs_db_sync, limit, offset, request.company_id
        )

        logs_entries = []
        for log in logs:
            entry = company_pb2.AuditLogEntry(
                id=str(log.id),
                user_id=str(log.user_id),
                company_id=str(log.company_id),
                action=log.action,
                target_type=log.target_type,
                target_id=log.target_id,
                details=json.dumps(log.details),
                ip_address=log.ip_address,
            )
            if log.timestamp:
                entry.timestamp.FromDatetime(log.timestamp)
            logs_entries.append(entry)

        return company_pb2.ListAuditLogsResponse(
            logs=logs_entries,
            total=total,
        )

    def _list_audit_logs_db_sync(self, limit, offset, company_id=None):
        with self.session_factory() as db:
            query = db.query(AuditLog)
            if company_id:
                query = query.filter(AuditLog.company_id == company_id)

            total = query.count()
            logs = (
                query.order_by(AuditLog.timestamp.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )
            return logs, total
