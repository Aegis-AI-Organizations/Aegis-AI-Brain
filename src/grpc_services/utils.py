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


def get_identity(context, verified_only=True):
    """Securely extracts identity from verified context or gRPC metadata fallback.
    Prioritizes verified_identity ContextVar set by the AuthInterceptor.
    """
    v_id = verified_identity.get()
    if v_id:
        return v_id

    if verified_only:
        return None

    if context is None:
        return None

    metadata = dict(context.invocation_metadata())
    user_id = metadata.get("user-id")
    company_id = metadata.get("company-id")
    role = metadata.get("role")

    if not user_id or not company_id:
        return None

    return {"user_id": user_id, "company_id": company_id, "role": role}


def with_identity(verified_only=True):
    """Decorator to inject identity into the handler.
    Supports both async functions and async generators.
    Fails closed if identity cannot be resolved.
    """

    def decorator(f):
        if inspect.isasyncgenfunction(f):

            @functools.wraps(f)
            async def wrapper(self, request, context, *args, **kwargs):
                identity = get_identity(context, verified_only=verified_only)
                if not identity:
                    await context.abort(
                        grpc.StatusCode.UNAUTHENTICATED, "Unauthenticated"
                    )
                async for response in f(
                    self, request, context, identity, *args, **kwargs
                ):
                    yield response

        else:

            @functools.wraps(f)
            async def wrapper(self, request, context, *args, **kwargs):
                identity = get_identity(context, verified_only=verified_only)
                if not identity:
                    await context.abort(
                        grpc.StatusCode.UNAUTHENTICATED, "Unauthenticated"
                    )
                return await f(self, request, context, identity, *args, **kwargs)

        return wrapper

    # Support @with_identity and @with_identity(verified_only=True)
    if callable(verified_only):
        func = verified_only
        verified_only = True
        return decorator(func)

    return decorator
