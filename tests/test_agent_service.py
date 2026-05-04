import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import uuid
import grpc
from grpc_services.agent import AgentService
import aegis.v2.agent_pb2 as agent_pb2


@pytest.fixture
def agent_service():
    with patch("grpc_services.agent.get_session_factory"), patch(
        "grpc_services.agent.Minio"
    ):
        service = AgentService()
        return service


@pytest.mark.asyncio
async def test_register_agent_success(agent_service):
    token = "ag_valid_token"
    company_id = "comp_123"
    request = agent_pb2.RegisterAgentRequest(token=token, name="TestAgent")
    context = AsyncMock(spec=grpc.aio.ServicerContext)

    # Mock the internal auth verification
    with patch(
        "grpc_services.internal_auth.InternalAuthService._verify_token_db_sync",
        return_value=company_id,
    ), patch("asyncio.to_thread", side_effect=[company_id, None]):
        response = await agent_service.RegisterAgent(request, context)
        assert response.agent_id is not None


@pytest.mark.asyncio
async def test_register_agent_invalid_token(agent_service):
    request = agent_pb2.RegisterAgentRequest(token="invalid", name="TestAgent")
    context = AsyncMock(spec=grpc.aio.ServicerContext)
    # Define a side effect that behaves like abort
    context.abort.side_effect = grpc.aio.AbortError(
        grpc.StatusCode.UNAUTHENTICATED, "Invalid token"
    )

    with patch(
        "grpc_services.internal_auth.InternalAuthService._verify_token_db_sync",
        return_value=None,
    ), patch("asyncio.to_thread", return_value=None):
        with pytest.raises(grpc.aio.AbortError):
            await agent_service.RegisterAgent(request, context)


@pytest.mark.asyncio
async def test_update_agent_status_success(agent_service):
    agent_id = str(uuid.uuid4())
    request = agent_pb2.UpdateAgentStatusRequest(agent_id=agent_id, status="IDLE")
    context = AsyncMock(spec=grpc.aio.ServicerContext)

    with patch("asyncio.to_thread", return_value=True):
        response = await agent_service.UpdateAgentStatus(request, context)
        assert response.success is True


@pytest.mark.asyncio
async def test_get_upload_link_success(agent_service):
    agent_id = str(uuid.uuid4())
    request = agent_pb2.GetUploadLinkRequest(agent_id=agent_id, filename="logs.tar.gz")
    context = AsyncMock(spec=grpc.aio.ServicerContext)

    agent_mock = MagicMock()
    agent_mock.company_id = "c1"

    with patch("asyncio.to_thread", side_effect=[agent_mock, "http://minio/upload"]):
        # We mock asyncio.to_thread directly to avoid issues with mocked MinIO methods
        response = await agent_service.GetUploadLink(request, context)
        assert response.url == "http://minio/upload"
        assert response.method == "PUT"


@pytest.mark.asyncio
async def test_get_upload_link_agent_not_found(agent_service):
    request = agent_pb2.GetUploadLinkRequest(agent_id="unknown", filename="test.txt")
    context = AsyncMock(spec=grpc.aio.ServicerContext)
    context.abort.side_effect = grpc.aio.AbortError(
        grpc.StatusCode.NOT_FOUND, "Agent not found"
    )

    with patch("asyncio.to_thread", return_value=None):
        with pytest.raises(grpc.aio.AbortError):
            await agent_service.GetUploadLink(request, context)
@pytest.mark.asyncio
async def test_register_agent_db_error(agent_service):
    request = agent_pb2.RegisterAgentRequest(token="ag_valid", name="TestAgent")
    context = AsyncMock(spec=grpc.aio.ServicerContext)
    context.abort.side_effect = grpc.aio.AbortError(
        grpc.StatusCode.INTERNAL, "DB error"
    )

    with patch(
        "grpc_services.internal_auth.InternalAuthService._verify_token_db_sync",
        return_value="comp_1",
    ), patch("asyncio.to_thread", side_effect=["comp_1", Exception("db error")]):
        with pytest.raises(grpc.aio.AbortError):
            await agent_service.RegisterAgent(request, context)


@pytest.mark.asyncio
async def test_update_agent_status_not_found(agent_service):
    request = agent_pb2.UpdateAgentStatusRequest(agent_id="unknown", status="IDLE")
    context = AsyncMock(spec=grpc.aio.ServicerContext)
    context.abort.side_effect = grpc.aio.AbortError(
        grpc.StatusCode.NOT_FOUND, "Not found"
    )

    with patch("asyncio.to_thread", return_value=False):
        with pytest.raises(grpc.aio.AbortError):
            await agent_service.UpdateAgentStatus(request, context)


@pytest.mark.asyncio
async def test_update_agent_status_error(agent_service):
    request = agent_pb2.UpdateAgentStatusRequest(agent_id="a1", status="IDLE")
    context = AsyncMock(spec=grpc.aio.ServicerContext)
    context.abort.side_effect = grpc.aio.AbortError(grpc.StatusCode.INTERNAL, "Error")

    with patch("asyncio.to_thread", side_effect=Exception("error")):
        with pytest.raises(grpc.aio.AbortError):
            await agent_service.UpdateAgentStatus(request, context)


@pytest.mark.asyncio
async def test_get_upload_link_error(agent_service):
    request = agent_pb2.GetUploadLinkRequest(agent_id="a1", filename="test.txt")
    context = AsyncMock(spec=grpc.aio.ServicerContext)
    context.abort.side_effect = grpc.aio.AbortError(grpc.StatusCode.INTERNAL, "Error")

    with patch("asyncio.to_thread", side_effect=[True, Exception("minio error")]):
        with pytest.raises(grpc.aio.AbortError):
            await agent_service.GetUploadLink(request, context)


@pytest.mark.asyncio
async def test_verify_agent_secret_success(agent_service):
    request = agent_pb2.VerifyAgentSecretRequest(agent_id="a1", secret="s1")
    context = AsyncMock(spec=grpc.aio.ServicerContext)

    with patch("asyncio.to_thread", return_value=(True, "comp1")):
        response = await agent_service.VerifyAgentSecret(request, context)
        assert response.valid is True
        assert response.tenant_id == "comp1"


@pytest.mark.asyncio
async def test_verify_agent_secret_failure(agent_service):
    request = agent_pb2.VerifyAgentSecretRequest(agent_id="a1", secret="wrong")
    context = AsyncMock(spec=grpc.aio.ServicerContext)

    with patch("asyncio.to_thread", return_value=(False, "")):
        response = await agent_service.VerifyAgentSecret(request, context)
        assert response.valid is False


@pytest.mark.asyncio
async def test_verify_agent_secret_exception(agent_service):
    request = agent_pb2.VerifyAgentSecretRequest(agent_id="a1", secret="s1")
    context = AsyncMock(spec=grpc.aio.ServicerContext)

    with patch("asyncio.to_thread", side_effect=Exception("error")):
        response = await agent_service.VerifyAgentSecret(request, context)
        assert response.valid is False
