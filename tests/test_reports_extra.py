from reports.engine import _safe_text, _truncate_text, _format_loot_data, _ensure_space
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


def test_ensure_space():
    pdf = FPDF()
    pdf.add_page()
    # Move near bottom
    pdf.set_y(pdf.h - 20)
    old_page_count = len(pdf.pages)
    _ensure_space(pdf, 50)
    assert len(pdf.pages) == old_page_count + 1
