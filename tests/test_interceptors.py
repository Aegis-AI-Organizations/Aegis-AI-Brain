import pytest
import jwt
import time
from unittest.mock import AsyncMock
from config.config import JWT_SECRET
from grpc_services.interceptors import AuthInterceptor
from grpc_services.utils import verified_identity


class MockHandlerCallDetails:
    def __init__(self, metadata, method="/aegis.v2.ScanService/StartScan"):
        self.invocation_metadata = metadata
        self.method = method


@pytest.mark.asyncio
async def test_auth_interceptor_valid_token():
    # Clear verified_identity before test
    verified_identity.set(None)

    interceptor = AuthInterceptor()
    token = jwt.encode(
        {"sub": "test-user", "company_id": "test-company", "role": "admin"},
        JWT_SECRET,
        algorithm="HS256",
    )
    metadata = [("authorization", f"Bearer {token}")]
    handler_details = MockHandlerCallDetails(metadata)

    continuation = AsyncMock()
    await interceptor.intercept_service(continuation, handler_details)

    continuation.assert_called_once_with(handler_details)

    # Verify the context var is set
    identity = verified_identity.get()
    assert identity is not None
    assert identity["user_id"] == "test-user"
    assert identity["company_id"] == "test-company"


@pytest.mark.asyncio
async def test_auth_interceptor_no_auth_header():
    verified_identity.set(None)
    interceptor = AuthInterceptor()
    metadata = []
    handler_details = MockHandlerCallDetails(metadata)

    continuation = AsyncMock()
    await interceptor.intercept_service(continuation, handler_details)

    continuation.assert_called_once_with(handler_details)
    assert verified_identity.get() is None


@pytest.mark.asyncio
async def test_auth_interceptor_invalid_token():
    verified_identity.set(None)
    interceptor = AuthInterceptor()
    metadata = [("authorization", "Bearer invalid-token")]
    handler_details = MockHandlerCallDetails(metadata)

    continuation = AsyncMock()
    await interceptor.intercept_service(continuation, handler_details)

    continuation.assert_called_once_with(handler_details)
    assert verified_identity.get() is None


@pytest.mark.asyncio
async def test_auth_interceptor_expired_token():
    verified_identity.set(None)
    interceptor = AuthInterceptor()
    token = jwt.encode({"exp": time.time() - 3600}, JWT_SECRET, algorithm="HS256")
    metadata = [("authorization", f"Bearer {token}")]
    handler_details = MockHandlerCallDetails(metadata)

    continuation = AsyncMock()
    await interceptor.intercept_service(continuation, handler_details)

    continuation.assert_called_once_with(handler_details)
    assert verified_identity.get() is None


@pytest.mark.asyncio
async def test_auth_interceptor_malformed_header():
    # Test "Bearer " without token (should not raise IndexError)
    verified_identity.set(None)
    interceptor = AuthInterceptor()
    metadata = [("authorization", "Bearer ")]
    handler_details = MockHandlerCallDetails(metadata)

    continuation = AsyncMock()
    await interceptor.intercept_service(continuation, handler_details)

    continuation.assert_called_once_with(handler_details)
    assert verified_identity.get() is None


@pytest.mark.asyncio
async def test_auth_interceptor_spoofing_prevention():
    # Test metadata present but no JWT (should result in no verified identity)
    verified_identity.set(None)
    interceptor = AuthInterceptor()
    metadata = [
        ("user-id", "evil-user"),
        ("company-id", "victim-company"),
    ]
    handler_details = MockHandlerCallDetails(metadata)

    continuation = AsyncMock()
    await interceptor.intercept_service(continuation, handler_details)

    continuation.assert_called_once_with(handler_details)
    assert verified_identity.get() is None
