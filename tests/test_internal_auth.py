from unittest.mock import MagicMock, patch

from grpc_services.internal_auth import InternalAuthService


def test_verify_token_success():
    """Valid active token returns the associated company_id."""
    service = InternalAuthService()
    mock_conn = MagicMock()
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchone.return_value = ("company-abc",)

    with patch("grpc_services.internal_auth.get_db_connection", return_value=mock_conn):
        result = service._verify_token_db_sync("ag_valid_token")

    assert result == "company-abc"
    mock_conn.close.assert_called_once()


def test_verify_token_not_found():
    """Unknown or inactive token returns None."""
    service = InternalAuthService()
    mock_conn = MagicMock()
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchone.return_value = None

    with patch("grpc_services.internal_auth.get_db_connection", return_value=mock_conn):
        result = service._verify_token_db_sync("ag_unknown_token")

    assert result is None
    mock_conn.close.assert_called_once()


def test_verify_token_db_exception():
    """DB error returns None gracefully (does not raise)."""
    service = InternalAuthService()

    with patch(
        "grpc_services.internal_auth.get_db_connection",
        side_effect=Exception("DB connection failed"),
    ):
        result = service._verify_token_db_sync("ag_any_token")

    assert result is None
