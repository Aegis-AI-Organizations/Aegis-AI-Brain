import asyncio
import logging
import grpc

# These will be available after generation
import aegis.v1.ping_pb2 as ping_pb2
import aegis.v1.ping_pb2_grpc as ping_pb2_grpc
import aegis.v1.scan_pb2 as scan_pb2
import aegis.v1.scan_pb2_grpc as scan_pb2_grpc
import aegis.v1.vulnerability_pb2 as vulnerability_pb2
import aegis.v1.vulnerability_pb2_grpc as vulnerability_pb2_grpc

logger = logging.getLogger("aegis_brain_grpc")


class PingService(ping_pb2_grpc.PingServiceServicer):
    async def Ping(self, request, context):
        return ping_pb2.PingResponse(message="pong")


class ScanService(scan_pb2_grpc.ScanServiceServicer):
    async def StartScan(self, request, context):
        logger.info(f"Received StartScan request for image: {request.target_image}")
        return scan_pb2.StartScanResponse(scan_id="proto-scan-id", status="PENDING")

    async def GetScanStatus(self, request, context):
        logger.info(f"Received GetScanStatus request for ID: {request.scan_id}")
        return scan_pb2.GetScanStatusResponse(
            scan_id=request.scan_id, status="COMPLETED"
        )


class VulnerabilityService(vulnerability_pb2_grpc.VulnerabilityServiceServicer):
    async def GetVulnerabilities(self, request, context):
        logger.info(f"Received GetVulnerabilities request for scan: {request.scan_id}")
        return vulnerability_pb2.GetVulnerabilitiesResponse(vulnerabilities=[])


async def serve(port: str = "50051"):
    server = grpc.aio.server()

    ping_pb2_grpc.add_PingServiceServicer_to_server(PingService(), server)
    scan_pb2_grpc.add_ScanServiceServicer_to_server(ScanService(), server)
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
    asyncio.run(serve())
