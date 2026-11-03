import pytest

from grpc_services.vulnerabilities import _extract_loot_fields
from services.proof_contract import (
    FindingRejected,
    dedupe_findings,
    ingest_findings,
    validate_finding,
)


def _finding(**overrides):
    finding = {
        "vuln_type": "SQL Injection (SQLi)",
        "severity": "CRITICAL",
        "target_endpoint": "http://sandbox/search?q=",
        "description": "desc",
        "evidences": [
            {
                "payload_used": "'",
                "loot_data": {"tool": "sqli-probe", "status": "SUCCESS"},
            }
        ],
    }
    finding.update(overrides)
    return finding


FLAG_LOOT = {
    "status": "SUCCESS",
    "seed_flag_extracted": True,
    "exfiltration": {"proof_marker": "aegis-flag-1234"},
}


def test_worker_finding_with_extracted_flag_is_exploited():
    finding = validate_finding(
        _finding(evidences=[{"payload_used": "UNION", "loot_data": FLAG_LOOT}]),
        "worker-pentest",
    )
    assert finding["source"] == "worker-pentest"
    assert finding["proof_level"] == "exploited"


def test_worker_finding_with_successful_tool_is_detected():
    assert validate_finding(_finding(), "worker-pentest")["proof_level"] == "detected"


def test_tool_error_evidence_is_unverified():
    finding = _finding(
        evidences=[{"payload_used": "sqlmap", "loot_data": {"status": "ERROR"}}]
    )
    assert validate_finding(finding, "worker-pentest")["proof_level"] == "unverified"


def test_declared_proof_level_is_downgraded_never_upgraded():
    downgraded = validate_finding(_finding(proof_level="exploited"), "worker-pentest")
    assert downgraded["proof_level"] == "detected"

    kept = validate_finding(_finding(proof_level="unverified"), "worker-pentest")
    assert kept["proof_level"] == "unverified"


def test_crew_evidence_needs_a_raw_response_excerpt():
    without_excerpt = _finding(
        evidences=[{"payload_used": "GET /", "loot_data": {"status": "SUCCESS"}}],
        proof_level="detected",
    )
    assert (
        validate_finding(without_excerpt, "agent-crew")["proof_level"] == "unverified"
    )

    with_excerpt = _finding(
        evidences=[
            {
                "payload_used": "GET /",
                "loot_data": {"status": "SUCCESS", "response_excerpt": "SQL syntax"},
            }
        ],
        proof_level="detected",
    )
    assert validate_finding(with_excerpt, "agent-crew")["proof_level"] == "detected"


def test_crew_exploited_requires_flag_in_raw_excerpt():
    claimed = _finding(
        evidences=[
            {
                "payload_used": "GET /.env",
                "loot_data": {**FLAG_LOOT, "response_excerpt": "DB_PASSWORD=x"},
            }
        ],
        proof_level="exploited",
    )
    assert validate_finding(claimed, "agent-crew")["proof_level"] == "detected"

    proven = _finding(
        evidences=[
            {
                "payload_used": "GET /.env",
                "loot_data": {
                    **FLAG_LOOT,
                    "response_excerpt": "SECRET=aegis-flag-1234",
                },
            }
        ],
        proof_level="exploited",
    )
    assert validate_finding(proven, "agent-crew")["proof_level"] == "exploited"


def test_unverified_finding_may_have_no_evidence():
    finding = validate_finding(_finding(evidences=None), "agent-crew")
    assert finding["evidences"] == []
    assert finding["proof_level"] == "unverified"


@pytest.mark.parametrize(
    "overrides, reason",
    [
        ({"severity": "High"}, "severity"),
        ({"vuln_type": ""}, "vuln_type"),
        ({"description": None}, "description"),
        ({"target_endpoint": None}, "target_endpoint"),
        ({"source": "worker-pentest"}, "does not match channel"),
        ({"proof_level": "confirmed"}, "proof_level"),
        ({"evidences": "x"}, "evidences must be a list"),
        ({"evidences": [{"payload_used": "", "loot_data": {}}]}, "payload_used"),
        ({"evidences": [{"payload_used": "p", "loot_data": "x"}]}, "loot_data"),
    ],
)
def test_non_conforming_findings_are_rejected(overrides, reason):
    with pytest.raises(FindingRejected, match=reason):
        validate_finding(_finding(**overrides), "agent-crew")


def test_ingest_findings_splits_accepted_and_rejected():
    accepted, rejected = ingest_findings(
        {
            "worker-pentest": [_finding()],
            "agent-crew": [_finding(severity="nope"), "not-a-dict"],
        }
    )
    assert [f["source"] for f in accepted] == ["worker-pentest"]
    assert [r["source"] for r in rejected] == ["agent-crew", "agent-crew"]


def test_dedupe_keeps_strongest_proof_then_worker_and_merges_evidences():
    crew = validate_finding(
        _finding(
            severity="HIGH",
            evidences=[
                {
                    "payload_used": "GET /search?q='",
                    "loot_data": {"status": "SUCCESS", "response_excerpt": "SQL"},
                }
            ],
        ),
        "agent-crew",
    )
    worker = validate_finding(_finding(), "worker-pentest")
    other_endpoint = validate_finding(
        _finding(target_endpoint="http://sandbox/other"), "worker-pentest"
    )

    findings = dedupe_findings([crew, worker, other_endpoint, dict(worker)])

    assert len(findings) == 2
    merged = findings[0]
    assert merged["source"] == "worker-pentest"
    assert merged["severity"] == "CRITICAL"
    assert [e["payload_used"] for e in merged["evidences"]] == ["'", "GET /search?q='"]


def test_dedupe_prefers_exploited_over_worker_tie_break():
    worker_detected = validate_finding(_finding(), "worker-pentest")
    worker_exploited = validate_finding(
        _finding(
            description="flag",
            evidences=[{"payload_used": "UNION", "loot_data": FLAG_LOOT}],
        ),
        "worker-pentest",
    )

    (merged,) = dedupe_findings([worker_detected, worker_exploited])

    assert merged["proof_level"] == "exploited"
    assert merged["description"] == "flag"
    assert len(merged["evidences"]) == 2


@pytest.mark.parametrize(
    "loot, expected",
    [
        ({"exfiltration": {"proof_marker": "aegis-flag-1234"}}, "aegis-flag-1234"),
        ({"sql_error": "syntax error"}, "syntax error"),
        ({"sql_error_signature": "SQLSTATE[42000]"}, "SQLSTATE[42000]"),
        ({"loot_proof": "explicit", "sql_error": "ignored"}, "explicit"),
    ],
)
def test_loot_proof_derivation_cascade(loot, expected):
    loot_proof, _ = _extract_loot_fields(loot)
    assert loot_proof == expected
