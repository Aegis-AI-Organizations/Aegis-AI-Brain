import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import uuid
import grpc
from datetime import datetime, timedelta, timezone
from grpc_services.agent import AgentService
from grpc_services.utils import verified_identity
import aegis.v2.agent_pb2 as agent_pb2

VALID_AGENT_TOKEN = "ag_0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefg"


@pytest.fixture
def agent_service():
    with patch("grpc_services.agent.get_session_factory"), patch(
        "grpc_services.agent.Minio"
    ):
        service = AgentService()
        return service


@pytest.mark.asyncio
async def test_register_agent_success(agent_service):
    token = VALID_AGENT_TOKEN
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

    with patch("asyncio.to_thread", side_effect=[True, None, "http://minio/upload"]):
        # We mock asyncio.to_thread directly to avoid issues with mocked MinIO methods
        response = await agent_service.GetUploadLink(request, context)
        assert response.url == "http://minio/upload"
        assert response.method == "PUT"
        assert response.object_name.endswith("_logs.tar.gz")


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
    request = agent_pb2.RegisterAgentRequest(token=VALID_AGENT_TOKEN, name="TestAgent")
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

    with patch("asyncio.to_thread", side_effect=[True, None, Exception("minio error")]):
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


@pytest.mark.asyncio
async def test_list_agents_for_current_company(agent_service):
    now = datetime.now(timezone.utc)
    agent = MagicMock()
    agent.id = uuid.uuid4()
    agent.company_id = uuid.uuid4()
    agent.name = "prod-agent"
    agent.status = "IDLE"
    agent.last_seen = now
    agent.created_at = now - timedelta(minutes=1)
    request = agent_pb2.ListAgentsRequest()
    context = AsyncMock(spec=grpc.aio.ServicerContext)
    identity_token = verified_identity.set(
        {"user_id": "user-1", "company_id": str(agent.company_id), "role": "owner"}
    )

    try:
        with patch("asyncio.to_thread", return_value=[agent]):
            response = await agent_service.ListAgents(request, context)
    finally:
        verified_identity.reset(identity_token)

    assert len(response.agents) == 1
    assert response.agents[0].id == str(agent.id)
    assert response.agents[0].company_id == str(agent.company_id)
    assert response.agents[0].name == "prod-agent"
    assert response.agents[0].status == "IDLE"


@pytest.mark.asyncio
async def test_list_agents_blocks_cross_company_access(agent_service):
    request = agent_pb2.ListAgentsRequest(company_id="other-company")
    context = AsyncMock(spec=grpc.aio.ServicerContext)
    context.abort.side_effect = grpc.aio.AbortError(
        grpc.StatusCode.PERMISSION_DENIED, "forbidden"
    )
    identity_token = verified_identity.set(
        {"user_id": "user-1", "company_id": "company-1", "role": "owner"}
    )

    try:
        with pytest.raises(grpc.aio.AbortError):
            await agent_service.ListAgents(request, context)
    finally:
        verified_identity.reset(identity_token)


@pytest.mark.asyncio
async def test_agent_status_summary_counts_active_and_inactive(agent_service):
    now = datetime.now(timezone.utc)
    active_agent = MagicMock()
    active_agent.last_seen = now
    active_agent.status = "IDLE"
    inactive_agent = MagicMock()
    inactive_agent.last_seen = now - timedelta(minutes=10)
    inactive_agent.status = "IDLE"
    offline_agent = MagicMock()
    offline_agent.last_seen = now
    offline_agent.status = "OFFLINE"
    request = agent_pb2.GetAgentStatusSummaryRequest()
    context = AsyncMock(spec=grpc.aio.ServicerContext)
    identity_token = verified_identity.set(
        {"user_id": "user-1", "company_id": "company-1", "role": "viewer"}
    )

    try:
        with patch(
            "asyncio.to_thread",
            return_value=[active_agent, inactive_agent, offline_agent],
        ):
            response = await agent_service.GetAgentStatusSummary(request, context)
    finally:
        verified_identity.reset(identity_token)

    assert response.total_agents == 3
    assert response.active_agents == 1
    assert response.inactive_agents == 2
    assert response.HasField("last_seen")
