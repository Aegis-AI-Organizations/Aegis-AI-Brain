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
