import asyncio
import logging
import uuid
import grpc
from datetime import datetime, timezone

from config.db import get_session_factory
from models.agent import Agent
import aegis.v2.agent_pb2 as agent_pb2
import aegis.v2.agent_pb2_grpc as agent_pb2_grpc

logger = logging.getLogger("aegis_brain_agent")

class AgentService(agent_pb2_grpc.AgentServiceServicer):
    def __init__(self):
        self.session_factory = get_session_factory()

    async def RegisterAgent(self, request, context):
        """
        Onboarding of the Rust agent using a deployment token (ag_...).
        Returns a unique agent_id.
        """
        token = request.token
        if not token or not token.startswith("ag_"):
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid deployment token format")

        from grpc_services.internal_auth import InternalAuthService
        # Reuse existing token verification logic
        company_id = await asyncio.to_thread(
            InternalAuthService()._verify_token_db_sync, token
        )

        if not company_id:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid or inactive deployment token")

        agent_id = str(uuid.uuid4())
        
        def _save_agent():
            with self.session_factory() as db:
                agent = Agent(
                    id=agent_id,
                    company_id=company_id,
                    name=request.name if request.name else f"Agent-{agent_id[:8]}",
                    status="IDLE"
                )
                db.add(agent)
                db.commit()
        
        try:
            await asyncio.to_thread(_save_agent)
            logger.info(f"New agent onboarded: {agent_id} for company {company_id}")
            return agent_pb2.RegisterAgentResponse(agent_id=agent_id)
        except Exception as e:
            logger.error(f"Failed to register agent: {e}")
            await context.abort(grpc.StatusCode.INTERNAL, "Database error during registration")

    async def UpdateAgentStatus(self, request, context):
        """
        Updates the agent's state (IDLE, UPLOADING, etc.) and last_seen timestamp.
        """
        def _update_status():
            with self.session_factory() as db:
                agent = db.query(Agent).filter(Agent.id == request.agent_id).first()
                if not agent:
                    return False
                agent.status = request.status
                agent.last_seen = datetime.now(timezone.utc)
                db.commit()
                return True

        try:
            success = await asyncio.to_thread(_update_status)
            if not success:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Agent not found")
                
            return agent_pb2.UpdateAgentStatusResponse(success=True)
        except Exception as e:
            logger.error(f"Failed to update agent status: {e}")
            await context.abort(grpc.StatusCode.INTERNAL, "Database error during status update")

    async def GetUploadLink(self, request, context):
        """
        Generates a presigned MinIO URL for the agent to upload infrastructure files/logs.
        """
        # Placeholder logic for MinIO presigned URL generation
        logger.info(f"Upload link requested by agent {request.agent_id} for file {request.filename}")
        
        # In the future, this will use a MinIO client to generate a real presigned URL
        mock_url = f"http://minio:9000/aegis-ingest/{request.agent_id}/{request.filename}?token=mock-presigned-signature"
        return agent_pb2.GetUploadLinkResponse(url=mock_url, method="PUT")
