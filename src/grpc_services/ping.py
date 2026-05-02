import aegis.v2.ping_pb2 as ping_pb2
import aegis.v2.ping_pb2_grpc as ping_pb2_grpc


class PingService(ping_pb2_grpc.PingServiceServicer):
    async def Ping(self, request, context):
        return ping_pb2.PingResponse(message="pong")
