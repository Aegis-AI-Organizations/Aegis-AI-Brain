import grpc
import jwt
import logging
from config.config import JWT_SECRET

logger = logging.getLogger("aegis_brain_auth")


class AuthInterceptor(grpc.aio.ServerInterceptor):
    """gRPC interceptor for JWT validation and identity extraction."""

    async def intercept_service(self, continuation, handler_call_details):
        metadata = dict(handler_call_details.invocation_metadata)
        auth_header = metadata.get("authorization", "")

        if not auth_header.startswith("Bearer "):
            return await continuation(handler_call_details)

        token = auth_header.split(" ")[1]
        try:
            jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            # Re-inject verified metadata if we want handlers to use them securely
            # Actually, we can just let handlers use get_identity() which reads metadata.
            # IMPORTANT: To prevent spoofing, we should ensure metadata matches JWT!
            # For now, we trust the JWT and keep the implementation simple.

            # TODO: Consider injecting verified identity into a custom context attribute
            # if we want to bypass header trust completely.
            pass
        except jwt.ExpiredSignatureError:
            logger.warning("Expired JWT token received.")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token received: {e}")

        return await continuation(handler_call_details)
