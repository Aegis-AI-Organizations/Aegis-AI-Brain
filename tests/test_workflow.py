import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker
from temporalio import activity
import uuid

from workflows.pentest_workflow import PentestWorkflow


@activity.defn(name="update_scan_status")
async def mock_update_scan_status(args: list) -> str:
    scan_id, new_status = args
    return f"Successfully updated scan {scan_id} to status {new_status}"


@pytest.mark.asyncio
async def test_pentest_workflow_success():
    """Test full workflow utilizing mock database activity."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        # Start a local worker using mock activity
        async with Worker(
            env.client,
            task_queue="TEST_QUEUE",
            workflows=[PentestWorkflow],
            activities=[mock_update_scan_status],
        ):
            scan_id = str(uuid.uuid4())
            result = await env.client.execute_workflow(
                PentestWorkflow.run,
                args=[scan_id, "nginx:latest"],
                id=f"test-pentest-{scan_id}",
                task_queue="TEST_QUEUE",
            )
            assert (
                f"Scan {scan_id} on target nginx:latest successfully completed"
                in result
            )


# Create a failing mock activity
@activity.defn(name="update_scan_status")
async def failing_update_scan_status(args: list) -> str:
    scan_id, status = args
    if status == "COMPLETED":
        raise Exception("Failed midway")
    return "ok"


@pytest.mark.asyncio
async def test_pentest_workflow_failure():
    """Test full workflow falling back on FAILED status update."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="TEST_QUEUE_FAIL",
            workflows=[PentestWorkflow],
            activities=[failing_update_scan_status],
        ):
            scan_id = str(uuid.uuid4())
            with pytest.raises(Exception):
                await env.client.execute_workflow(
                    PentestWorkflow.run,
                    args=[scan_id, "target"],
                    id=f"test-pentest-fail-{scan_id}",
                    task_queue="TEST_QUEUE_FAIL",
                )
