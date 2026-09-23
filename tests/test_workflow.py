import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker
from temporalio import activity
from temporalio.exceptions import ApplicationError
import uuid

from workflows.pentest_workflow import PentestWorkflow
from workflows.graph_pentest_workflow import GraphDrivenPentestWorkflow


CREATED_SANDBOX_REQUESTS = []
CREWAI_REQUESTS = []
TARGETED_PENTEST_CALLS = []
REPORT_REQUESTS = []
CREWAI_REPORT_UPDATES = []
TASK_QUEUE_POLLER_CHECKS = []


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
    scan_id: str, vulnerabilities: list, crew_report_markdown: str = ""
) -> str:
    REPORT_REQUESTS.append(
        {
            "scan_id": scan_id,
            "vulnerabilities": vulnerabilities,
            "crew_report_markdown": crew_report_markdown,
        }
    )
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
            "topology_json": '{"containers":[{"name":"web","image":"nginx","ports":[{"number":80}]}],"databaseSchemas":[],"externalMocks":[]}',
            "preferred_endpoint_workload": "web",
        },
    }


@activity.defn(name="DownloadMinIOArtifact")
async def mock_download_invalid_topology_artifact(reference: str) -> dict:
    return {
        "bucket": "aegis-ingest",
        "key": "targets/invalid-sandbox.json",
        "target_image": "topology:minio",
        "sandbox_request": {
            "topology_json": '{"containers":[{"name":"web","image":"nginx","ports":[{"number":"80"}]}],"databaseSchemas":[],"externalMocks":[]}',
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


@activity.defn(name="identify_attack_targets")
async def mock_identify_attack_targets_with_external_url(
    company_id: str,
    agent_id: str | None = None,
    target_ids: list[str] | None = None,
):
    return [
        {
            "entry_id": "entry-web",
            "target_id": "target-admin",
            "target_name": "admin-panel",
            "target_kind": "service",
            "path": "http://source.example.test/admin?debug=true",
            "label": "admin-panel",
            "path_length": 1,
            "criticality": 90,
            "score": 900,
        }
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
        ],
        "databaseSchemas": [],
        "externalMocks": [],
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


@activity.defn(name="run_targeted_pentest")
async def mock_capture_run_targeted_pentest(
    target_host: str, port: int, targets: list[dict]
) -> dict:
    TARGETED_PENTEST_CALLS.append(
        {"target_host": target_host, "port": port, "targets": targets}
    )
    return {"status": "COMPLETED", "vulnerabilities": [], "targets": targets}


@activity.defn(name="run_crew_pentest")
async def mock_run_crew_pentest(payload: dict) -> dict:
    CREWAI_REQUESTS.append(payload)
    return {
        "status": "COMPLETED",
        "summary": "CrewAI mock completed",
        "findings": [{"title": "SQLi confirmed", "severity": "HIGH"}],
        "agent_trace": {"planner": "plan", "guider": "guide", "executor": "exec"},
        "final_report_markdown": "# CrewAI Pentest Report\n\n- SQLi confirmed",
    }


@activity.defn(name="update_scan_crew_report")
async def mock_update_scan_crew_report(
    scan_id: str, crew_report_json: str, crew_report_markdown: str
) -> str:
    CREWAI_REPORT_UPDATES.append(
        {
            "scan_id": scan_id,
            "crew_report_json": crew_report_json,
            "crew_report_markdown": crew_report_markdown,
        }
    )
    return f"Successfully updated CrewAI report for scan {scan_id}"


@activity.defn(name="check_task_queue_pollers")
async def mock_check_task_queue_pollers(task_queue: str) -> bool:
    TASK_QUEUE_POLLER_CHECKS.append(task_queue)
    return True


@activity.defn(name="check_task_queue_pollers")
async def mock_check_task_queue_pollers_unavailable(task_queue: str) -> bool:
    TASK_QUEUE_POLLER_CHECKS.append(task_queue)
    return False


@activity.defn(name="run_crew_pentest")
async def mock_run_crew_pentest_with_markdown(payload: dict) -> dict:
    CREWAI_REQUESTS.append(payload)
    return {
        "status": "COMPLETED",
        "summary": "CrewAI mock completed",
        "final_report_markdown": "# CrewAI Evidence\n\n- SQLi confirmed by agent trace",
    }


@activity.defn(name="run_crew_pentest")
async def mock_run_crew_pentest_failed(payload: dict) -> dict:
    CREWAI_REQUESTS.append(payload)
    return {
        "status": "FAILED",
        "summary": "CrewAI mock failed",
        "error": "LLM provider unavailable",
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
                mock_update_scan_crew_report,
                mock_generate_and_store_pdf_report,
                mock_seed_target_databases,
                mock_download_minio_artifact,
                mock_run_pentest,
            ],
        ):
            async with Worker(
                env.client,
                task_queue="DEPLOYER_TASK_QUEUE",
                activities=[
                    mock_create_sandbox,
                    mock_destroy_sandbox,
                    mock_seed_target_databases,
                ],
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
                mock_update_scan_crew_report,
                mock_generate_and_store_pdf_report,
                mock_seed_target_databases,
                mock_download_minio_artifact,
                mock_run_pentest,
            ],
        ):
            async with Worker(
                env.client,
                task_queue="DEPLOYER_TASK_QUEUE",
                activities=[
                    mock_create_sandbox,
                    mock_destroy_sandbox,
                    mock_seed_target_databases,
                ],
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
    CREWAI_REQUESTS.clear()
    CREWAI_REPORT_UPDATES.clear()
    TASK_QUEUE_POLLER_CHECKS.clear()
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="TEST_QUEUE_GRAPH",
            workflows=[GraphDrivenPentestWorkflow],
            activities=[
                mock_update_scan_status,
                mock_check_task_queue_pollers,
                mock_update_scan_crew_report,
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
                activities=[
                    mock_create_sandbox,
                    mock_destroy_sandbox,
                    mock_seed_target_databases,
                ],
            ):
                async with Worker(
                    env.client,
                    task_queue="PENTEST_TASK_QUEUE",
                    activities=[mock_run_targeted_pentest],
                ):
                    async with Worker(
                        env.client,
                        task_queue="CREWAI_TASK_QUEUE",
                        activities=[mock_run_crew_pentest],
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
                        assert CREWAI_REQUESTS[-1]["scan_id"] == scan_id
                        assert CREWAI_REQUESTS[-1]["constraints"] == {
                            "mode": "non_destructive",
                            "allow_patch_apply": False,
                            "allow_pr_create": False,
                        }
                        assert TASK_QUEUE_POLLER_CHECKS[-1] == "CREWAI_TASK_QUEUE"
                        assert CREWAI_REPORT_UPDATES[-1]["scan_id"] == scan_id
                        assert (
                            '"status":"COMPLETED"'
                            in CREWAI_REPORT_UPDATES[-1]["crew_report_json"]
                        )
                        assert CREWAI_REPORT_UPDATES[-1][
                            "crew_report_markdown"
                        ].startswith("# CrewAI Pentest Report")


@pytest.mark.asyncio
async def test_graph_driven_pentest_workflow_skips_crewai_when_queue_has_no_pollers():
    CREWAI_REQUESTS.clear()
    CREWAI_REPORT_UPDATES.clear()
    TASK_QUEUE_POLLER_CHECKS.clear()
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="TEST_QUEUE_GRAPH_NO_CREW",
            workflows=[GraphDrivenPentestWorkflow],
            activities=[
                mock_update_scan_status,
                mock_check_task_queue_pollers_unavailable,
                mock_update_scan_crew_report,
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
                activities=[
                    mock_create_sandbox,
                    mock_destroy_sandbox,
                    mock_seed_target_databases,
                ],
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
                        id=f"test-graph-pentest-no-crew-{scan_id}",
                        task_queue="TEST_QUEUE_GRAPH_NO_CREW",
                    )

    assert (
        f"Graph-driven scan {scan_id} on target nginx:latest successfully completed"
        in result
    )
    assert TASK_QUEUE_POLLER_CHECKS[-1] == "CREWAI_TASK_QUEUE"
    assert CREWAI_REQUESTS == []
    assert CREWAI_REPORT_UPDATES[-1]["scan_id"] == scan_id
    assert '"status":"FAILED"' in CREWAI_REPORT_UPDATES[-1]["crew_report_json"]
    assert CREWAI_REPORT_UPDATES[-1]["crew_report_markdown"] == ""


@pytest.mark.asyncio
async def test_graph_driven_pentest_workflow_continues_when_crewai_returns_failed():
    CREWAI_REQUESTS.clear()
    CREWAI_REPORT_UPDATES.clear()
    TASK_QUEUE_POLLER_CHECKS.clear()
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="TEST_QUEUE_GRAPH_CREW_FAILED",
            workflows=[GraphDrivenPentestWorkflow],
            activities=[
                mock_update_scan_status,
                mock_check_task_queue_pollers,
                mock_update_scan_crew_report,
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
                activities=[
                    mock_create_sandbox,
                    mock_destroy_sandbox,
                    mock_seed_target_databases,
                ],
            ):
                async with Worker(
                    env.client,
                    task_queue="PENTEST_TASK_QUEUE",
                    activities=[mock_run_targeted_pentest],
                ):
                    async with Worker(
                        env.client,
                        task_queue="CREWAI_TASK_QUEUE",
                        activities=[mock_run_crew_pentest_failed],
                    ):
                        scan_id = str(uuid.uuid4())
                        result = await env.client.execute_workflow(
                            GraphDrivenPentestWorkflow.run,
                            args=[scan_id, "nginx:latest", "company-1"],
                            id=f"test-graph-pentest-crew-failed-{scan_id}",
                            task_queue="TEST_QUEUE_GRAPH_CREW_FAILED",
                        )

    assert (
        f"Graph-driven scan {scan_id} on target nginx:latest successfully completed"
        in result
    )
    assert CREWAI_REQUESTS[-1]["scan_id"] == scan_id
    assert CREWAI_REPORT_UPDATES[-1]["scan_id"] == scan_id
    assert '"status":"FAILED"' in CREWAI_REPORT_UPDATES[-1]["crew_report_json"]
    assert "LLM provider unavailable" in CREWAI_REPORT_UPDATES[-1]["crew_report_json"]
    assert CREWAI_REPORT_UPDATES[-1]["crew_report_markdown"] == ""


def test_graph_driven_workflow_extracts_crewai_markdown_for_report_generation():
    crew_report = {
        "status": "COMPLETED",
        "summary": "CrewAI mock completed",
        "final_report_markdown": "# CrewAI Evidence\n\n- SQLi confirmed by agent trace",
    }

    assert (
        GraphDrivenPentestWorkflow._extract_crew_report_markdown(crew_report)
        == "# CrewAI Evidence\n\n- SQLi confirmed by agent trace"
    )


@pytest.mark.asyncio
async def test_graph_workflow_pentests_deployer_endpoint_not_graph_host():
    TARGETED_PENTEST_CALLS.clear()
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="TEST_GRAPH_ENDPOINT_AUTHORITY",
            workflows=[GraphDrivenPentestWorkflow],
            activities=[
                mock_update_scan_status,
                mock_identify_attack_targets_with_external_url,
                mock_build_sandbox_topology,
                mock_save_vulnerabilities,
                mock_update_scan_crew_report,
                mock_generate_and_store_pdf_report,
                mock_seed_target_databases,
            ],
        ):
            async with Worker(
                env.client,
                task_queue="DEPLOYER_TASK_QUEUE",
                activities=[
                    mock_create_sandbox,
                    mock_destroy_sandbox,
                    mock_seed_target_databases,
                ],
            ):
                async with Worker(
                    env.client,
                    task_queue="PENTEST_TASK_QUEUE",
                    activities=[mock_capture_run_targeted_pentest],
                ):
                    async with Worker(
                        env.client,
                        task_queue="CREWAI_TASK_QUEUE",
                        activities=[mock_run_crew_pentest],
                    ):
                        scan_id = str(uuid.uuid4())
                        await env.client.execute_workflow(
                            GraphDrivenPentestWorkflow.run,
                            args=[
                                scan_id,
                                "topology:target-admin",
                                "company-1",
                                "agent-1",
                            ],
                            id=f"test-graph-endpoint-authority-{scan_id}",
                            task_queue="TEST_GRAPH_ENDPOINT_AUTHORITY",
                        )

    assert TARGETED_PENTEST_CALLS == [
        {
            "target_host": f"svc-{scan_id}.aegis-war-room-{scan_id}.svc.cluster.local",
            "port": 80,
            "targets": TARGETED_PENTEST_CALLS[0]["targets"],
        }
    ]
    assert (
        TARGETED_PENTEST_CALLS[0]["targets"][0]["path"]
        == "http://source.example.test/admin?debug=true"
    )


def test_graph_driven_workflow_builds_crewai_activity_payload():
    payload = GraphDrivenPentestWorkflow._build_crew_pentest_request(
        scan_id="scan-1",
        sandbox_host="aegis-target.aegis-war-room-scan-1.svc.cluster.local",
        sandbox_port=8080,
        attack_targets=[
            {
                "path": "/search",
                "label": "default-search",
                "target_name": "aegis-target",
                "criticality": 5,
                "score": 9,
            }
        ],
        sandbox_request={
            "preferred_endpoint_workload": "aegis-target",
            "topology": {
                "containers": [{"name": "aegis-target", "image": "python:3.12-alpine"}]
            },
        },
        pentest_report={"status": "COMPLETED", "target_count": 1},
        seed_contract={"seed_flag": "aegis-flag-1234", "seeded_count": 0},
    )

    assert payload == {
        "scan_id": "scan-1",
        "sandbox_endpoint": {
            "host": "aegis-target.aegis-war-room-scan-1.svc.cluster.local",
            "port": 8080,
            "scheme": "http",
        },
        "targets": [
            {
                "path": "/search",
                "label": "default-search",
                "target_name": "aegis-target",
                "criticality": 5,
                "score": 9,
            }
        ],
        "topology_summary": {
            "preferred_endpoint_workload": "aegis-target",
            "container_count": 1,
            "pentest_status": "COMPLETED",
            "pentest_target_count": 1,
        },
        "seed_contract": {"seed_flag": "aegis-flag-1234", "seeded_count": 0},
        "pentest_report": {"status": "COMPLETED", "target_count": 1},
        "constraints": {
            "mode": "non_destructive",
            "allow_patch_apply": False,
            "allow_pr_create": False,
        },
    }


def test_graph_driven_workflow_builds_failed_crew_report_from_error():
    report = GraphDrivenPentestWorkflow._build_failed_crew_report(
        ApplicationError("ollama unreachable"),
    )

    assert report == {
        "status": "FAILED",
        "summary": "CrewAI pentest failed.",
        "error": "ollama unreachable",
    }


def test_graph_driven_workflow_crewai_schedule_to_start_timeout_is_short():
    assert GraphDrivenPentestWorkflow.CREWAI_SCHEDULE_TO_START_TIMEOUT == 30


@pytest.mark.asyncio
async def test_graph_driven_workflow_downloads_minio_artifact_before_deploying():
    CREATED_SANDBOX_REQUESTS.clear()
    CREWAI_REQUESTS.clear()
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="TEST_QUEUE_GRAPH_MINIO",
            workflows=[GraphDrivenPentestWorkflow],
            activities=[
                mock_update_scan_status,
                mock_save_vulnerabilities,
                mock_update_scan_crew_report,
                mock_generate_and_store_pdf_report,
                mock_seed_target_databases,
                mock_download_minio_artifact,
                mock_identify_attack_targets,
                mock_build_sandbox_topology,
                mock_check_task_queue_pollers,
            ],
        ):
            async with Worker(
                env.client,
                task_queue="DEPLOYER_TASK_QUEUE",
                activities=[
                    mock_create_sandbox,
                    mock_destroy_sandbox,
                    mock_seed_target_databases,
                ],
            ):
                async with Worker(
                    env.client,
                    task_queue="PENTEST_TASK_QUEUE",
                    activities=[mock_run_targeted_pentest],
                ):
                    async with Worker(
                        env.client,
                        task_queue="CREWAI_TASK_QUEUE",
                        activities=[mock_run_crew_pentest],
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
    assert (
        CREWAI_REQUESTS[-1]["topology_summary"]["preferred_endpoint_workload"] == "web"
    )
    assert CREWAI_REQUESTS[-1]["pentest_report"]["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_pentest_workflow_rejects_invalid_topology_before_create_sandbox():
    CREATED_SANDBOX_REQUESTS.clear()
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="TEST_QUEUE_INVALID_TOPOLOGY",
            workflows=[PentestWorkflow],
            activities=[
                mock_update_scan_status,
                mock_save_vulnerabilities,
                mock_generate_and_store_pdf_report,
                mock_seed_target_databases,
                mock_download_invalid_topology_artifact,
                mock_run_pentest,
            ],
        ):
            async with Worker(
                env.client,
                task_queue="DEPLOYER_TASK_QUEUE",
                activities=[
                    mock_create_sandbox,
                    mock_destroy_sandbox,
                    mock_seed_target_databases,
                ],
            ):
                scan_id = str(uuid.uuid4())
                with pytest.raises(Exception) as exc_info:
                    await env.client.execute_workflow(
                        PentestWorkflow.run,
                        args=[
                            scan_id,
                            "minio://aegis-ingest/targets/invalid-sandbox.json",
                        ],
                        id=f"test-invalid-topology-{scan_id}",
                        task_queue="TEST_QUEUE_INVALID_TOPOLOGY",
                    )

    assert "Invalid sandbox topology" in str(exc_info.value.__cause__)
    assert CREATED_SANDBOX_REQUESTS == []


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
