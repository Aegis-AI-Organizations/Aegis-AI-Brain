import pytest
from unittest.mock import patch, MagicMock
from temporalio.testing import ActivityEnvironment
from activities.db_activities import update_scan_status, generate_and_store_pdf_report


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
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


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
