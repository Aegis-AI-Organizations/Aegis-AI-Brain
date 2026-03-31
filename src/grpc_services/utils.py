import functools
from google.protobuf.timestamp_pb2 import Timestamp


def to_pb_timestamp(dt):
    if dt is None:
        return None
    ts = Timestamp()
    ts.FromDatetime(dt)
    return ts


def get_identity(context):
    """Extract identity meta-data from gRPC context."""
    metadata = dict(context.invocation_metadata())
    user_id = metadata.get("user-id")
    company_id = metadata.get("company-id")
    role = metadata.get("role")
    return {"user_id": user_id, "company_id": company_id, "role": role}


def with_identity(f):
    """Decorator to inject identity into the handler."""

    @functools.wraps(f)
    async def wrapper(self, request, context, *args, **kwargs):
        identity = get_identity(context)
        return await f(self, request, context, identity, *args, **kwargs)

    return wrapper
