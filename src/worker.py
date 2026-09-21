import logging
from concurrent.futures import ThreadPoolExecutor
from temporalio.worker import Worker

from workflows.pentest_workflow import PentestWorkflow
from workflows.graph_pentest_workflow import GraphDrivenPentestWorkflow
from activities.db_activities import (
    update_scan_status,
    update_scan_debug_bundle,
    update_scan_crew_report,
    save_vulnerabilities,
    generate_and_store_pdf_report,
)
from activities.attack_targets import identify_attack_targets
from activities.sandbox_topology import build_sandbox_topology
from activities.temporal_activities import check_task_queue_pollers
from activities.minio_artifacts import download_minio_artifact
from config.config import BRAIN_TASK_QUEUE
from services.temporal_client_holder import set_temporal_client

logger = logging.getLogger("aegis_brain_worker")


async def start_worker(client):
    set_temporal_client(client)
    logger.info(
        f"Registering Brain worker on queue {BRAIN_TASK_QUEUE} with PentestWorkflow and DB activities"
    )
    worker = Worker(
        client,
        task_queue=BRAIN_TASK_QUEUE,
        workflows=[PentestWorkflow, GraphDrivenPentestWorkflow],
        activities=[
            update_scan_status,
            update_scan_debug_bundle,
            update_scan_crew_report,
            save_vulnerabilities,
            generate_and_store_pdf_report,
            identify_attack_targets,
            build_sandbox_topology,
            check_task_queue_pollers,
            download_minio_artifact,
        ],
        activity_executor=ThreadPoolExecutor(max_workers=10),
    )
    logger.info(
        f"🚀 Worker ready to process tasks on queue {BRAIN_TASK_QUEUE} with graph-driven orchestration enabled..."
    )
    await worker.run()
