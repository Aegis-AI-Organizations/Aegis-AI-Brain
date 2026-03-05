import asyncio
import logging
import os
from temporalio.client import Client
from temporalio.worker import Worker
from dotenv import load_dotenv

from concurrent.futures import ThreadPoolExecutor

from workflows.pentest_workflow import PentestWorkflow
from activities.db_activities import update_scan_status
from activities.kubernetes_activities import deploy_sandbox_target, cleanup_sandbox


async def init_brain():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("aegis_brain")

    load_dotenv()

    temporal_host = os.getenv("TEMPORAL_HOST", "localhost:7233")
    logger.info(
        f"🧠 Aegis AI Brain starting... Connecting to Temporal at {temporal_host}"
    )

    try:
        client = await Client.connect(temporal_host)
        logger.info("✅ Connected to Temporal!")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Temporal: {e}")
        return

    worker = Worker(
        client,
        task_queue="PENTEST_TASK_QUEUE",
        workflows=[PentestWorkflow],
        activities=[update_scan_status, deploy_sandbox_target, cleanup_sandbox],
        activity_executor=ThreadPoolExecutor(max_workers=10),
    )

    logger.info("🚀 Worker ready to process tasks on queue PENTEST_TASK_QUEUE...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(init_brain())
