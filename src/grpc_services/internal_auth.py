import logging
import grpc
import asyncio
from aegis.v2 import internal_auth_pb2
from aegis.v2 import internal_auth_pb2_grpc
from config.db import get_session_factory
from models.company import Company

logger = logging.getLogger(__name__)

class InternalAuthService(internal_auth_pb2_grpc.InternalAuthServiceServicer):
    """InternalAuthService handles service-to-service authentication (e.g., Agent to Brain)."""

    def __init__(self):
        self._session_factory = None

    @property
    def session_factory(self):
        if self._session_factory is None:
            self._session_factory = get_session_factory()
        return self._session_factory

    async def VerifyToken(self, request, context):
        """Validates a deployment token and returns the company ID (TenantID)."""
        token = request.token
        if not token:
            logger.warning("VerifyToken called with empty token")
            return internal_auth_pb2.VerifyTokenResponse(valid=False)

        try:
            # Execute DB query in a thread to avoid blocking the event loop
            company_id = await asyncio.to_thread(self._verify_token_db_sync, token)
            
            if company_id:
                logger.info(f"Token verified successfully for company: {company_id}")
                return internal_auth_pb2.VerifyTokenResponse(
                    valid=True,
                    tenant_id=str(company_id)
                )
            else:
                logger.warning(f"Token verification failed for token: {token[:8]}...")
                return internal_auth_pb2.VerifyTokenResponse(valid=False)
        except Exception as e:
            logger.exception("Failed to verify token")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal server error during token verification")
            return internal_auth_pb2.VerifyTokenResponse(valid=False)

    def _verify_token_db_sync(self, token: str):
        """Synchronous DB query using SQLAlchemy session."""
        with self.session_factory() as db:
            # Query company by deployment_token and ensure it is active
            company = db.query(Company).filter(
                Company.deployment_token == token,
                Company.is_active == True
            ).first()
            if company:
                return company.id
            return None
