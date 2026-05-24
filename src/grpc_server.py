import asyncio
import logging
import grpc

import aegis.v2.auth_pb2_grpc as auth_pb2_grpc
import aegis.v2.ping_pb2_grpc as ping_pb2_grpc
import aegis.v2.scan_pb2_grpc as scan_pb2_grpc
import aegis.v2.vulnerability_pb2_grpc as vulnerability_pb2_grpc
import aegis.v2.company_pb2_grpc as company_pb2_grpc
import aegis.v2.billing_pb2_grpc as billing_pb2_grpc
import aegis.v2.agent_pb2_grpc as agent_pb2_grpc
import aegis.v2.internal_auth_pb2_grpc as internal_auth_pb2_grpc

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
from grpc_services.company import CompanyService
from grpc_services.billing import BillingService
from grpc_services.agent import AgentService
from grpc_services.internal_auth import InternalAuthService
from grpc_services.interceptors import AuthInterceptor

logger = logging.getLogger("aegis_brain_grpc")


async def serve(port: str, temporal_client=None):
    if temporal_client is None:
        logger.warning("Starting gRPC server without Temporal Client!")

    server = grpc.aio.server(
        interceptors=[AuthInterceptor()],
        options=[
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),
            ("grpc.max_send_message_length", 50 * 1024 * 1024),
            ("grpc.keepalive_time_ms", 60000),
            ("grpc.keepalive_timeout_ms", 20000),
            ("grpc.keepalive_permit_without_calls", True),
            ("grpc.http2.max_pings_without_data", 0),
            ("grpc.http2.min_recv_ping_interval_without_data_ms", 10000),
        ],
    )

    ping_pb2_grpc.add_PingServiceServicer_to_server(PingService(), server)
    auth_pb2_grpc.add_AuthServiceServicer_to_server(AuthService(), server)
    scan_pb2_grpc.add_ScanServiceServicer_to_server(
        ScanService(temporal_client), server
    )
    vulnerability_pb2_grpc.add_VulnerabilityServiceServicer_to_server(
        VulnerabilityService(), server
    )
    company_pb2_grpc.add_CompanyServiceServicer_to_server(CompanyService(), server)
    billing_pb2_grpc.add_BillingServiceServicer_to_server(BillingService(), server)
    agent_pb2_grpc.add_AgentServiceServicer_to_server(AgentService(temporal_client), server)
    internal_auth_pb2_grpc.add_InternalAuthServiceServicer_to_server(
        InternalAuthService(), server
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
                raise RuntimeError(
                    "mTLS is enabled but certificates could not be loaded"
                ) from e
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
