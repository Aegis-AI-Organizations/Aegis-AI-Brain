import logging
import asyncio
import enum
import grpc

import aegis.v2.company_pb2 as company_pb2
import aegis.v2.company_pb2_grpc as company_pb2_grpc
from config.db import get_session_factory
from models.company import Company
from models.user import User, UserRole
from sqlalchemy.orm import joinedload
from grpc_services.utils import with_identity
from utils.auth_utils import hash_password
import uuid

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
                return new_company, CompanyCreateError.SUCCESS
            except Exception:
                db.rollback()
                logger.exception("Failed to create company")
                return None, CompanyCreateError.DB_ERROR

    @with_identity(verified_only=True)
    async def CreateCompany(
        self, request: company_pb2.CreateCompanyRequest, context, identity
    ) -> company_pb2.CreateCompanyResponse:
        if identity["role"] != "superadmin":
            context.set_code(grpc.StatusCode.PERMISSION_DENIED)
            context.set_details("Only SuperAdmin can create companies")
            return company_pb2.CreateCompanyResponse()

        company, error = await asyncio.to_thread(
            self._create_company_db_sync, request.name, request.owner_email
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

        return company_pb2.CreateCompanyResponse(id=str(company.id), name=company.name)

    def _onboard_company_db_sync(
        self,
        company_name: str,
        owner_name: str,
        owner_email: str,
        owner_password: str,
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
                    name=company_name, deployment_token=deployment_token
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
        )

        company_id, owner_id, token, error = res

        if error:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(error)
            return company_pb2.OnboardCompanyResponse()

        return company_pb2.OnboardCompanyResponse(
            company_id=company_id, owner_id=owner_id, deployment_token=token
        )

    def _list_companies_db_sync(self):
        with self.session_factory() as db:
            companies = (
                db.query(Company)
                .options(joinedload(Company.owner), joinedload(Company.members))
                .all()
            )
            result = []
            for c in companies:
                owner_email = c.owner.email if c.owner else ""
                owner_id = str(c.owner_id) if c.owner_id else ""
                result.append(
                    company_pb2.CompanySummary(
                        id=str(c.id),
                        name=c.name,
                        owner_id=owner_id,
                        owner_email=owner_email,
                        member_count=len(c.members),
                        deployment_token=c.deployment_token or "",
                    )
                )
            return result

    @with_identity(verified_only=True)
    async def ListCompanies(
        self, request: company_pb2.ListCompaniesRequest, context, identity
    ) -> company_pb2.ListCompaniesResponse:
        if identity["role"] != "superadmin":
            context.set_code(grpc.StatusCode.PERMISSION_DENIED)
            context.set_details("Only SuperAdmin can list companies")
            return company_pb2.ListCompaniesResponse()

        try:
            companies = await asyncio.to_thread(self._list_companies_db_sync)
            return company_pb2.ListCompaniesResponse(companies=companies)
        except Exception:
            logger.exception("Failed to list companies")
            context.set_code(grpc.StatusCode.INTERNAL)
            return company_pb2.ListCompaniesResponse()
