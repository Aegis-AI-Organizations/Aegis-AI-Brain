import logging
import aegis.v2.topology_pb2 as topology_pb2
import aegis.v2.topology_pb2_grpc as topology_pb2_grpc
from .utils import with_identity

logger = logging.getLogger("aegis_brain_grpc")

class TopologyService(topology_pb2_grpc.TopologyServiceServicer):
    """
    TopologyService handles incoming infrastructure data from Agents.
    This data is used to reconstruct the client's infrastructure in the SaaS.
    """

    @with_identity
    async def ReportTopology(self, request, context, identity):
        company_id = identity.get("company_id")
        
        # Log the received topology for now
        host_count = len(request.topology.hosts)
        container_count = sum(len(h.containers) for h in request.topology.hosts)
        
        logger.info(
            f"Received topology report from Company {company_id}: "
            f"{host_count} hosts, {container_count} containers."
        )

        # TODO: Store topology in database for infrastructure reconstruction
        # This will be used by the AI simulation engine.

        return topology_pb2.ReportTopologyResponse(success=True)
