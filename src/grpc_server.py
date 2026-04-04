import asyncio
import logging
import grpc

import aegis.v2.auth_pb2_grpc as auth_pb2_grpc
import aegis.v2.ping_pb2_grpc as ping_pb2_grpc
import aegis.v2.scan_pb2_grpc as scan_pb2_grpc
import aegis.v2.vulnerability_pb2_grpc as vulnerability_pb2_grpc

from config.config import (
    GRPC_PORT,
    TLS_ENABLE,
    TLS_CA_CERT,
    TLS_SERVER_CERT,
    TLS_SERVER_KEY,
)
from grpc_services.auth import AuthService
from grpc_services.ping import PingService
from grpc_services.scans import ScanService
from grpc_services.vulnerabilities import VulnerabilityService
from grpc_services.interceptors import AuthInterceptor

logger = logging.getLogger("aegis_brain_grpc")


async def serve(port: str, temporal_client=None):
    if temporal_client is None:
        logger.warning("Starting gRPC server without Temporal Client!")

    server = grpc.aio.server(interceptors=[AuthInterceptor()])

    ping_pb2_grpc.add_PingServiceServicer_to_server(PingService(), server)
    auth_pb2_grpc.add_AuthServiceServicer_to_server(AuthService(), server)
    scan_pb2_grpc.add_ScanServiceServicer_to_server(
        ScanService(temporal_client), server
    )
    vulnerability_pb2_grpc.add_VulnerabilityServiceServicer_to_server(
        VulnerabilityService(), server
    )

    listen_addr = f"0.0.0.0:{port}"
    try:
        if TLS_ENABLE:
            logger.info("🔐 Enabling mTLS for gRPC server")
            try:
                with open(TLS_CA_CERT, "rb") as f:
                    ca_cert = f.read()
                with open(TLS_SERVER_CERT, "rb") as f:
                    server_cert = f.read()
                with open(TLS_SERVER_KEY, "rb") as f:
                    server_key = f.read()

                server_credentials = grpc.ssl_server_credentials(
                    [(server_key, server_cert)],
                    root_certificates=ca_cert,
                    require_client_auth=True,
                )
                server.add_secure_port(listen_addr, server_credentials)
            except Exception as e:
                logger.error(f"❌ Failed to load gRPC TLS certificates: {e}")
                logger.warning("⚠️ Falling back to insecure port due to TLS failure")
                server.add_insecure_port(listen_addr)
        else:
            server.add_insecure_port(listen_addr)

        logger.info(f"📡 gRPC server starting on {listen_addr}")
        await server.start()
        await server.wait_for_termination()
    except Exception as e:
        logger.error(f"❌ gRPC server failed: {e}")
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("grpc").setLevel(logging.DEBUG)
    asyncio.run(serve(GRPC_PORT))
