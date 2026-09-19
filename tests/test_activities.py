import pytest
from unittest.mock import patch, MagicMock
from temporalio.testing import ActivityEnvironment
from activities.db_activities import (
    update_scan_status,
    update_scan_debug_bundle,
    save_vulnerabilities,
    generate_and_store_pdf_report,
)


def test_build_sandbox_topology_includes_database_schemas(monkeypatch):
    from services.neo4j_sandbox_topology import Neo4jSandboxTopologyService

    service = Neo4jSandboxTopologyService(
        url="http://neo4j", user="neo4j", password="pw"
    )
    calls = []

    def fake_execute_query(cypher, parameters):
        calls.append(cypher)
        if "MATCH (c:Container)" in cypher:
            return [
                [
                    "company-1:agent-1:web",
                    "portfolio-web",
                    "portfolio-web:local",
                    ["DB_HOST=portfolio-db"],
                    [],
                    ["portfolio-net"],
                    ["8080:tcp:LISTEN::18080:docker"],
                    [],
                    "minio:archives/portfolio-web.tar",
                    "archives/portfolio-web.tar",
                ]
            ]
        if "MATCH (r:Route)" in cypher:
            return []
        if "MATCH (d:DatabaseSchema)" in cypher:
            return [
                [
                    "postgres",
                    "portfolio-db",
                    5432,
                    "portfolio",
                    "portfolio",
                    "company-1:agent-1:web",
                    "portfolio-web",
                ]
            ]
        raise AssertionError(cypher)

    monkeypatch.setattr(service, "_execute_query", fake_execute_query)

    topology = service.build_sandbox_topology("company-1", [])

    assert (
        topology["containers"][0]["image_archive_ref"]
        == "minio:archives/portfolio-web.tar"
    )
    assert topology["databaseSchemas"] == [
        {
            "engine": "postgres",
            "host": "portfolio-db",
            "port": 5432,
            "databaseName": "portfolio",
            "username": "portfolio",
            "sourceContainerId": "company-1:agent-1:web",
            "sourceContainerName": "portfolio-web",
        }
    ]


@pytest.mark.asyncio
async def test_update_scan_status_success():
    """Test updating the status of a scan successfully."""
    mock_conn = MagicMock()
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.rowcount = 1

    with patch("activities.db_activities.get_db_connection", return_value=mock_conn):
        activity_env = ActivityEnvironment()
        result = await activity_env.run(
            update_scan_status, "test-scan-123", "COMPLETED"
        )

        assert "Successfully updated scan test-scan-123 to status COMPLETED" in result
        mock_cursor.execute.assert_called_once()
        sql_query, query_params = mock_cursor.execute.call_args[0]
        assert "completed_at = CURRENT_TIMESTAMP" in sql_query
        assert query_params == ("COMPLETED", "test-scan-123")
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


@pytest.mark.asyncio
async def test_update_scan_status_keeps_intermediate_completed_at_unchanged():
    """Test intermediate status updates do not set completed_at."""
    mock_conn = MagicMock()
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.rowcount = 1

    with patch("activities.db_activities.get_db_connection", return_value=mock_conn):
        activity_env = ActivityEnvironment()
        await activity_env.run(update_scan_status, "test-scan-123", "ATTACKING")

        sql_query, query_params = mock_cursor.execute.call_args[0]
        assert "completed_at" not in sql_query
        assert query_params == ("ATTACKING", "test-scan-123")


@pytest.mark.asyncio
async def test_update_scan_status_not_found():
    """Test activity throwing exception when rowcount is 0."""
    mock_conn = MagicMock()
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.rowcount = 0

    with patch("activities.db_activities.get_db_connection", return_value=mock_conn):
        activity_env = ActivityEnvironment()
        with pytest.raises(
            Exception, match="Scan ID test-scan-123 not found to update"
        ):
            await activity_env.run(update_scan_status, "test-scan-123", "IN_PROGRESS")
        mock_conn.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_update_scan_status_db_fail():
    """Test activity throwing exception when DB is down."""
    with patch("activities.db_activities.get_db_connection", return_value=None):
        activity_env = ActivityEnvironment()
        with pytest.raises(Exception, match="Database connection failed"):
            await activity_env.run(update_scan_status, "test-scan-123", "FAILED")


@pytest.mark.asyncio
async def test_update_scan_debug_bundle_success():
    """Test storing a sandbox debug bundle reference."""
    mock_conn = MagicMock()
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.rowcount = 1

    with patch("activities.db_activities.get_db_connection", return_value=mock_conn):
        activity_env = ActivityEnvironment()
        result = await activity_env.run(
            update_scan_debug_bundle,
            "scan-123",
            "s3://aegis-debug/debug-bundles/scan-123/bundle.tar.gz",
        )

        assert "Successfully updated scan scan-123 debug bundle" in result
        mock_cursor.execute.assert_called_once_with(
            "UPDATE scans SET debug_bundle = %s WHERE id = %s",
            ("s3://aegis-debug/debug-bundles/scan-123/bundle.tar.gz", "scan-123"),
        )
        mock_conn.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_scan_debug_bundle_skips_empty_reference():
    """Test empty debug bundle references do not touch the database."""
    with patch("activities.db_activities.get_db_connection") as mock_get_conn:
        activity_env = ActivityEnvironment()
        result = await activity_env.run(update_scan_debug_bundle, "scan-123", "")

        assert "No debug bundle reference to update for scan scan-123" in result
        mock_get_conn.assert_not_called()


@pytest.mark.asyncio
async def test_save_vulnerabilities_success():
    """Test saving vulnerabilities and their evidences."""
    mock_conn = MagicMock()
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchone.return_value = ["mock-vuln-uuid-1234"]

    vulnerabilities = [
        {
            "vuln_type": "XSS",
            "severity": "HIGH",
            "target_endpoint": "http://target/reflect",
            "description": "Found XSS",
            "evidences": [
                {"payload_used": "<script>", "loot_data": {"reflected": True}}
            ],
        }
    ]

    with patch("activities.db_activities.get_db_connection", return_value=mock_conn):
        from activities.db_activities import save_vulnerabilities

        activity_env = ActivityEnvironment()
        result = await activity_env.run(
            save_vulnerabilities, "scan-123", vulnerabilities
        )

        assert "Successfully saved 1 vulnerabilities for scan scan-123" in result
        assert mock_cursor.execute.call_count == 2
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


@pytest.mark.asyncio
async def test_save_vulnerabilities_deduplicates_findings_and_evidences():
    """Duplicate findings/evidences in a single run are stored once."""
    mock_conn = MagicMock()
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchone.return_value = ["mock-vuln-uuid-1234"]

    duplicate_vulnerability = {
        "vuln_type": "SQLi",
        "severity": "HIGH",
        "target_endpoint": "http://target/search",
        "description": "Boolean SQL injection",
        "evidences": [
            {"payload_used": "' OR 1=1 --", "loot_data": {"matched": True}},
            {"payload_used": "' OR 1=1 --", "loot_data": {"matched": True}},
        ],
    }

    with patch("activities.db_activities.get_db_connection", return_value=mock_conn):
        activity_env = ActivityEnvironment()
        result = await activity_env.run(
            save_vulnerabilities,
            "scan-123",
            [duplicate_vulnerability, dict(duplicate_vulnerability)],
        )

    assert "Successfully saved 1 vulnerabilities for scan scan-123" in result
    assert mock_cursor.execute.call_count == 2
    vulnerability_insert = mock_cursor.execute.call_args_list[0].args
    evidence_insert = mock_cursor.execute.call_args_list[1].args
    assert "INSERT INTO vulnerabilities" in vulnerability_insert[0]
    assert "INSERT INTO evidences" in evidence_insert[0]


@pytest.mark.asyncio
async def test_save_vulnerabilities_empty():
    """Test saving empty vulnerabilities list."""
    with patch("activities.db_activities.get_db_connection") as mock_get_conn:
        from activities.db_activities import save_vulnerabilities

        activity_env = ActivityEnvironment()
        result = await activity_env.run(save_vulnerabilities, "scan-123", [])

        assert "No vulnerabilities to save for scan scan-123" in result
        mock_get_conn.assert_not_called()


@pytest.mark.asyncio
async def test_generate_and_store_pdf_report_success():
    """Test generating and storing a PDF report successfully."""
    mock_conn = MagicMock()
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.rowcount = 1

    vulnerabilities = [
        {
            "vuln_type": "SQLi",
            "severity": "CRITICAL",
            "target_endpoint": "http://target/login",
            "description": "Union based SQL injection",
            "evidences": [{"payload_used": "' OR 1=1 --", "loot_data": {"ok": True}}],
        }
    ]

    with patch("activities.db_activities.get_db_connection", return_value=mock_conn):
        activity_env = ActivityEnvironment()
        result = await activity_env.run(
            generate_and_store_pdf_report, "scan-123", vulnerabilities
        )

        assert (
            "Successfully generated and stored PDF report for scan scan-123" in result
        )
        mock_cursor.execute.assert_called_once()
        sql_query, query_params = mock_cursor.execute.call_args[0]
        assert "UPDATE scans SET report_pdf = %s WHERE id = %s" in sql_query
        assert query_params[1] == "scan-123"
        assert isinstance(query_params[0], bytes)
        assert query_params[0].startswith(b"%PDF")
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


@pytest.mark.asyncio
async def test_generate_and_store_pdf_report_passes_crew_markdown_to_report_engine():
    mock_conn = MagicMock()
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.rowcount = 1

    with (
        patch("activities.db_activities.get_db_connection", return_value=mock_conn),
        patch("activities.db_activities.build_report", return_value=b"%PDF crew") as mock_build_report,
    ):
        activity_env = ActivityEnvironment()
        await activity_env.run(
            generate_and_store_pdf_report,
            "scan-123",
            [],
            "# CrewAI Evidence\n\n- SQLi confirmed by agent trace",
        )

    mock_build_report.assert_called_once_with(
        "scan-123",
        [],
        crew_report_markdown="# CrewAI Evidence\n\n- SQLi confirmed by agent trace",
    )


@pytest.mark.asyncio
async def test_generate_and_store_pdf_report_not_found():
    """Test exception when storing PDF for a missing scan."""
    mock_conn = MagicMock()
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.rowcount = 0

    with patch("activities.db_activities.get_db_connection", return_value=mock_conn):
        activity_env = ActivityEnvironment()
        with pytest.raises(
            Exception, match="Scan ID scan-123 not found to store PDF report"
        ):
            await activity_env.run(generate_and_store_pdf_report, "scan-123", [])
        mock_conn.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_generate_and_store_pdf_report_db_fail():
    """Test PDF report activity when DB connection cannot be established."""
    with patch("activities.db_activities.get_db_connection", return_value=None):
        activity_env = ActivityEnvironment()
        with pytest.raises(Exception, match="Database connection failed"):
            await activity_env.run(generate_and_store_pdf_report, "scan-123", [])
