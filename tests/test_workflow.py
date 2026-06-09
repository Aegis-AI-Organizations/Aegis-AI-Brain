import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker
from temporalio import activity
import uuid

from workflows.pentest_workflow import PentestWorkflow
from workflows.graph_pentest_workflow import GraphDrivenPentestWorkflow


@activity.defn(name="update_scan_status")
async def mock_update_scan_status(scan_id: str, new_status: str) -> str:
    return f"Successfully updated scan {scan_id} to status {new_status}"


@activity.defn(name="CreateSandbox")
async def mock_create_sandbox(request: dict) -> dict:
    scan_id = request["scan_id"]
    return {
        "namespace": f"aegis-war-room-{scan_id}",
        "endpoint": f"http://svc-{scan_id}.aegis-war-room-{scan_id}.svc.cluster.local:80",
    }


@activity.defn(name="DestroySandbox")
async def mock_destroy_sandbox(scan_id: str) -> str:
    return "CLEANED"


@activity.defn(name="save_vulnerabilities")
async def mock_save_vulnerabilities(scan_id: str, vulnerabilities: list) -> str:
    return f"Saved {len(vulnerabilities)} vulnerabilities for {scan_id}"


@activity.defn(name="generate_and_store_pdf_report")
async def mock_generate_and_store_pdf_report(
    scan_id: str, vulnerabilities: list
) -> str:
    return f"Stored PDF report for {scan_id}"


@activity.defn(name="run_pentest")
async def mock_run_pentest(target_ip: str, port: int) -> dict:
    return {"status": "COMPLETED", "vulnerabilities": []}


@activity.defn(name="identify_attack_targets")
async def mock_identify_attack_targets(company_id: str, agent_id: str | None = None):
    return [
        {
            "entry_id": "entry-auth",
            "target_id": "target-auth",
            "target_name": "auth-service",
            "target_kind": "service",
            "target_namespace": "aegis-system",
            "path": "/login",
            "label": "auth-service",
            "path_length": 2,
            "criticality": 100,
            "score": 998,
        },
        {
            "entry_id": "entry-admin",
            "target_id": "target-admin",
            "target_name": "admin-panel",
            "target_kind": "service",
            "target_namespace": "aegis-system",
            "path": "/admin",
            "label": "admin-panel",
            "path_length": 3,
            "criticality": 90,
            "score": 897,
        },
    ]


@activity.defn(name="build_sandbox_topology")
async def mock_build_sandbox_topology(
    company_id: str, target_ids: list[str] | None = None
):
    return {
        "containers": [
            {
                "name": "auth-service",
                "image": "nginx:latest",
                "ports": [{"number": 80, "protocol": "tcp"}],
            }
        ]
    }


@activity.defn(name="run_targeted_pentest")
async def mock_run_targeted_pentest(
    target_host: str, port: int, targets: list[dict]
) -> dict:
    return {
        "status": "COMPLETED",
        "vulnerabilities": [
            {
                "vuln_type": "SQLi",
                "target_endpoint": f"http://{target_host}:{port}{targets[0]['path']}",
            }
        ],
        "targets": targets,
        "target_count": len(targets),
    }


@pytest.mark.asyncio
async def test_pentest_workflow_success():
    """Test full workflow utilizing mock database activity."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        # Start a local worker using mock activity
        async with Worker(
            env.client,
            task_queue="TEST_QUEUE",
            workflows=[PentestWorkflow],
            activities=[
                mock_update_scan_status,
                mock_save_vulnerabilities,
                mock_generate_and_store_pdf_report,
                mock_run_pentest,
            ],
        ):
            async with Worker(
                env.client,
                task_queue="DEPLOYER_TASK_QUEUE",
                activities=[mock_create_sandbox, mock_destroy_sandbox],
            ):
                async with Worker(
                    env.client,
                    task_queue="PENTEST_TASK_QUEUE",
                    activities=[mock_run_pentest],
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
async def failing_update_scan_status(scan_id: str, status: str) -> str:
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
            activities=[
                failing_update_scan_status,
                mock_save_vulnerabilities,
                mock_generate_and_store_pdf_report,
                mock_run_pentest,
            ],
        ):
            async with Worker(
                env.client,
                task_queue="DEPLOYER_TASK_QUEUE",
                activities=[mock_create_sandbox, mock_destroy_sandbox],
            ):
                async with Worker(
                    env.client,
                    task_queue="PENTEST_TASK_QUEUE",
                    activities=[mock_run_pentest],
                ):
                    scan_id = str(uuid.uuid4())
                    with pytest.raises(Exception):
                        await env.client.execute_workflow(
                            PentestWorkflow.run,
                            args=[scan_id, "target"],
                            id=f"test-pentest-fail-{scan_id}",
                            task_queue="TEST_QUEUE_FAIL",
                        )


@pytest.mark.asyncio
async def test_graph_driven_pentest_workflow_success():
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="TEST_QUEUE_GRAPH",
            workflows=[GraphDrivenPentestWorkflow],
            activities=[
                mock_update_scan_status,
                mock_save_vulnerabilities,
                mock_generate_and_store_pdf_report,
                mock_identify_attack_targets,
                mock_build_sandbox_topology,
            ],
        ):
            async with Worker(
                env.client,
                task_queue="DEPLOYER_TASK_QUEUE",
                activities=[mock_create_sandbox, mock_destroy_sandbox],
            ):
                async with Worker(
                    env.client,
                    task_queue="PENTEST_TASK_QUEUE",
                    activities=[mock_run_targeted_pentest],
                ):
                    scan_id = str(uuid.uuid4())
                    result = await env.client.execute_workflow(
                        GraphDrivenPentestWorkflow.run,
                        args=[scan_id, "nginx:latest", "company-1"],
                        id=f"test-graph-pentest-{scan_id}",
                        task_queue="TEST_QUEUE_GRAPH",
                    )
                    assert (
                        f"Graph-driven scan {scan_id} on target nginx:latest successfully completed"
                        in result
                    )


def test_graph_driven_workflow_filters_selected_topology_targets():
    workflow = GraphDrivenPentestWorkflow()
    targets = workflow._normalize_targets(
        [
            {
                "entry_id": "entry-auth",
                "target_id": "target-auth",
                "target_name": "auth-service",
                "target_path": "/login",
                "score": 100,
            },
            {
                "entry_id": "entry-admin",
                "target_id": "target-admin",
                "target_name": "admin-service",
                "target_path": "/admin",
                "score": 90,
            },
        ]
    )

    selected_ids = workflow._parse_topology_target_ids("topology:target-admin")
    filtered = workflow._filter_targets(targets, selected_ids)

    assert len(filtered) == 1
    assert filtered[0]["target_id"] == "target-admin"
