import asyncio
import logging
import os
from temporalio.client import Client
from temporalio.worker import Worker

from concurrent.futures import ThreadPoolExecutor

from workflows.pentest_workflow import PentestWorkflow
from activities.db_activities import (
    update_scan_status,
    save_vulnerabilities,
    generate_and_store_pdf_report,
)
from activities.kubernetes_activities import deploy_sandbox_target, cleanup_sandbox


async def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("aegis_brain")

    temporal_host = os.getenv("TEMPORAL_HOST", "localhost:7233")
    grpc_port = os.getenv("GRPC_PORT", "50051")

    logger.info(
        f"🧠 Aegis AI Brain starting... Connecting to Temporal at {temporal_host}"
    )

    try:
        client = await Client.connect(temporal_host)
        logger.info("✅ Connected to Temporal!")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Temporal: {e}")
        return

    brain_queue = os.getenv("BRAIN_TASK_QUEUE", "BRAIN_TASK_QUEUE")

    worker = Worker(
        client,
        task_queue=brain_queue,
        workflows=[PentestWorkflow],
        activities=[
            update_scan_status,
            save_vulnerabilities,
            generate_and_store_pdf_report,
            deploy_sandbox_target,
            cleanup_sandbox,
        ],
        activity_executor=ThreadPoolExecutor(max_workers=10),
    )

    logger.info(f"🚀 Worker ready to process tasks on queue {brain_queue}...")

    from grpc_server import serve

    await asyncio.gather(worker.run(), serve(grpc_port, client))


if __name__ == "__main__":
    asyncio.run(main())
