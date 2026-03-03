import pytest
from unittest.mock import patch, MagicMock
from temporalio.testing import ActivityEnvironment
from activities.db_activities import update_scan_status


@pytest.mark.asyncio
async def test_update_scan_status_success():
    """Test updating the status of a scan successfully."""
    mock_conn = MagicMock()
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.rowcount = 1

    with patch("activities.db_activities.get_db_connection", return_value=mock_conn):
        activity_env = ActivityEnvironment()
        result = await activity_env.run(
            update_scan_status, ["test-scan-123", "COMPLETED"]
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
            await activity_env.run(update_scan_status, ["test-scan-123", "IN_PROGRESS"])
        mock_conn.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_update_scan_status_db_fail():
    """Test activity throwing exception when DB is down."""
    with patch("activities.db_activities.get_db_connection", return_value=None):
        activity_env = ActivityEnvironment()
        with pytest.raises(Exception, match="Database connection failed"):
            await activity_env.run(update_scan_status, ["test-scan-123", "FAILED"])
