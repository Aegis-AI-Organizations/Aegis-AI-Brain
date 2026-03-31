import pytest
import grpc
import jwt
from unittest.mock import AsyncMock, MagicMock
from config.config import JWT_SECRET
from grpc_services.interceptors import AuthInterceptor

class MockHandlerCallDetails:
    def __init__(self, metadata):
        self.invocation_metadata = metadata

@pytest.mark.asyncio
async def test_auth_interceptor_valid_token():
    interceptor = AuthInterceptor()
    token = jwt.encode({"user_id": "test", "company_id": "comp", "role": "admin"}, JWT_SECRET, algorithm="HS256")
    metadata = [("authorization", f"Bearer {token}")]
    handler_details = MockHandlerCallDetails(metadata)
    
    continuation = AsyncMock()
    await interceptor.intercept_service(continuation, handler_details)
    
    continuation.assert_called_once_with(handler_details)

@pytest.mark.asyncio
async def test_auth_interceptor_no_auth_header():
    interceptor = AuthInterceptor()
    metadata = []
    handler_details = MockHandlerCallDetails(metadata)
    
    continuation = AsyncMock()
    await interceptor.intercept_service(continuation, handler_details)
    
    continuation.assert_called_once_with(handler_details)

@pytest.mark.asyncio
async def test_auth_interceptor_invalid_token():
    interceptor = AuthInterceptor()
    metadata = [("authorization", "Bearer invalid-token")]
    handler_details = MockHandlerCallDetails(metadata)
    
    continuation = AsyncMock()
    # Interceptor should log and continue (handler checks identity)
    await interceptor.intercept_service(continuation, handler_details)
    
    continuation.assert_called_once_with(handler_details)

@pytest.mark.asyncio
async def test_auth_interceptor_expired_token():
    import time
    interceptor = AuthInterceptor()
    token = jwt.encode({"exp": time.time() - 3600}, JWT_SECRET, algorithm="HS256")
    metadata = [("authorization", f"Bearer {token}")]
    handler_details = MockHandlerCallDetails(metadata)
    
    continuation = AsyncMock()
    await interceptor.intercept_service(continuation, handler_details)
    
    continuation.assert_called_once_with(handler_details)
