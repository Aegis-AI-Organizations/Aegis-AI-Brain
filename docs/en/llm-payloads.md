# 🧠 LLM Payload Assistance

The Brain can use LLM-assisted logic to help generate candidate payloads and
remediation explanations. This capability stays bounded by safety controls and
never replaces deterministic validation.

---

## Intended use

- Suggest candidate payloads for supported vulnerability classes.
- Adapt test inputs to observed service behavior.
- Summarize technical evidence for reports.
- Help produce remediation guidance after a finding is confirmed.

---

## Safety boundaries

- Never send secrets, customer credentials, tokens, or raw private data to
  external model providers.
- Execute offensive payloads only inside controlled scan / sandbox workflows.
- Store evidence produced by the worker, not the model's claims.
- Require deterministic validation before a vulnerability is marked confirmed.

---

## Worker interaction

The Pentest Worker treats model output as **input candidates**. The worker
remains responsible for request execution, response capture, proof extraction,
severity classification, evidence upload, and final status reporting.

---

## Prompt data

Allowed prompt context is limited to technical metadata: service type, version,
error class, HTTP status patterns, and sanitized response snippets.

---

*Aegis AI Brain — Decision Center — 2026*
