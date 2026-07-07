import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker
from temporalio import activity
import uuid

from workflows.pentest_workflow import PentestWorkflow
from workflows.graph_pentest_workflow import GraphDrivenPentestWorkflow


CREATED_SANDBOX_REQUESTS = []


@activity.defn(name="update_scan_status")
async def mock_update_scan_status(scan_id: str, new_status: str) -> str:
    return f"Successfully updated scan {scan_id} to status {new_status}"


@activity.defn(name="CreateSandbox")
async def mock_create_sandbox(request: dict) -> dict:
    CREATED_SANDBOX_REQUESTS.append(request)
    scan_id = request["scan_id"]
    endpoint_workload = request.get("preferred_endpoint_workload", "")
    return {
        "namespace": f"aegis-war-room-{scan_id}",
        "endpoint": f"http://svc-{scan_id}.aegis-war-room-{scan_id}.svc.cluster.local:80",
        "endpoint_workload": endpoint_workload,
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


@activity.defn(name="SeedTargetDatabases")
async def mock_seed_target_databases(request: dict) -> dict:
    scan_id = request["scan_id"]
    return {
        "namespace": f"aegis-war-room-{scan_id}",
        "seeded": ["postgres"],
        "seeded_count": 1,
        "seed_flag": "aegis-flag-1234",
    }


@activity.defn(name="DownloadMinIOArtifact")
async def mock_download_minio_artifact(reference: str) -> dict:
    return {
        "bucket": "aegis-ingest",
        "key": "targets/sandbox.json",
        "target_image": "topology:minio",
        "sandbox_request": {
            "topology_json": '{"containers":[{"name":"web","image":"nginx","ports":[{"number":80}]}]}',
            "preferred_endpoint_workload": "web",
        },
    }


@activity.defn(name="run_pentest")
async def mock_run_pentest(target_ip: str, port: int) -> dict:
    return {"status": "COMPLETED", "vulnerabilities": []}


@activity.defn(name="identify_attack_targets")
async def mock_identify_attack_targets(
    company_id: str,
    agent_id: str | None = None,
    target_ids: list[str] | None = None,
):
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
                mock_seed_target_databases,
                mock_download_minio_artifact,
                mock_run_pentest,
            ],
        ):
            async with Worker(
                env.client,
                task_queue="DEPLOYER_TASK_QUEUE",
                activities=[mock_create_sandbox, mock_destroy_sandbox, mock_seed_target_databases],
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
                mock_seed_target_databases,
                mock_download_minio_artifact,
                mock_run_pentest,
            ],
        ):
            async with Worker(
                env.client,
                task_queue="DEPLOYER_TASK_QUEUE",
                activities=[mock_create_sandbox, mock_destroy_sandbox, mock_seed_target_databases],
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
                mock_seed_target_databases,
                mock_download_minio_artifact,
                mock_identify_attack_targets,
                mock_build_sandbox_topology,
            ],
        ):
            async with Worker(
                env.client,
                task_queue="DEPLOYER_TASK_QUEUE",
                    activities=[mock_create_sandbox, mock_destroy_sandbox, mock_seed_target_databases],
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


@pytest.mark.asyncio
async def test_graph_driven_workflow_downloads_minio_artifact_before_deploying():
    CREATED_SANDBOX_REQUESTS.clear()
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="TEST_QUEUE_GRAPH_MINIO",
            workflows=[GraphDrivenPentestWorkflow],
            activities=[
                mock_update_scan_status,
                mock_save_vulnerabilities,
                mock_generate_and_store_pdf_report,
                mock_seed_target_databases,
                mock_download_minio_artifact,
                mock_identify_attack_targets,
                mock_build_sandbox_topology,
            ],
        ):
            async with Worker(
                env.client,
                task_queue="DEPLOYER_TASK_QUEUE",
                    activities=[mock_create_sandbox, mock_destroy_sandbox, mock_seed_target_databases],
            ):
                async with Worker(
                    env.client,
                    task_queue="PENTEST_TASK_QUEUE",
                    activities=[mock_run_targeted_pentest],
                ):
                    scan_id = str(uuid.uuid4())
                    result = await env.client.execute_workflow(
                        GraphDrivenPentestWorkflow.run,
                        args=[
                            scan_id,
                            "minio://aegis-ingest/targets/sandbox.json",
                            "company-1",
                        ],
                        id=f"test-graph-pentest-minio-{scan_id}",
                        task_queue="TEST_QUEUE_GRAPH_MINIO",
                    )

    assert "topology:minio" in result
    assert CREATED_SANDBOX_REQUESTS[-1]["scan_id"] == scan_id
    assert CREATED_SANDBOX_REQUESTS[-1]["preferred_endpoint_workload"] == "web"
    assert "topology_json" in CREATED_SANDBOX_REQUESTS[-1]


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


def test_graph_driven_workflow_selects_preferred_endpoint_workload():
    workflow = GraphDrivenPentestWorkflow()
    topology = {
        "containers": [
            {"name": "web-frontend", "image": "nginx:1.27"},
            {"id": "container-api", "name": "api", "image": "ghcr.io/aegis/api:anon"},
        ]
    }
    attack_targets = [
        {
            "target_name": "api",
            "entry_name": "api",
            "label": "api",
            "target_id": "target-api",
        }
    ]

    assert (
        workflow._select_preferred_endpoint_workload(topology, attack_targets) == "api"
    )
    assert (
        workflow._select_preferred_endpoint_workload(
            topology,
            [],
            {"container-api"},
        )
        == "api"
    )


def test_graph_driven_workflow_uses_graph_targets_when_selected_filter_is_too_strict():
    workflow = GraphDrivenPentestWorkflow()
    targets = workflow._normalize_targets(
        [
            {
                "entry_id": "route-cadvisor",
                "target_id": "route-cadvisor",
                "target_name": "cadvisor-vm-epitech",
                "target_path": "/metrics",
                "criticality": 60,
                "path_length": 0,
                "score": 6000,
            }
        ]
    )

    filtered = workflow._filter_targets(targets, {"container-cadvisor"})

    assert filtered == []
    assert targets[0]["score"] == 6000
    assert targets[0]["criticality"] == 60


def test_graph_driven_workflow_deprioritizes_observability_endpoint():
    workflow = GraphDrivenPentestWorkflow()
    topology = {
        "containers": [
            {
                "name": "backrest-vm-epitech",
                "image": "garethgeorge/backrest:latest",
                "ports": [{"number": 9898}],
            },
            {
                "name": "cadvisor-vm-epitech",
                "image": "gcr.io/cadvisor/cadvisor:latest",
                "ports": [{"number": 8080}],
            },
            {
                "name": "prometheus-vm-epitech",
                "image": "prom/prometheus:latest",
                "ports": [{"number": 9090}],
            },
        ]
    }
    attack_targets = [
        {
            "target_name": "cadvisor-vm-epitech",
            "entry_name": "cadvisor-vm-epitech",
            "label": "cadvisor-vm-epitech",
            "target_id": "target-cadvisor",
        }
    ]

    assert (
        workflow._select_preferred_endpoint_workload(topology, attack_targets)
        == "backrest-vm-epitech"
    )
