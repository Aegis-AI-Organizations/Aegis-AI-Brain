import asyncio
import logging
import uuid
import grpc
from datetime import datetime, timezone, timedelta
from minio import Minio

from config.db import get_session_factory
from models.agent import Agent
from config.config import (
    MINIO_ENDPOINT,
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
    MINIO_SECURE,
    MINIO_INGEST_BUCKET,
)
import aegis.v2.agent_pb2 as agent_pb2
import aegis.v2.agent_pb2_grpc as agent_pb2_grpc

logger = logging.getLogger("aegis_brain_agent")


class AgentService(agent_pb2_grpc.AgentServiceServicer):
    def __init__(self):
        self.session_factory = get_session_factory()
        # Initialize MinIO client
        self.minio_client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE,
        )

    async def RegisterAgent(self, request, context):
        """
        Onboarding of the Rust agent using a deployment token (ag_...).
        Returns a unique agent_id.
        """
        token = request.token
        if not token or not token.startswith("ag_"):
            await context.abort(
                grpc.StatusCode.UNAUTHENTICATED, "Invalid deployment token format"
            )

        from grpc_services.internal_auth import InternalAuthService

        # Reuse existing token verification logic
        company_id = await asyncio.to_thread(
            InternalAuthService()._verify_token_db_sync, token
        )

        if not company_id:
            await context.abort(
                grpc.StatusCode.UNAUTHENTICATED, "Invalid or inactive deployment token"
            )

        agent_id = str(uuid.uuid4())

        def _save_agent():
            with self.session_factory() as db:
                agent = Agent(
                    id=agent_id,
                    company_id=company_id,
                    name=request.name if request.name else f"Agent-{agent_id[:8]}",
                    status="IDLE",
                )
                db.add(agent)
                db.commit()

        try:
            await asyncio.to_thread(_save_agent)
            logger.info(f"New agent onboarded: {agent_id} for company {company_id}")
            return agent_pb2.RegisterAgentResponse(agent_id=agent_id)
        except Exception as e:
            logger.error(f"Failed to register agent: {e}")
            await context.abort(
                grpc.StatusCode.INTERNAL, "Database error during registration"
            )

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
            await context.abort(
                grpc.StatusCode.INTERNAL, "Database error during status update"
            )

    async def GetUploadLink(self, request, context):
        """
        Generates a presigned MinIO URL for the agent to upload infrastructure files/logs.
        Path pattern: agents/{agent_id}/{timestamp}_{filename}
        """
        agent_id = request.agent_id
        filename = request.filename

        # 1. Verify agent existence
        def _check_agent():
            with self.session_factory() as db:
                return db.query(Agent).filter(Agent.id == agent_id).first() is not None

        if not await asyncio.to_thread(_check_agent):
            await context.abort(
                grpc.StatusCode.NOT_FOUND, f"Agent {agent_id} not found"
            )

        # 2. Sanitize and build object name
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        object_name = f"agents/{agent_id}/{timestamp}_{filename}"

        try:
            # 3. Generate presigned URL for PUT (valid for 1 hour)
            url = await asyncio.to_thread(
                self.minio_client.presigned_put_object,
                MINIO_INGEST_BUCKET,
                object_name,
                expires=timedelta(hours=1),
            )
            logger.info(f"Generated upload link for agent {agent_id}: {object_name}")
            return agent_pb2.GetUploadLinkResponse(url=url, method="PUT")
        except Exception as e:
            logger.error(f"Failed to generate MinIO presigned URL: {e}")
            await context.abort(
                grpc.StatusCode.INTERNAL, "Error generating upload link"
            )
