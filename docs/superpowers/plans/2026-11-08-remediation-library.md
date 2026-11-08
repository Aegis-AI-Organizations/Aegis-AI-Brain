# Remediation Library (Phase B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fill in `remediation` with deterministic, vuln_type-keyed guidance for any finding that reaches `save_vulnerabilities`/the PDF without one (Phase A already threads `remediation` through storage, gRPC and the Dashboard; Phase B is what populates it when the producer didn't).

**Architecture:** A new pure module exposes a small exact-match dict from the known Worker-Pentest `vuln_type` strings to remediation text, plus a `get_remediation(vuln_type: str) -> str` lookup that returns `""` for anything unmatched (Agent-Crew's free-text types, `"Known CVE (template-matched)"` which doesn't name a specific CVE, `"TOOL_EXECUTION_ERROR"`, or anything future). The workflow's `_ingest_findings` calls it once, after `dedupe_findings`, only for findings whose `remediation` is falsy — never overwriting a producer-supplied value.

**Tech Stack:** Python, Temporal workflow sandbox (pure functions only, no I/O), pytest.

**Spec:** This plan's own header + Architecture section is the spec; agreed directly with the user in chat (no separate spec file for a change this size).

## Global Constraints

- Pure function, no I/O: must run inside the Temporal workflow sandbox like the rest of `proof_contract.py`.
- Never overwrite a `remediation` value a producer (Agent-Crew) already supplied.
- Exact-match only on `vuln_type` for this phase — no keyword/fuzzy matching of Agent-Crew's free-text types.
- Unmatched `vuln_type` → empty string, never a generic placeholder.

## Review Focus

- A finding with `remediation` already set to a non-empty string from Agent-Crew must keep it unchanged (not overwritten by the library).
- A finding with `remediation` set to `""` (not missing, explicitly empty) from any producer must still get enriched — "falsy" means both missing and empty.
- `vuln_type` values that don't exactly match the library (Agent-Crew free text, `"Known CVE (template-matched)"`, `"TOOL_EXECUTION_ERROR"`) must end up with `remediation == ""`, not raise.
- Enrichment must run after dedup, so it sees the final deduped list, not pre-dedup duplicates (avoids wasted lookups, and matches where Phase A's pass-through tests already anchor behavior).
- Findings with no `vuln_type` key at all (defensive case, contract validation requires it so should not occur, but the lookup function itself must not crash on `None`/missing).

---

### Task 1: `remediation_library.py` module

**Files:**
- Create: `src/services/remediation_library.py`
- Test: `tests/test_remediation_library.py`

**Interfaces:**
- Produces: `get_remediation(vuln_type: str | None) -> str` — exact-match lookup; returns `""` when `vuln_type` is `None` or not in the library.

- [ ] **Step 1: Write the failing tests**

```python
from services.remediation_library import get_remediation


def test_get_remediation_known_sqli():
    assert get_remediation("SQL Injection (SQLi)") != ""


def test_get_remediation_known_xss():
    assert get_remediation("Cross-Site Scripting (XSS)") != ""


def test_get_remediation_known_server_misconfiguration():
    assert get_remediation("SERVER_MISCONFIGURATION") != ""


def test_get_remediation_unknown_type_returns_empty():
    assert get_remediation("Something Agent-Crew made up") == ""


def test_get_remediation_known_cve_template_matched_returns_empty():
    assert get_remediation("Known CVE (template-matched)") == ""


def test_get_remediation_tool_execution_error_returns_empty():
    assert get_remediation("TOOL_EXECUTION_ERROR") == ""


def test_get_remediation_none_returns_empty():
    assert get_remediation(None) == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_remediation_library.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'services.remediation_library'`

- [ ] **Step 3: Implement `get_remediation(vuln_type: str | None) -> str` in `src/services/remediation_library.py`**

A module-level `REMEDIATION_LIBRARY: dict[str, str]` with exactly three keys — `"SQL Injection (SQLi)"`, `"Cross-Site Scripting (XSS)"`, `"SERVER_MISCONFIGURATION"` — each mapped to one or two sentences of concrete, actionable guidance (parameterized queries for SQLi, output encoding/CSP for XSS, disabling verbose error pages/default credentials/directory listing for server misconfiguration). `get_remediation` returns `REMEDIATION_LIBRARY.get(vuln_type, "")`, guarding against `vuln_type` being `None`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_remediation_library.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add src/services/remediation_library.py tests/test_remediation_library.py
git commit -m "[ADD] Add deterministic vuln_type-keyed remediation library"
```

---

### Task 2: Wire enrichment into `_ingest_findings`

**Files:**
- Modify: `src/workflows/graph_pentest_workflow.py` (the `_ingest_findings` static method, around line 505-530 as last read)
- Test: `tests/test_workflow.py`

**Interfaces:**
- Consumes: `get_remediation(vuln_type: str | None) -> str` from Task 1.
- Produces: `_ingest_findings` return value (the deduped list already relied on by `save_vulnerabilities` and the PDF) now has every finding's `remediation` non-empty whenever its `vuln_type` matches the library and it didn't already have one.

- [ ] **Step 1: Write the failing test(s)**

Add to `tests/test_workflow.py`, next to the existing `_ingest_findings`/dedup-related tests:

```python
def test_ingest_findings_fills_in_remediation_when_producer_omitted_it():
    report = {
        "vulnerabilities": [
            {
                "vuln_type": "SQL Injection (SQLi)",
                "severity": "CRITICAL",
                "target_endpoint": "http://target/search",
                "description": "desc",
                "evidences": [
                    {"payload_used": "'", "loot_data": {"status": "SUCCESS"}}
                ],
            }
        ]
    }

    [finding] = GraphDrivenPentestWorkflow._ingest_findings("scan-1", report, None)

    assert finding["remediation"] != ""


def test_ingest_findings_keeps_producer_supplied_remediation():
    crew_report = {
        "findings": [
            {
                "vuln_type": "SQL Injection (SQLi)",
                "severity": "CRITICAL",
                "target_endpoint": "http://target/search",
                "description": "desc",
                "remediation": "Agent-Crew's specific guidance for this finding.",
                "evidences": [
                    {
                        "payload_used": "'",
                        "loot_data": {
                            "status": "SUCCESS",
                            "response_excerpt": "error",
                        },
                    }
                ],
            }
        ]
    }

    [finding] = GraphDrivenPentestWorkflow._ingest_findings(
        "scan-1", None, crew_report
    )

    assert finding["remediation"] == "Agent-Crew's specific guidance for this finding."


def test_ingest_findings_leaves_remediation_empty_for_unmatched_vuln_type():
    report = {
        "vulnerabilities": [
            {
                "vuln_type": "Known CVE (template-matched)",
                "severity": "HIGH",
                "target_endpoint": "http://target/",
                "description": "desc",
                "evidences": [
                    {"payload_used": "nuclei", "loot_data": {"status": "SUCCESS"}}
                ],
            }
        ]
    }

    [finding] = GraphDrivenPentestWorkflow._ingest_findings("scan-1", report, None)

    assert finding["remediation"] == ""
```

Check the exact fixture shapes (evidence `loot_data`, required fields) against what `validate_finding`/`justified_proof_level` in `src/services/proof_contract.py` actually require (worker-pentest evidences only need `status: SUCCESS`; agent-crew evidences additionally need a non-empty `response_excerpt` per `_is_observed`) before running — adjust the fixtures if the contract rejects them, the assertions on `remediation` are what matters.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_workflow.py -k remediation -v`
Expected: first test FAILs with `KeyError: 'remediation'` or similar; second and third may already pass incidentally — confirm the first genuinely fails before continuing.

- [ ] **Step 3: Implement the enrichment call**

In `_ingest_findings`, after the existing `return dedupe_findings(accepted)` becomes `deduped = dedupe_findings(accepted)`, add a loop (or comprehension) that sets `finding["remediation"] = get_remediation(finding.get("vuln_type"))` for every finding in `deduped` whose current `remediation` is falsy (missing or `""`), then `return deduped`. Import `get_remediation` from `services.remediation_library` at the top of the file alongside the existing `services.proof_contract` imports.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_workflow.py -k remediation -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Run the full suite**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: all tests passed, no regressions

- [ ] **Step 6: Commit**

```bash
git add src/workflows/graph_pentest_workflow.py tests/test_workflow.py
git commit -m "[FEAT] Fill in remediation from the deterministic library when a producer omitted it"
```
