import os
from unittest.mock import patch, MagicMock
from config.db import get_db_connection


class TestDatabaseConnection:
    @patch("config.db.psycopg.connect")
    @patch.dict(os.environ, {"POSTGRES_PASSWORD": "dummy"}, clear=True)
    def test_get_db_connection_success(self, mock_connect):
        """Test returning a database connection on success."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        conn = get_db_connection()

        assert conn is mock_conn
        mock_connect.assert_called_once()

    @patch("config.db.psycopg.connect")
    @patch.dict(os.environ, {"POSTGRES_PASSWORD": "dummy"}, clear=True)
    def test_get_db_connection_failure(self, mock_connect):
        """Test returning None when database connection fails."""
        mock_connect.side_effect = Exception("Connection Failed")

        conn = get_db_connection()

        assert conn is None
        mock_connect.assert_called_once()
