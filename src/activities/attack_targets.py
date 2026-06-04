from temporalio import activity

from services.neo4j_attack_targets import (
    identify_attack_targets as query_attack_targets,
)


@activity.defn
async def identify_attack_targets(
    company_id: str, agent_id: str | None = None
) -> list[dict]:
    return query_attack_targets(company_id=company_id, agent_id=agent_id)
