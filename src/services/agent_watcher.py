import asyncio
import logging
import redis.asyncio as redis
from sqlalchemy.orm import Session
from config.db import get_engine
from models.agent import Agent
from config.config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD

logger = logging.getLogger("aegis_brain.agent_watcher")

class AgentWatcher:
    def __init__(self):
        self.redis_url = f"redis://{REDIS_HOST}:{REDIS_PORT}"
        self.redis_password = REDIS_PASSWORD
        self.engine = get_engine()

    async def start(self):
        """Starts the Redis keyspace notification listener."""
        logger.info(f"📡 AgentWatcher starting... Subscribing to Redis at {self.redis_url}")
        
        try:
            r = redis.from_url(
                self.redis_url, 
                password=self.redis_password,
                decode_responses=True
            )
            
            # Subscribe to expired events
            pubsub = r.pubsub()
            # __keyevent@0__:expired is the standard channel for DB 0 expirations
            await pubsub.subscribe("__keyevent@0__:expired")
            
            logger.info("✅ AgentWatcher subscribed to Redis expiration events")
            
            async for message in pubsub.listen():
                if message["type"] == "message":
                    key = message["data"]
                    if key.startswith("agent:health:"):
                        agent_id = key.split(":")[-1]
                        await self._handle_agent_offline(agent_id)
                        
        except Exception as e:
            logger.error(f"❌ AgentWatcher error: {e}")
            # Wait before retry
            await asyncio.sleep(5)
            await self.start()

    async def _handle_agent_offline(self, agent_id: str):
        """Updates the agent status to OFFLINE in the database."""
        logger.warning(f"⚠️ Agent {agent_id} heartbeat timeout! Marking as OFFLINE.")
        
        try:
            with Session(self.engine) as session:
                agent = session.query(Agent).filter(Agent.id == agent_id).first()
                if agent:
                    agent.status = "OFFLINE"
                    session.commit()
                    logger.info(f"✅ Agent {agent_id} status updated to OFFLINE")
                else:
                    logger.error(f"❌ Agent {agent_id} not found in database")
        except Exception as e:
            logger.error(f"❌ Failed to update agent {agent_id} status: {e}")

async def start_agent_watcher():
    watcher = AgentWatcher()
    await watcher.start()
