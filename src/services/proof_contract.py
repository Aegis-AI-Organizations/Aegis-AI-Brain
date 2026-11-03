"""Proof contract v1.0.0 enforcement (Aegis-AI-Proto/docs/fr/proof-contract.md).

The Brain does not translate producer output: it validates each finding,
recomputes the proof level its evidences justify, rejects what does not
conform, and deduplicates across producers. Everything here is pure so it
can run inside the Temporal workflow sandbox.
"""

import json

SEED_FLAG = "aegis-flag-1234"

SOURCE_WORKER_PENTEST = "worker-pentest"
SOURCE_AGENT_CREW = "agent-crew"
SOURCES = {SOURCE_WORKER_PENTEST, SOURCE_AGENT_CREW}

SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}

PROOF_LEVEL_EXPLOITED = "exploited"
PROOF_LEVEL_DETECTED = "detected"
PROOF_LEVEL_UNVERIFIED = "unverified"
PROOF_LEVEL_RANK = {
    PROOF_LEVEL_UNVERIFIED: 0,
    PROOF_LEVEL_DETECTED: 1,
    PROOF_LEVEL_EXPLOITED: 2,
}

TOOL_STATUS_SUCCESS = "SUCCESS"


class FindingRejected(ValueError):
    pass


def _response_excerpt(loot_data: dict) -> str:
    excerpt = loot_data.get("response_excerpt")
    return excerpt if isinstance(excerpt, str) else ""


def _is_observed(loot_data: dict, source: str) -> bool:
    """A tool really ran and observed the target (contract §4.1, §4.2)."""
    if loot_data.get("status") != TOOL_STATUS_SUCCESS:
        return False
    if source == SOURCE_AGENT_CREW:
        return bool(_response_excerpt(loot_data).strip())
    return True


def _is_exploited(loot_data: dict, source: str) -> bool:
    exfiltration = loot_data.get("exfiltration")
    flag_extracted = (
        loot_data.get("seed_flag_extracted") is True
        and isinstance(exfiltration, dict)
        and exfiltration.get("proof_marker") == SEED_FLAG
    )
    if source == SOURCE_AGENT_CREW:
        # The flag must sit in the raw tool output, not only in LLM prose.
        return (
            flag_extracted
            and _is_observed(loot_data, source)
            and SEED_FLAG in _response_excerpt(loot_data)
        )
    return flag_extracted


def justified_proof_level(evidences: list, source: str) -> str:
    loot_items = [evidence["loot_data"] for evidence in evidences]
    if any(_is_exploited(loot_data, source) for loot_data in loot_items):
        return PROOF_LEVEL_EXPLOITED
    if any(_is_observed(loot_data, source) for loot_data in loot_items):
        return PROOF_LEVEL_DETECTED
    return PROOF_LEVEL_UNVERIFIED


def _require_text(finding: dict, field: str, allow_empty: bool = False) -> str:
    value = finding.get(field)
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise FindingRejected(f"{field} must be a non-empty string")
    return value


def _validate_evidences(raw_evidences) -> list:
    if raw_evidences is None:
        return []
    if not isinstance(raw_evidences, list):
        raise FindingRejected("evidences must be a list")
    evidences = []
    for evidence in raw_evidences:
        if not isinstance(evidence, dict):
            raise FindingRejected("each evidence must be an object")
        payload_used = evidence.get("payload_used")
        if not isinstance(payload_used, str) or not payload_used:
            raise FindingRejected("evidence.payload_used must be a non-empty string")
        if not isinstance(evidence.get("loot_data"), dict):
            raise FindingRejected("evidence.loot_data must be an object")
        evidences.append(
            {"payload_used": payload_used, "loot_data": evidence["loot_data"]}
        )
    return evidences


def validate_finding(raw: dict, source: str) -> dict:
    """Return the contract-conforming copy of a finding, or raise FindingRejected.

    source is the channel the finding arrived on; a finding cannot claim
    another producer. A declared proof_level is only ever downgraded to what
    the evidences justify (§4.2); a missing one is computed.
    """
    if not isinstance(raw, dict):
        raise FindingRejected("finding must be an object")
    declared_source = raw.get("source")
    if declared_source not in (None, source):
        raise FindingRejected(
            f"source {declared_source!r} does not match channel {source!r}"
        )

    severity = raw.get("severity")
    if severity not in SEVERITIES:
        raise FindingRejected(f"severity {severity!r} is not in {sorted(SEVERITIES)}")

    finding = dict(raw)
    finding["vuln_type"] = _require_text(raw, "vuln_type")
    finding["target_endpoint"] = _require_text(raw, "target_endpoint", allow_empty=True)
    finding["description"] = _require_text(raw, "description")
    finding["source"] = source
    finding["evidences"] = _validate_evidences(raw.get("evidences"))

    justified = justified_proof_level(finding["evidences"], source)
    declared = raw.get("proof_level")
    if declared is not None and declared not in PROOF_LEVEL_RANK:
        raise FindingRejected(f"proof_level {declared!r} is not a contract value")
    if declared is None or PROOF_LEVEL_RANK[declared] > PROOF_LEVEL_RANK[justified]:
        finding["proof_level"] = justified
    else:
        finding["proof_level"] = declared

    if not finding["evidences"] and finding["proof_level"] != PROOF_LEVEL_UNVERIFIED:
        raise FindingRejected("a finding above unverified needs at least one evidence")
    return finding


def ingest_findings(sources: dict) -> tuple[list, list]:
    """Validate findings per source channel.

    Returns (accepted, rejected); rejected items are
    {"source", "reason", "finding"} dicts for logging.
    """
    accepted = []
    rejected = []
    for source, raw_findings in sources.items():
        if not isinstance(raw_findings, list):
            continue
        for raw in raw_findings:
            try:
                accepted.append(validate_finding(raw, source))
            except FindingRejected as exc:
                rejected.append({"source": source, "reason": str(exc), "finding": raw})
    return accepted, rejected


def _stable_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def dedupe_evidences(evidences: list) -> list:
    deduped = []
    seen = set()
    for evidence in evidences or []:
        if not isinstance(evidence, dict):
            continue
        key = (
            evidence.get("payload_used") or "",
            _stable_json(evidence.get("loot_data")),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(evidence)
    return deduped


def _priority(finding: dict) -> tuple[int, int]:
    rank = PROOF_LEVEL_RANK.get(finding.get("proof_level"), -1)
    return rank, int(finding.get("source") == SOURCE_WORKER_PENTEST)


def dedupe_findings(findings: list) -> list:
    """Collapse findings sharing (vuln_type, target_endpoint) (contract §7).

    The strongest proof level wins, then worker-pentest; the losers'
    evidences are merged into the winner. First-seen order is kept.
    """
    kept: dict[tuple[str, str], dict] = {}
    for finding in findings or []:
        if not isinstance(finding, dict):
            continue
        key = (finding.get("vuln_type") or "", finding.get("target_endpoint") or "")
        current = kept.get(key)
        if current is None:
            kept[key] = {
                **finding,
                "evidences": dedupe_evidences(finding.get("evidences")),
            }
            continue
        winner, loser = (
            (finding, current)
            if _priority(finding) > _priority(current)
            else (current, finding)
        )
        kept[key] = {
            **winner,
            "evidences": dedupe_evidences(
                list(winner.get("evidences") or []) + list(loser.get("evidences") or [])
            ),
        }
    return list(kept.values())
