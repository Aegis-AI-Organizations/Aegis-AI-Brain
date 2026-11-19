"""Deterministic, vuln_type-keyed remediation guidance (proof-contract Phase B).

Exact-match only: Worker-Pentest emits a closed, known set of vuln_type
strings, so a dict lookup is sufficient. Agent-Crew's free-text vuln_type
values, and generic types like "Known CVE (template-matched)" that don't
name a specific CVE, fall through to an empty string rather than a
misleading generic suggestion.
"""

REMEDIATION_LIBRARY: dict[str, str] = {
    "SQL Injection (SQLi)": (
        "Use parameterized queries or prepared statements instead of "
        "concatenating user input into SQL. Apply least-privilege database "
        "accounts and validate/escape input as a defense-in-depth measure."
    ),
    "Cross-Site Scripting (XSS)": (
        "Encode output based on context (HTML, attribute, JS, URL) before "
        "rendering user-controlled data, and deploy a Content-Security-Policy "
        "header to limit the impact of any injected script."
    ),
    "SERVER_MISCONFIGURATION": (
        "Disable verbose error pages and directory listing, remove default "
        "credentials and sample/admin endpoints, and apply the hosting "
        "platform's hardening baseline before exposing the service."
    ),
}


def get_remediation(vuln_type: str | None) -> str:
    if vuln_type is None:
        return ""
    return REMEDIATION_LIBRARY.get(vuln_type, "")
