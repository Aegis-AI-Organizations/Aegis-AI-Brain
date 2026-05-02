import pytest
from unittest.mock import patch, MagicMock
from config.db import get_db_connection


class TestDatabaseConnection:
    @patch("config.db.psycopg.connect")
    @patch("config.db.DB_PASSWORD", "dummy")
    def test_get_db_connection_success(self, mock_connect):
        """Test returning a database connection on success."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        conn = get_db_connection()

        assert conn is mock_conn
        mock_connect.assert_called_once()

    @patch("config.db.psycopg.connect")
    @patch("config.db.DB_PASSWORD", "dummy")
    def test_get_db_connection_failure(self, mock_connect):
        """Test raising ConnectionError when database connection fails."""
        mock_connect.side_effect = Exception("Connection Failed")

        with pytest.raises(ConnectionError, match="Database connection failed"):
            get_db_connection()

        mock_connect.assert_called_once()
