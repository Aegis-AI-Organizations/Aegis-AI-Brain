import logging
import asyncio
import grpc

import aegis.v2.company_pb2 as company_pb2
import aegis.v2.company_pb2_grpc as company_pb2_grpc
from config.db import get_session_factory
from models.company import Company
from models.user import User

logger = logging.getLogger(__name__)


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
                return None, "Owner user not found"

            # 2. Check if company name already exists
            existing = db.query(Company).filter(Company.name == name).first()
            if existing:
                return None, "Company name already exists"

            try:
                new_company = Company(name=name, owner_id=owner.id)
                db.add(new_company)
                db.flush()  # Get ID

                # Update user's company_id
                owner.company_id = new_company.id

                db.commit()
                return new_company, None
            except Exception as e:
                db.rollback()
                logger.exception("Failed to create company")
                return None, str(e)

    async def CreateCompany(
        self, request: company_pb2.CreateCompanyRequest, context
    ) -> company_pb2.CreateCompanyResponse:
        company, error = await asyncio.to_thread(
            self._create_company_db_sync, request.name, request.owner_email
        )

        if error:
            if "exists" in error:
                context.set_code(grpc.StatusCode.ALREADY_EXISTS)
            else:
                context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(error)
            return company_pb2.CreateCompanyResponse()

        return company_pb2.CreateCompanyResponse(id=str(company.id), name=company.name)

    def _list_companies_db_sync(self):
        with self.session_factory() as db:
            companies = db.query(Company).all()
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
                    )
                )
            return result

    async def ListCompanies(
        self, request: company_pb2.ListCompaniesRequest, context
    ) -> company_pb2.ListCompaniesResponse:
        try:
            companies = await asyncio.to_thread(self._list_companies_db_sync)
            return company_pb2.ListCompaniesResponse(companies=companies)
        except Exception:
            logger.exception("Failed to list companies")
            context.set_code(grpc.StatusCode.INTERNAL)
            return company_pb2.ListCompaniesResponse()
