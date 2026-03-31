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

        if not auth_header.startswith("Bearer "):
            return await continuation(handler_call_details)

        parts = auth_header.split(" ", 1)
        if len(parts) != 2:
            logger.warning("Malformed Authorization header received.")
            # We don't abort here to allow public pings, but we don't set verified_identity
            return await continuation(handler_call_details)

        token = parts[1]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])

            # Securely inject the verified identity into the ContextVar
            identity = {
                "user_id": payload.get("sub"),
                "company_id": payload.get("company_id"),
                "role": payload.get("role"),
            }
            if identity["user_id"] and identity["company_id"]:
                verified_identity.set(identity)

        except jwt.ExpiredSignatureError:
            logger.warning("Expired JWT token received.")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token received: {e}")

        return await continuation(handler_call_details)
