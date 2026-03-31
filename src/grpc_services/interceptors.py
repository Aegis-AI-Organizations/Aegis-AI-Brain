import grpc
import jwt
import logging
from config.config import JWT_SECRET
from grpc_services.utils import verified_identity

logger = logging.getLogger("aegis_brain_auth")


class AuthInterceptor(grpc.aio.ServerInterceptor):
    """gRPC interceptor for JWT validation and verified identity injection."""

    async def intercept_service(self, continuation, handler_call_details):
        metadata = dict(handler_call_details.invocation_metadata)
        auth_header = metadata.get("authorization", "")

        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
                identity = {
                    "user_id": payload.get("sub"),
                    "company_id": payload.get("company_id"),
                    "role": payload.get("role"),
                }
                if identity["user_id"] and identity["company_id"]:
                    verified_identity.set(identity)
                    logger.debug(f"Identity verified for user: {identity['user_id']}")
                else:
                    logger.warning("JWT missing required identity claims.")

            except jwt.ExpiredSignatureError:
                logger.warning("Expired JWT token received.")
            except jwt.InvalidTokenError as e:
                logger.warning(f"Invalid JWT token received: {e}")
        else:
            # Check for legacy metadata fallback (primarily for tests)
            user_id = metadata.get("user-id")
            company_id = metadata.get("company-id")
            if user_id and company_id:
                logger.debug(f"Using legacy metadata fallback for user: {user_id}")

        return await continuation(handler_call_details)
