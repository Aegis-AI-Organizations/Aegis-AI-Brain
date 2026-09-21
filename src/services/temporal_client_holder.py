from temporalio.client import Client


_client: Client | None = None


def set_temporal_client(client: Client) -> None:
    global _client
    _client = client


def get_temporal_client() -> Client:
    if _client is None:
        raise RuntimeError("Temporal client is not initialized")
    return _client
