import asyncio
import logging
import grpc

import aegis.v2.ping_pb2_grpc as ping_pb2_grpc
import aegis.v2.scan_pb2_grpc as scan_pb2_grpc
import aegis.v2.vulnerability_pb2_grpc as vulnerability_pb2_grpc

from grpc_services.ping import PingService
from grpc_services.scans import ScanService
from grpc_services.vulnerabilities import VulnerabilityService

logger = logging.getLogger("aegis_brain_grpc")


async def serve(port: str, temporal_client=None):
    if temporal_client is None:
        logger.warning("Starting gRPC server without Temporal Client!")

    server = grpc.aio.server()

    ping_pb2_grpc.add_PingServiceServicer_to_server(PingService(), server)
    scan_pb2_grpc.add_ScanServiceServicer_to_server(
        ScanService(temporal_client), server
    )
    vulnerability_pb2_grpc.add_VulnerabilityServiceServicer_to_server(
        VulnerabilityService(), server
    )

    listen_addr = f"[::]:{port}"
    server.add_insecure_port(listen_addr)
    logger.info(f"📡 gRPC server starting on {listen_addr}")
    await server.start()
    await server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Enable gRPC debug logging
    logging.getLogger("grpc").setLevel(logging.DEBUG)
    asyncio.run(serve("50051"))
