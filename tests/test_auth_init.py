import pytest
import os
from unittest.mock import patch
from grpc_services.auth import AuthService


def test_auth_service_init_no_db_env():
    """Verify AuthService initializes even if DB env is missing."""
    with patch.dict(os.environ, {}, clear=True):
        try:
            service = AuthService()
            assert service._session_factory is None
        except Exception as e:
            pytest.fail(f"AuthService failed to initialize without DB env: {e}")


def test_auth_service_lazy_factory():
    """Verify session_factory is only created on first access."""
    service = AuthService()
    assert service._session_factory is None

    with patch("grpc_services.auth.get_session_factory") as mock_get_factory:
        mock_get_factory.return_value = "mock_factory"
        factory = service.session_factory
        assert factory == "mock_factory"
        assert service._session_factory == "mock_factory"
        mock_get_factory.assert_called_once()
