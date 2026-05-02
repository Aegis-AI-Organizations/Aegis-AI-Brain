import grpc
import jwt
import logging
from config.config import JWT_SECRET
from grpc_services.utils import verified_identity

logger = logging.getLogger("aegis_brain_auth")


class AuthInterceptor(grpc.aio.ServerInterceptor):
    """gRPC interceptor for JWT validation and verified identity injection."""

    _PUBLIC_METHODS = {
        "/aegis.v2.AuthService/Login",
        "/aegis.v2.AuthService/Refresh",
        "/aegis.v2.AuthService/Logout",
        "/aegis.v2.PingService/Ping",
    }

    @staticmethod
    def _unauthenticated_abort_message():
        return "Missing or invalid bearer token"

    def _build_unauthenticated_handler(self, handler):
        async def unary_unary(request, context):
            await context.abort(
                grpc.StatusCode.UNAUTHENTICATED,
                self._unauthenticated_abort_message(),
            )

        async def unary_stream(request, context):
            await context.abort(
                grpc.StatusCode.UNAUTHENTICATED,
                self._unauthenticated_abort_message(),
            )
            if False:
                yield None

        async def stream_unary(request_iterator, context):
            await context.abort(
                grpc.StatusCode.UNAUTHENTICATED,
                self._unauthenticated_abort_message(),
            )

        async def stream_stream(request_iterator, context):
            await context.abort(
                grpc.StatusCode.UNAUTHENTICATED,
                self._unauthenticated_abort_message(),
            )
            if False:
                yield None

        if handler.request_streaming and handler.response_streaming:
            return grpc.stream_stream_rpc_method_handler(
                stream_stream,
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )
        if handler.request_streaming:
            return grpc.stream_unary_rpc_method_handler(
                stream_unary,
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )
        if handler.response_streaming:
            return grpc.unary_stream_rpc_method_handler(
                unary_stream,
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )
        return grpc.unary_unary_rpc_method_handler(
            unary_unary,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )

    async def intercept_service(self, continuation, handler_call_details):
        verified_identity.set(None)
        metadata = dict(handler_call_details.invocation_metadata)
        auth_header = metadata.get("authorization") or metadata.get("Authorization", "")
        method = handler_call_details.method
        is_authenticated = False

        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
            if token:
                try:
                    payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
                    identity = {
                        "user_id": payload.get("sub"),
                        "company_id": payload.get("company_id"),
                        "role": payload.get("role"),
                    }
                    if identity["user_id"] and identity["company_id"]:
                        verified_identity.set(identity)
                        is_authenticated = True
                        logger.debug(
                            f"Identity verified for user: {identity['user_id']}"
                        )
                    else:
                        logger.warning("JWT missing required identity claims.")
                except jwt.ExpiredSignatureError:
                    logger.warning("Expired JWT token received.")
                except jwt.InvalidTokenError as e:
                    logger.warning(f"Invalid JWT token received: {e}")

        handler = await continuation(handler_call_details)
        if handler is None:
            return None

        if method in self._PUBLIC_METHODS or is_authenticated:
            return handler

        logger.warning(f"Unauthenticated access denied for method: {method}")
        return self._build_unauthenticated_handler(handler)
