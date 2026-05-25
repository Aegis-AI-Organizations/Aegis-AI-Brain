import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import grpc_server
from grpc_server import serve


@pytest.mark.asyncio
@patch("grpc.aio.server")
async def test_grpc_server_serve_registration(mock_server_class):
    mock_server = MagicMock()
    mock_server_class.return_value = mock_server

    # We mock start() to avoid actual listening
    mock_server.start = MagicMock()
    mock_server.wait_for_termination = MagicMock()

    # Run serve in a task and cancel it soon
    import asyncio

    task = asyncio.create_task(serve("50051", MagicMock()))
    await asyncio.sleep(0.1)
    task.cancel()

    # Just verify it tried to create a server
    assert mock_server_class.called


@pytest.mark.asyncio
@patch("grpc_server.grpc.ssl_server_credentials")
@patch("grpc.aio.server")
async def test_grpc_server_mtls_requires_client_certificate(
    mock_server_class, mock_ssl_credentials, tmp_path, monkeypatch
):
    ca_path = tmp_path / "ca.pem"
    certificate_path = tmp_path / "brain.pem"
    key_path = tmp_path / "brain.key"
    ca_path.write_bytes(b"ca")
    certificate_path.write_bytes(b"certificate")
    key_path.write_bytes(b"key")
    monkeypatch.setattr(grpc_server, "TLS_ENABLE", True)
    monkeypatch.setattr(grpc_server, "TLS_CA_CERT", str(ca_path))
    monkeypatch.setattr(grpc_server, "TLS_SERVER_CERT", str(certificate_path))
    monkeypatch.setattr(grpc_server, "TLS_SERVER_KEY", str(key_path))

    mock_server = MagicMock()
    mock_server.start = AsyncMock()
    mock_server.wait_for_termination = AsyncMock()
    mock_server_class.return_value = mock_server
    credentials = MagicMock()
    mock_ssl_credentials.return_value = credentials

    await serve("50051", MagicMock())

    mock_ssl_credentials.assert_called_once_with(
        [(b"key", b"certificate")],
        root_certificates=b"ca",
        require_client_auth=True,
    )
    mock_server.add_secure_port.assert_called_once_with("0.0.0.0:50051", credentials)


@pytest.mark.asyncio
@patch("grpc.aio.server")
async def test_grpc_server_mtls_fails_when_certificate_missing(
    mock_server_class, tmp_path, monkeypatch
):
    monkeypatch.setattr(grpc_server, "TLS_ENABLE", True)
    monkeypatch.setattr(grpc_server, "TLS_CA_CERT", str(tmp_path / "missing-ca.pem"))
    monkeypatch.setattr(
        grpc_server, "TLS_SERVER_CERT", str(tmp_path / "missing-brain.pem")
    )
    monkeypatch.setattr(
        grpc_server, "TLS_SERVER_KEY", str(tmp_path / "missing-brain.key")
    )
    mock_server_class.return_value = MagicMock()

    with pytest.raises(RuntimeError, match="certificates could not be loaded"):
        await serve("50051", MagicMock())
