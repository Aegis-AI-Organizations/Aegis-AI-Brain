import asyncio
import logging
from temporalio.client import Client

from config.config import TEMPORAL_HOST, GRPC_PORT
from worker import start_worker
from grpc_server import serve


async def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("aegis_brain")

    logger.info(
        f"🧠 Aegis AI Brain starting... Connecting to Temporal at {TEMPORAL_HOST}"
    )

    try:
        client = await Client.connect(TEMPORAL_HOST)
        logger.info("✅ Connected to Temporal!")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Temporal: {e}")
        return

    await asyncio.gather(start_worker(client), serve(GRPC_PORT, client))


if __name__ == "__main__":
    asyncio.run(main())
