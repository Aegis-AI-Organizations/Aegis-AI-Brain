import asyncio
import logging
import uuid
import grpc
import secrets
import bcrypt
from datetime import datetime, timezone, timedelta
from minio import Minio

from config.db import get_session_factory
from models.agent import Agent
from grpc_services.utils import to_pb_timestamp, with_identity
from config.config import (
    MINIO_ENDPOINT,
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
    MINIO_SECURE,
    MINIO_INGEST_BUCKET,
    MINIO_EXTERNAL_ENDPOINT,
    MINIO_EXTERNAL_SECURE,
)
import aegis.v2.agent_pb2 as agent_pb2
import aegis.v2.agent_pb2_grpc as agent_pb2_grpc
from utils.token_utils import is_valid_agent_token_format

logger = logging.getLogger("aegis_brain_agent")
AGENT_ACTIVE_WINDOW = timedelta(minutes=5)
INACTIVE_AGENT_STATUSES = {"OFFLINE", "ERROR"}
INTERNAL_ROLES = {"superadmin", "admin", "technicien", "support"}


class AgentService(agent_pb2_grpc.AgentServiceServicer):
    def __init__(self, temporal_client=None):
        self.session_factory = get_session_factory()
        # Initialize MinIO client
        self.minio_client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE,
        )
        self.presign_client = Minio(
            MINIO_EXTERNAL_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_EXTERNAL_SECURE,
        )
        self.temporal_client = temporal_client

        # Initialize Redis client for tracking latest agent uploads
        import redis
        from config.config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD

        try:
            if REDIS_PASSWORD:
                self.redis_client = redis.Redis(
                    host=REDIS_HOST,
                    port=int(REDIS_PORT),
                    password=REDIS_PASSWORD,
                    decode_responses=True,
                )
            else:
                self.redis_client = redis.Redis(
                    host=REDIS_HOST,
                    port=int(REDIS_PORT),
                    decode_responses=True,
                )
            logger.info("✅ AgentService connected to Redis")
        except Exception as e:
            logger.error(f"❌ AgentService failed to connect to Redis: {e}")
            self.redis_client = None

    @staticmethod
    def _normalize_status(status: str) -> str:
        return (status or "UNKNOWN").upper()

    @staticmethod
    def _ensure_aware(dt):
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def _resolve_company_scope(self, request_company_id: str, identity):
        role = (identity.get("role") or "").lower()
        identity_company_id = str(identity.get("company_id") or "")

        if role in INTERNAL_ROLES:
            company_id = request_company_id or identity_company_id
            if not company_id:
                return None, grpc.StatusCode.INVALID_ARGUMENT, "Missing company_id"
            return company_id, None, None

        if not identity_company_id:
            return None, grpc.StatusCode.PERMISSION_DENIED, "Missing company scope"

        if request_company_id and request_company_id != identity_company_id:
            return (
                None,
                grpc.StatusCode.PERMISSION_DENIED,
                "Cannot access another company agents",
            )

        return identity_company_id, None, None

    def _agent_to_proto(self, agent: Agent):
        record = agent_pb2.AgentRecord(
            id=str(agent.id),
            company_id=str(agent.company_id),
            name=agent.name or "",
            status=self._normalize_status(agent.status),
        )
        last_seen = to_pb_timestamp(self._ensure_aware(agent.last_seen))
        created_at = to_pb_timestamp(self._ensure_aware(agent.created_at))
        if last_seen is not None:
            record.last_seen.CopyFrom(last_seen)
        if created_at is not None:
            record.created_at.CopyFrom(created_at)
        return record

    def _is_agent_active(self, agent: Agent, now: datetime) -> bool:
        status = self._normalize_status(agent.status)
        if status in INACTIVE_AGENT_STATUSES:
            return False

        last_seen = self._ensure_aware(agent.last_seen)
        if last_seen is None:
            return False

        return now - last_seen <= AGENT_ACTIVE_WINDOW

    async def RegisterAgent(self, request, context):
        """
        Onboarding of the Rust agent using a deployment token (ag_...).
        Returns a unique agent_id.
        """
        token = request.token
        if not is_valid_agent_token_format(token):
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

        agent_name = request.name if request.name else f"Agent-{str(uuid.uuid4())[:8]}"
        # Generate a 256-bit secure secret (32 bytes -> hex string)
        agent_secret = secrets.token_hex(32)
        # Hash the secret using bcrypt
        token_hash = bcrypt.hashpw(agent_secret.encode(), bcrypt.gensalt()).decode()

        def _save_agent():
            with self.session_factory() as db:
                existing = (
                    db.query(Agent)
                    .filter(Agent.company_id == company_id, Agent.name == agent_name)
                    .first()
                )

                if existing:
                    existing.token_hash = token_hash
                    existing.status = "IDLE"
                    existing.last_seen = datetime.now(timezone.utc)
                    agent = existing
                else:
                    agent = Agent(
                        id=str(uuid.uuid4()),
                        company_id=company_id,
                        name=agent_name,
                        status="IDLE",
                        token_hash=token_hash,
                    )
                    db.add(agent)

                db.commit()
                return str(agent.id)

        try:
            agent_id = await asyncio.to_thread(_save_agent)
            logger.info(
                f"Agent registered/updated: {agent_id} for company {company_id}"
            )
            return agent_pb2.RegisterAgentResponse(
                agent_id=agent_id, agent_secret=agent_secret
            )
        except Exception as e:
            logger.error(f"Failed to register agent: {e}")
            await context.abort(
                grpc.StatusCode.INTERNAL, "Database error during registration"
            )

    async def UpdateAgentStatus(self, request, context):
        """
        Updates the agent's state (IDLE, UPLOADING, etc.) and last_seen timestamp.
        """
        status_to_save = request.status
        if request.status == "UPLOAD_COMPLETE":
            status_to_save = "IDLE"

        def _update_status():
            with self.session_factory() as db:
                agent = db.query(Agent).filter(Agent.id == request.agent_id).first()
                if not agent:
                    return False
                agent.status = status_to_save
                agent.last_seen = datetime.now(timezone.utc)
                db.commit()
                return True

        try:
            success = await asyncio.to_thread(_update_status)
            if not success:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Agent not found")

            # If status is UPLOAD_COMPLETE, start the Temporal Ingest topology workflow!
            if request.status == "UPLOAD_COMPLETE":
                object_name = request.payload_key
                if not object_name and self.redis_client:
                    try:
                        redis_key = f"agent:latest_upload:{request.agent_id}"
                        object_name = self.redis_client.get(redis_key)
                    except Exception as redis_err:
                        logger.error(
                            f"Failed to get latest upload key from Redis: {redis_err}"
                        )

                if object_name:
                    if self.temporal_client:
                        try:
                            workflow_id = f"ingest-{request.agent_id}-{int(datetime.now(timezone.utc).timestamp())}"
                            logger.info(
                                f"Starting IngestTopologyWorkflow for {object_name} with ID {workflow_id}"
                            )
                            await self.temporal_client.start_workflow(
                                "IngestTopologyWorkflow",
                                args=[
                                    {"bucket": MINIO_INGEST_BUCKET, "key": object_name}
                                ],
                                id=workflow_id,
                                task_queue="INGEST_TASK_QUEUE",
                            )
                        except Exception as temporal_err:
                            logger.error(
                                f"Failed to start IngestTopologyWorkflow: {temporal_err}"
                            )
                    else:
                        logger.warning(
                            "No Temporal client available on AgentService to start workflow!"
                        )
                else:
                    logger.warning(
                        f"No upload key found in request payload_key or Redis for agent {request.agent_id}"
                    )

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

        def _check_and_create_bucket():
            try:
                if not self.minio_client.bucket_exists(MINIO_INGEST_BUCKET):
                    self.minio_client.make_bucket(MINIO_INGEST_BUCKET)
            except Exception as bucket_err:
                logger.warning(
                    f"Failed to check/create bucket {MINIO_INGEST_BUCKET}: {bucket_err}"
                )

        await asyncio.to_thread(_check_and_create_bucket)

        try:
            # 3. Generate presigned URL for PUT (valid for 1 hour)
            url = await asyncio.to_thread(
                self.presign_client.presigned_put_object,
                MINIO_INGEST_BUCKET,
                object_name,
                expires=timedelta(hours=1),
            )
            # Store in Redis so we can link it back on UpdateAgentStatus("UPLOAD_COMPLETE")
            if self.redis_client:
                try:
                    redis_key = f"agent:latest_upload:{agent_id}"
                    self.redis_client.set(
                        redis_key, object_name, ex=3600
                    )  # expires in 1 hour
                except Exception as redis_err:
                    logger.error(
                        f"Failed to save latest upload key to Redis: {redis_err}"
                    )
            logger.info(f"Generated upload link for agent {agent_id}: {object_name}")
            return agent_pb2.GetUploadLinkResponse(
                url=url, method="PUT", object_name=object_name
            )
        except Exception as e:
            logger.error(f"Failed to generate MinIO presigned URL: {e}")
            await context.abort(
                grpc.StatusCode.INTERNAL, "Error generating upload link"
            )

    async def VerifyAgentSecret(self, request, context):
        """
        Validates an operational secret against an agent ID.
        Used by the Gateway to ensure the agent is authorized and is who they say they are.
        """
        agent_id = request.agent_id
        secret = request.secret

        def _verify():
            with self.session_factory() as db:
                agent = db.query(Agent).filter(Agent.id == agent_id).first()
                if not agent or not agent.token_hash:
                    return False, ""

                # Verify bcrypt hash
                is_valid = bcrypt.checkpw(secret.encode(), agent.token_hash.encode())
                return is_valid, agent.company_id

        try:
            valid, company_id = await asyncio.to_thread(_verify)
            return agent_pb2.VerifyAgentSecretResponse(
                valid=valid, tenant_id=str(company_id) if valid else ""
            )
        except Exception as e:
            logger.error(f"Error during agent secret verification: {e}")
            return agent_pb2.VerifyAgentSecretResponse(valid=False, tenant_id="")

    @with_identity(verified_only=True)
    async def ListAgents(self, request, context, identity):
        company_id, code, message = self._resolve_company_scope(
            request.company_id, identity
        )
        if code is not None:
            await context.abort(code, message)

        def _list_agents():
            with self.session_factory() as db:
                return (
                    db.query(Agent)
                    .filter(Agent.company_id == company_id)
                    .order_by(Agent.last_seen.desc(), Agent.created_at.desc())
                    .all()
                )

        try:
            agents = await asyncio.to_thread(_list_agents)
            return agent_pb2.ListAgentsResponse(
                agents=[self._agent_to_proto(agent) for agent in agents]
            )
        except Exception as e:
            logger.error(f"Failed to list agents for company {company_id}: {e}")
            await context.abort(
                grpc.StatusCode.INTERNAL, "Database error listing agents"
            )

    @with_identity(verified_only=True)
    async def GetAgentStatusSummary(self, request, context, identity):
        company_id, code, message = self._resolve_company_scope(
            request.company_id, identity
        )
        if code is not None:
            await context.abort(code, message)

        def _list_agents():
            with self.session_factory() as db:
                return (
                    db.query(Agent)
                    .filter(Agent.company_id == company_id)
                    .order_by(Agent.last_seen.desc(), Agent.created_at.desc())
                    .all()
                )

        try:
            agents = await asyncio.to_thread(_list_agents)
            now = datetime.now(timezone.utc)
            active_agents = sum(
                1 for agent in agents if self._is_agent_active(agent, now)
            )
            last_seen = next(
                (agent.last_seen for agent in agents if agent.last_seen), None
            )

            response = agent_pb2.GetAgentStatusSummaryResponse(
                total_agents=len(agents),
                active_agents=active_agents,
                inactive_agents=len(agents) - active_agents,
            )
            last_seen_ts = to_pb_timestamp(self._ensure_aware(last_seen))
            if last_seen_ts is not None:
                response.last_seen.CopyFrom(last_seen_ts)
            return response
        except Exception as e:
            logger.error(
                f"Failed to build agent status summary for company {company_id}: {e}"
            )
            await context.abort(
                grpc.StatusCode.INTERNAL, "Database error summarizing agents"
            )
