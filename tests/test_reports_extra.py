from reports.engine import (
    _safe_text,
    _truncate_text,
    _format_loot_data,
    _ensure_space,
    build_report,
)
from fpdf import FPDF


def test_safe_text_none():
    assert _safe_text(None, default="EMPTY") == "EMPTY"


def test_truncate_text_long():
    text = "A" * 200
    truncated = _truncate_text(text, max_len=10)
    assert truncated == "AAAAAAA..."


def test_format_loot_data():
    assert _format_loot_data(None) == "No loot captured."
    assert _format_loot_data("") == "No loot captured."
    assert _format_loot_data({"key": "val"}) == '{\n  "key": "val"\n}'
    assert _format_loot_data("plain") == "plain"


def test_build_report_renders_more_content_when_remediation_present():
    base = {
        "vuln_type": "SQLi",
        "severity": "CRITICAL",
        "target_endpoint": "http://target",
        "description": "desc",
        "evidences": [],
    }
    without = build_report("scan-1", [base])
    with_remediation = build_report(
        "scan-1",
        [
            {
                **base,
                "remediation": "Use parameterized queries instead of string-concatenated SQL.",
            }
        ],
    )

    assert len(with_remediation) > len(without)


def test_build_report_output_is_identical_whether_remediation_is_absent_or_empty():
    base = {
        "vuln_type": "SQLi",
        "severity": "CRITICAL",
        "target_endpoint": "http://target",
        "description": "desc",
        "evidences": [],
    }

    missing_key = build_report("scan-1", [base])
    empty_string = build_report("scan-1", [{**base, "remediation": ""}])

    assert len(missing_key) == len(empty_string)


def test_ensure_space():
    pdf = FPDF()
    pdf.add_page()
    # Move near bottom
    pdf.set_y(pdf.h - 20)
    old_page_count = len(pdf.pages)
    _ensure_space(pdf, 50)
    assert len(pdf.pages) == old_page_count + 1
