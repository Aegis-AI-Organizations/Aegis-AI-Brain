from datetime import datetime
from grpc_services.broadcaster import StatusBroadcaster
from grpc_services.utils import to_pb_timestamp


def test_broadcaster():
    b = StatusBroadcaster()
    q = b.register()
    assert q.empty()

    b.broadcast("id1", "status1")
    assert q.get_nowait() == ("id1", "status1")

    b.unregister(q)
    assert len(b.queues) == 0


def test_to_pb_timestamp():
    dt = datetime(2025, 1, 1, 12, 0, 0)
    ts = to_pb_timestamp(dt)
    assert ts.seconds > 0
    assert to_pb_timestamp(None) is None
