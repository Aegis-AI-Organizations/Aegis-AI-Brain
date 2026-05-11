from unittest.mock import MagicMock, patch

from grpc_services.internal_auth import InternalAuthService
from utils.token_utils import hash_token

VALID_AGENT_TOKEN = "ag_0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefg"


def test_verify_token_success():
    """Valid active token returns the associated company_id."""
    service = InternalAuthService()
    mock_conn = MagicMock()
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchone.return_value = ("company-abc",)

    with patch("grpc_services.internal_auth.get_db_connection", return_value=mock_conn):
        result = service._verify_token_db_sync(VALID_AGENT_TOKEN)

    assert result == "company-abc"
    mock_cursor.execute.assert_called_once_with(
        "SELECT id FROM companies WHERE deployment_token = %s",
        (hash_token(VALID_AGENT_TOKEN),),
    )
    mock_conn.close.assert_called_once()


def test_verify_token_not_found():
    """Unknown or inactive token returns None."""
    service = InternalAuthService()
    mock_conn = MagicMock()
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchone.return_value = None

    with patch("grpc_services.internal_auth.get_db_connection", return_value=mock_conn):
        result = service._verify_token_db_sync(VALID_AGENT_TOKEN)

    assert result is None
    mock_conn.close.assert_called_once()


def test_verify_token_db_exception():
    """DB error returns None gracefully (does not raise)."""
    service = InternalAuthService()

    with patch(
        "grpc_services.internal_auth.get_db_connection",
        side_effect=Exception("DB connection failed"),
    ):
        result = service._verify_token_db_sync(VALID_AGENT_TOKEN)

    assert result is None


def test_verify_token_invalid_format_skips_database():
    """Invalid token formats fail before DB lookup."""
    service = InternalAuthService()

    with patch("grpc_services.internal_auth.get_db_connection") as mock_get_db:
        result = service._verify_token_db_sync("ag_too-short")

    assert result is None
    mock_get_db.assert_not_called()
