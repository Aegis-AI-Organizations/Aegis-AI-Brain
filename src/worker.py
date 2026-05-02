import logging
from concurrent.futures import ThreadPoolExecutor
from temporalio.worker import Worker

from workflows.pentest_workflow import PentestWorkflow
from activities.db_activities import (
    update_scan_status,
    save_vulnerabilities,
    generate_and_store_pdf_report,
)
from activities.kubernetes_activities import deploy_sandbox_target, cleanup_sandbox
from config.config import BRAIN_TASK_QUEUE

logger = logging.getLogger("aegis_brain_worker")


async def start_worker(client):
    worker = Worker(
        client,
        task_queue=BRAIN_TASK_QUEUE,
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
    logger.info(f"🚀 Worker ready to process tasks on queue {BRAIN_TASK_QUEUE}...")
    await worker.run()
