import logging
import asyncio
import enum
import grpc

import aegis.v2.company_pb2 as company_pb2
import aegis.v2.company_pb2_grpc as company_pb2_grpc
from config.db import get_session_factory
from models.company import Company
from models.user import User, UserRole
from sqlalchemy import String
from sqlalchemy.orm import joinedload
from grpc_services.utils import with_identity
from .broadcaster import broadcaster
from utils.auth_utils import hash_password
from models.audit_log import AuditLog
import uuid
import json

logger = logging.getLogger(__name__)


class CompanyCreateError(enum.Enum):
    SUCCESS = 0
    OWNER_NOT_FOUND = 1
    NAME_EXISTS = 2
    DB_ERROR = 3


class CompanyService(company_pb2_grpc.CompanyServiceServicer):
    """CompanyService handles company creation and administrative listing."""

    def __init__(self):
        self._session_factory = None

    @property
    def session_factory(self):
        if self._session_factory is None:
            self._session_factory = get_session_factory()
        return self._session_factory

    def _create_company_db_sync(
        self, name: str, owner_email: str, org_size: str = None, org_type: str = None
    ):
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
                new_company = Company(
                    name=name, owner_id=owner.id, org_size=org_size, org_type=org_type
                )
                db.add(new_company)
                db.flush()  # Get ID

                # Update user's company_id
                owner.company_id = new_company.id

                db.commit()
                # Broadcast company creation
                broadcaster.broadcast(
                    "team", ("COMPANY_CREATED", str(new_company.id), new_company.name)
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
        owner_password: str,
        org_size: str = None,
        org_type: str = None,
    ):
        with self.session_factory() as db:
            # 1. Check if email already exists
            existing_user = db.query(User).filter(User.email == owner_email).first()
            if existing_user:
                return None, None, None, "User already exists with this email"

            # 2. Check if company name already exists
            existing_company = (
                db.query(Company).filter(Company.name == company_name).first()
            )
            if existing_company:
                return None, None, None, "Company already exists with this name"

            try:
                # 3. Create Company
                deployment_token = f"ag_{uuid.uuid4().hex}"
                new_company = Company(
                    name=company_name,
                    deployment_token=deployment_token,
                    org_size=org_size,
                    org_type=org_type,
                )
                db.add(new_company)
                db.flush()  # Get ID

                # 4. Create Owner User
                new_owner = User(
                    name=owner_name,
                    email=owner_email,
                    password_hash=hash_password(owner_password),
                    role=UserRole.owner,
                    company_id=new_company.id,
                    is_active=True,
                )
                db.add(new_owner)
                db.flush()  # Get Owner ID

                # 5. Link Owner back to Company
                new_company.owner_id = new_owner.id

                db.commit()
                # Broadcast company creation
                broadcaster.broadcast(
                    "team", ("COMPANY_CREATED", str(new_company.id), new_company.name)
                )
                return (
                    str(new_company.id),
                    str(new_owner.id),
                    deployment_token,
                    None,
                )
            except Exception as e:
                db.rollback()
                logger.exception("Failed to onboard company")
                return None, None, None, f"Database error: {str(e)}"

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
            request.owner_password,
            company_pb2.OrganizationSize.Name(request.org_size),
            company_pb2.OrganizationType.Name(request.org_type),
        )

        company_id, owner_id, token, error = res

        if error:
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
                    },
                )
                db.add(audit)
                db.commit()
        except Exception:
            logger.exception("Failed to log audit for onboarding")

        return company_pb2.OnboardCompanyResponse(
            company_id=company_id, owner_id=owner_id, deployment_token=token
        )

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
                    query = query.filter(User.company_id == company_id)
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
                        "token_balance": 0,
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
                    owner_email = c.owner.email if c.owner else ""
                    owner_id = str(c.owner_id) if c.owner_id else ""
                    summary_kwargs = {
                        "id": str(c.id),
                        "name": c.name,
                        "owner_id": owner_id,
                        "owner_email": owner_email,
                        "member_count": len(c.members),
                        "deployment_token": c.deployment_token or "",
                        "org_size": company_pb2.OrganizationSize.Value(
                            c.org_size
                            if c.org_size
                            else "ORGANIZATION_SIZE_UNSPECIFIED"
                        ),
                        "org_type": company_pb2.OrganizationType.Value(
                            c.org_type
                            if c.org_type
                            else "ORGANIZATION_TYPE_UNSPECIFIED"
                        ),
                        "token_balance": c.token_balance,
                    }
                    if hasattr(company_pb2.CompanySummary, "avatar_url"):
                        summary_kwargs["avatar_url"] = (
                            c.owner.avatar_url if c.owner else ""
                        )
                    result.append(company_pb2.CompanySummary(**summary_kwargs))
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

    def _create_user_db_sync(self, name, email, password, role, company_id):
        with self.session_factory() as db:
            # Check if email exists
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                return None, "Email already in use"

            try:
                new_user = User(
                    name=name,
                    email=email,
                    password_hash=hash_password(password),
                    role=role,
                    company_id=company_id,
                    is_active=True,
                )
                db.add(new_user)
                db.commit()
                # Broadcast user creation
                broadcaster.broadcast("team", ("USER_CREATED", str(new_user.id), name))
                return str(new_user.id), None
            except Exception as e:
                db.rollback()
                return None, str(e)

    @with_identity(verified_only=True)
    async def CreateCompany(
        self, request: company_pb2.CreateCompanyRequest, context, identity
    ) -> company_pb2.CreateCompanyResponse:
        metadata = dict(context.invocation_metadata())
        action = metadata.get("x-action", "create-company")

        if action == "create-user":
            # Hijack for user creation
            allowed_roles = ["superadmin", "admin", "owner"]
            if identity["role"] not in allowed_roles:
                context.set_code(grpc.StatusCode.PERMISSION_DENIED)
                return company_pb2.CreateCompanyResponse()

            user_role = metadata.get("x-user-role", "viewer")
            user_password = metadata.get("x-user-password", "")
            company_id = metadata.get("x-company-id", "")

            # If owner, force company_id
            if identity["role"] == "owner":
                company_id = str(identity["company_id"])

            user_id, error = await asyncio.to_thread(
                self._create_user_db_sync,
                request.name,
                request.owner_email,  # using owner_email field as user email
                user_password,
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
                        },
                    )
                    db.add(audit)
                    db.commit()
            except Exception:
                logger.exception("Failed to log audit for user creation")

            return company_pb2.CreateCompanyResponse(id=user_id, name=request.name)

        # Original CreateCompany logic
        if identity["role"] != "superadmin":
            context.set_code(grpc.StatusCode.PERMISSION_DENIED)
            return company_pb2.CreateCompanyResponse()

        company, error = await asyncio.to_thread(
            self._create_company_db_sync,
            request.name,
            request.owner_email,
            company_pb2.OrganizationSize.Name(request.org_size),
            company_pb2.OrganizationType.Name(request.org_type),
        )

        if error != CompanyCreateError.SUCCESS:
            if error == CompanyCreateError.NAME_EXISTS:
                context.set_code(grpc.StatusCode.ALREADY_EXISTS)
                context.set_details("Company name already exists")
            elif error == CompanyCreateError.OWNER_NOT_FOUND:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("Owner user not found")
            else:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("Failed to create company")
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
        # RBAC: only admins/superadmins/commercial can watch all team changes
        # (Simplified for now, but could be restricted by company_id)
        allowed_roles = ["superadmin", "admin", "commercial", "owner"]
        if identity["role"] not in allowed_roles:
            context.set_code(grpc.StatusCode.PERMISSION_DENIED)
            return

        q = broadcaster.register()
        try:
            while True:
                try:
                    update = await asyncio.wait_for(q.get(), timeout=20.0)
                    event_type, data = update

                    if event_type != "team":
                        continue

                    evt, eid, ename = data
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

        return company_pb2.ListAuditLogsResponse(
            logs=[
                company_pb2.AuditLogEntry(
                    id=str(log.id),
                    user_id=str(log.user_id),
                    company_id=str(log.company_id),
                    action=log.action,
                    target_type=log.target_type,
                    target_id=log.target_id,
                    details=json.dumps(log.details),
                    ip_address=log.ip_address,
                    timestamp=None,  # Handled below
                )
                for log in logs
            ],
            total=total,
        )

        # Fill timestamps
        for i, log in enumerate(logs):
            res.logs[i].timestamp.FromDatetime(log.timestamp)

        return res

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
