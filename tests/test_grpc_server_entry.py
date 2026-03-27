import pytest
from unittest.mock import MagicMock, patch
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
