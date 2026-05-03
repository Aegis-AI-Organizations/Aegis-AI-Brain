import pytest
from unittest.mock import MagicMock, patch
import uuid
import grpc
from grpc_services.agent import AgentService
import aegis.v2.agent_pb2 as agent_pb2

@pytest.fixture
def agent_service():
    with patch("grpc_services.agent.get_session_factory"), \
         patch("grpc_services.agent.Minio"):
        service = AgentService()
        return service

@pytest.mark.asyncio
async def test_register_agent_success(agent_service):
    token = "ag_valid_token"
    company_id = "comp_123"
    request = agent_pb2.RegisterAgentRequest(deployment_token=token, name="TestAgent")
    context = MagicMock()

    # Mock the internal auth verification
    with patch("grpc_services.internal_auth.InternalAuthService._verify_token_db_sync", return_value=company_id), \
         patch("asyncio.to_thread", side_effect=[company_id, None]):
        
        response = await agent_service.RegisterAgent(request, context)
        assert response.agent_id is not None

@pytest.mark.asyncio
async def test_register_agent_invalid_token(agent_service):
    request = agent_pb2.RegisterAgentRequest(deployment_token="invalid", name="TestAgent")
    context = MagicMock()

    with patch("grpc_services.internal_auth.InternalAuthService._verify_token_db_sync", return_value=None), \
         patch("asyncio.to_thread", return_value=None):
        
        await agent_service.RegisterAgent(request, context)
        context.abort.assert_called_with(grpc.StatusCode.UNAUTHENTICATED, "Invalid deployment token")

@pytest.mark.asyncio
async def test_update_agent_status_success(agent_service):
    agent_id = str(uuid.uuid4())
    request = agent_pb2.UpdateAgentStatusRequest(agent_id=agent_id, status="IDLE")
    context = MagicMock()

    with patch("asyncio.to_thread", return_value=True):
        response = await agent_service.UpdateAgentStatus(request, context)
        assert response.success is True

@pytest.mark.asyncio
async def test_get_upload_link_success(agent_service):
    agent_id = str(uuid.uuid4())
    request = agent_pb2.GetUploadLinkRequest(agent_id=agent_id, filename="logs.tar.gz")
    context = MagicMock()
    
    agent_mock = MagicMock()
    agent_mock.company_id = "c1"

    with patch("asyncio.to_thread", return_value=agent_mock), \
         patch.object(agent_service.minio_client, "presigned_put_object", return_value="http://minio/upload"):
        
        response = await agent_service.GetUploadLink(request, context)
        assert response.url == "http://minio/upload"
        assert response.method == "PUT"

@pytest.mark.asyncio
async def test_get_upload_link_agent_not_found(agent_service):
    request = agent_pb2.GetUploadLinkRequest(agent_id="unknown", filename="test.txt")
    context = MagicMock()

    with patch("asyncio.to_thread", return_value=None):
        await agent_service.GetUploadLink(request, context)
        context.abort.assert_called_with(grpc.StatusCode.NOT_FOUND, "Agent not found")
