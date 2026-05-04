import asyncio
import logging
from temporalio.client import Client

from config.config import TEMPORAL_HOST, TEMPORAL_NAMESPACE, GRPC_PORT
from config.db import get_engine
from models.base import Base

# Ensure all models are loaded before create_all (needed for SQLAlchemy)
import models.user as _user  # noqa: F401
import models.company as _company  # noqa: F401
import models.agent as _agent  # noqa: F401
import models.audit_log as _audit  # noqa: F401
import models.refresh_token as _refresh  # noqa: F401

from worker import start_worker
from grpc_server import serve


async def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("aegis_brain")

    logger.info(
        f"🧠 Aegis AI Brain starting... Connecting to Temporal at {TEMPORAL_HOST}"
    )

    # Automatically create missing database tables
    try:
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables synchronized")
    except Exception as e:
        logger.error(f"❌ Failed to synchronize database tables: {e}")

    try:
        client = await Client.connect(TEMPORAL_HOST, namespace=TEMPORAL_NAMESPACE)
        logger.info("✅ Connected to Temporal!")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Temporal: {e}")
        return

    from services.agent_watcher import start_agent_watcher
    await asyncio.gather(
        start_worker(client), 
        serve(GRPC_PORT, client),
        start_agent_watcher()
    )


if __name__ == "__main__":
    asyncio.run(main())
