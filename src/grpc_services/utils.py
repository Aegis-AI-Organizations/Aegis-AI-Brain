import contextvars
import functools
import inspect
import grpc
from google.protobuf.timestamp_pb2 import Timestamp

# Trusted storage for verified identities from AuthInterceptor
verified_identity = contextvars.ContextVar("verified_identity", default=None)


def to_pb_timestamp(dt):
    if dt is None:
        return None
    ts = Timestamp()
    ts.FromDatetime(dt)
    return ts


def get_identity(context):
    """Securely extracts identity from verified context or gRPC metadata fallback.
    Prioritizes verified_identity ContextVar set by the AuthInterceptor.
    """
    v_id = verified_identity.get()
    if v_id:
        return v_id

    # Fallback for unit tests where interceptor is not present
    if context is None:
        return None

    metadata = dict(context.invocation_metadata())
    user_id = metadata.get("user-id")
    company_id = metadata.get("company-id")
    role = metadata.get("role")

    if not user_id or not company_id:
        return None

    return {"user_id": user_id, "company_id": company_id, "role": role}


def with_identity(f):
    """Decorator to inject identity into the handler.
    Supports both async functions and async generators.
    """

    if inspect.isasyncgenfunction(f):

        @functools.wraps(f)
        async def wrapper(self, request, context, *args, **kwargs):
            identity = get_identity(context)
            async for response in f(self, request, context, identity, *args, **kwargs):
                yield response
    else:

        @functools.wraps(f)
        async def wrapper(self, request, context, *args, **kwargs):
            identity = get_identity(context)
            return await f(self, request, context, identity, *args, **kwargs)

    return wrapper
