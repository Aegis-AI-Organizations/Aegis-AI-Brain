from temporalio import activity

from services.neo4j_sandbox_topology import (
    build_sandbox_topology as query_sandbox_topology,
)


@activity.defn
async def build_sandbox_topology(
    company_id: str, target_ids: list[str] | None = None
) -> dict:
    return query_sandbox_topology(company_id=company_id, target_ids=target_ids)
