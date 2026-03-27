from google.protobuf.timestamp_pb2 import Timestamp


def to_pb_timestamp(dt):
    if dt is None:
        return None
    ts = Timestamp()
    ts.FromDatetime(dt)
    return ts
