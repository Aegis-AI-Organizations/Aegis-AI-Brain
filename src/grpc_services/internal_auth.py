import logging
import asyncio
import aegis.v2.internal_auth_pb2 as internal_auth_pb2
import aegis.v2.internal_auth_pb2_grpc as internal_auth_pb2_grpc
from config.db import get_db_connection

logger = logging.getLogger(__name__)


class InternalAuthService(internal_auth_pb2_grpc.InternalAuthServiceServicer):
    """gRPC service for verifying agent deployment tokens. Caching is handled by the API Gateway."""

    def _verify_token_db_sync(self, token: str) -> str:
        """Synchronously verifies an agent token and returns the company_id."""
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            # Deployment tokens are stored directly in the 'companies' table
            cur.execute(
                "SELECT id FROM companies WHERE deployment_token = %s",
                (token,),
            )
            row = cur.fetchone()
            cur.close()
            if row:
                return str(row[0])
            return None
        except Exception as e:
            logger.error(f"Database error during token verification: {e}")
            return None
        finally:
            if conn:
                conn.close()

    async def VerifyToken(
        self, request: internal_auth_pb2.VerifyTokenRequest, context
    ) -> internal_auth_pb2.VerifyTokenResponse:
        """gRPC handler for token verification."""
        company_id = await asyncio.to_thread(self._verify_token_db_sync, request.token)

        if not company_id:
            return internal_auth_pb2.VerifyTokenResponse(valid=False, tenant_id="")

        return internal_auth_pb2.VerifyTokenResponse(valid=True, tenant_id=company_id)
