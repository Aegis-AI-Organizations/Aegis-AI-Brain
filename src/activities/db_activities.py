from temporalio import activity
from config.db import get_db_connection
import logging
from reports.engine import build_report
import json
import os
from datetime import datetime, timezone
from io import BytesIO
from urllib.parse import urlparse
from fpdf import FPDF, FontFace
from fpdf.enums import XPos, YPos

logger = logging.getLogger(__name__)

SEVERITY_DISPLAY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO", "UNKNOWN"]
SEVERITY_COLORS = {
    "CRITICAL": (153, 27, 27),
    "HIGH": (194, 65, 12),
    "MEDIUM": (180, 83, 9),
    "LOW": (22, 101, 52),
    "INFO": (30, 64, 175),
    "UNKNOWN": (75, 85, 99),
}
REPORT_PRIMARY_COLOR = (16, 44, 84)
SECTION_FILL_COLOR = (232, 240, 251)
CONTENT_BOX_FILL_COLOR = (246, 249, 253)
MUTED_TEXT_COLOR = (107, 114, 128)


def _execute_status_update(scan_id: str, new_status: str):
    """Internal helper to execute the SQL update."""
    conn = get_db_connection()
    if not conn:
        raise Exception("Database connection failed")

    try:
        cur = conn.cursor()
        cur.execute("UPDATE scans SET status = %s WHERE id = %s", (new_status, scan_id))

        if cur.rowcount == 0:
            raise Exception(f"Scan ID {scan_id} not found to update")

        conn.commit()
        cur.close()
        logger.info(f"Scan {scan_id} status updated to {new_status}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating scan {scan_id} status: {e}")
        raise e
    finally:
        conn.close()


@activity.defn
async def update_scan_status(scan_id: str, new_status: str) -> str:
    """
    Updates the status of a specific scan in the PostgreSQL database.
    """
    _execute_status_update(scan_id, new_status)
    return f"Successfully updated scan {scan_id} to status {new_status}"


def _execute_save_vulnerabilities(scan_id: str, vulnerabilities: list):
    """Internal helper to insert vulnerabilities and their evidences."""

    conn = get_db_connection()
    if not conn:
        raise Exception("Database connection failed")

    try:
        cur = conn.cursor()
        for v in vulnerabilities:
            cur.execute(
                """
                INSERT INTO vulnerabilities (scan_id, vuln_type, severity, target_endpoint, description)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    scan_id,
                    v.get("vuln_type"),
                    v.get("severity"),
                    v.get("target_endpoint"),
                    v.get("description"),
                ),
            )
            vuln_id = cur.fetchone()[0]

            for ev in v.get("evidences", []):
                cur.execute(
                    """
                    INSERT INTO evidences (vulnerability_id, payload_used, loot_data)
                    VALUES (%s, %s, %s);
                    """,
                    (
                        vuln_id,
                        ev.get("payload_used"),
                        json.dumps(ev.get("loot_data"))
                        if ev.get("loot_data")
                        else None,
                    ),
                )

        conn.commit()
        cur.close()
        logger.info(f"Saved {len(vulnerabilities)} vulnerabilities for scan {scan_id}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving vulnerabilities for scan {scan_id}: {e}")
        raise e
    finally:
        conn.close()


@activity.defn
async def save_vulnerabilities(scan_id: str, vulnerabilities: list) -> str:
    """
    Saves a list of vulnerabilities and their evidences to the PostgreSQL database.
    """
    if not vulnerabilities:
        return f"No vulnerabilities to save for scan {scan_id}"

    _execute_save_vulnerabilities(scan_id, vulnerabilities)
    return (
        f"Successfully saved {len(vulnerabilities)} vulnerabilities for scan {scan_id}"
    )


def _safe_text(value, default: str = "N/A") -> str:
    """Normalizes raw values into clean text for PDF rendering."""
    if value is None:
        return default

    text = str(value).strip()
    return text if text else default


def _normalize_severity(severity) -> str:
    """Returns an uppercase severity in the supported range."""
    raw = _safe_text(severity, default="UNKNOWN").upper()
    severity_aliases = {"INFORMATIONAL": "INFO", "MED": "MEDIUM"}
    normalized = severity_aliases.get(raw, raw)
    return normalized if normalized in SEVERITY_COLORS else "UNKNOWN"


def _severity_fill_color(severity) -> tuple:
    return SEVERITY_COLORS[_normalize_severity(severity)]


def _count_by_severity(vulnerabilities: list) -> dict:
    counts = {severity: 0 for severity in SEVERITY_DISPLAY_ORDER}
    for vulnerability in vulnerabilities:
        normalized = _normalize_severity(vulnerability.get("severity"))
        counts[normalized] = counts.get(normalized, 0) + 1
    return counts


def _truncate_text(text, max_len: int = 120) -> str:
    normalized = _safe_text(text)
    if len(normalized) <= max_len:
        return normalized
    return f"{normalized[: max_len - 3]}..."


def _format_loot_data(loot_data) -> str:
    if loot_data in (None, ""):
        return "No loot captured."
    if isinstance(loot_data, (dict, list)):
        return json.dumps(loot_data, indent=2, ensure_ascii=True)
    return str(loot_data)


def _extract_target_name(vulnerabilities: list) -> str:
    for vulnerability in vulnerabilities:
        for key in ("target_name", "target", "target_image"):
            value = vulnerability.get(key)
            if value:
                return str(value)

    for vulnerability in vulnerabilities:
        endpoint = _safe_text(vulnerability.get("target_endpoint"), default="")
        if not endpoint:
            continue

        parsed = urlparse(endpoint if "://" in endpoint else f"http://{endpoint}")
        host = parsed.netloc or parsed.path.split("/")[0]
        if host:
            return host

    return "Unknown target"


def _extract_target_image_path(vulnerabilities: list):
    for vulnerability in vulnerabilities:
        for key in ("target_image_path", "target_image_file", "target_image"):
            candidate = vulnerability.get(key)
            if (
                isinstance(candidate, str)
                and candidate.strip()
                and os.path.isfile(candidate)
            ):
                return candidate
    return None


def _ensure_space(pdf: FPDF, required_space: float):
    if pdf.get_y() + required_space > pdf.h - pdf.b_margin:
        pdf.add_page()


def _render_section_header(pdf: FPDF, title: str):
    pdf.set_draw_color(206, 221, 240)
    pdf.set_fill_color(*SECTION_FILL_COLOR)
    pdf.set_text_color(20, 20, 20)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, title, border=1, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)


def _render_cover_page(
    pdf: FPDF, scan_id: str, vulnerabilities: list, generated_at: str
):
    target_name = _extract_target_name(vulnerabilities)
    target_image_path = _extract_target_image_path(vulnerabilities)

    pdf.add_page()
    pdf.set_fill_color(*REPORT_PRIMARY_COLOR)
    pdf.rect(0, 0, pdf.w, 60, style="F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(pdf.l_margin, 17)
    pdf.set_font("Helvetica", "B", 24)
    pdf.cell(0, 11, "Aegis AI Pentest Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", size=12)
    pdf.cell(
        0,
        7,
        "Security Assessment Summary",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )

    pdf.set_text_color(0, 0, 0)
    pdf.set_y(76)
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 8, "Target Snapshot", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    image_box_x = pdf.l_margin
    image_box_y = pdf.get_y()
    image_box_w = 64
    image_box_h = 48
    pdf.set_draw_color(207, 216, 224)
    pdf.set_fill_color(*CONTENT_BOX_FILL_COLOR)
    pdf.rect(image_box_x, image_box_y, image_box_w, image_box_h, style="FD")

    if target_image_path:
        try:
            pdf.image(
                target_image_path,
                x=image_box_x + 1.5,
                y=image_box_y + 1.5,
                w=image_box_w - 3,
                h=image_box_h - 3,
                keep_aspect_ratio=True,
            )
        except Exception:
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(*MUTED_TEXT_COLOR)
            pdf.set_xy(image_box_x, image_box_y + 21)
            pdf.cell(image_box_w, 6, "Target image unavailable", align="C")
            pdf.set_text_color(0, 0, 0)
    else:
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(*MUTED_TEXT_COLOR)
        pdf.set_xy(image_box_x, image_box_y + 21)
        pdf.cell(image_box_w, 6, "No target image provided", align="C")
        pdf.set_text_color(0, 0, 0)

    info_x = image_box_x + image_box_w + 10
    info_w = pdf.w - pdf.r_margin - info_x
    pdf.set_xy(info_x, image_box_y)

    cover_fields = [
        ("Target Name", target_name),
        ("Scan ID", scan_id),
        ("Generation Date", generated_at),
    ]
    for label, value in cover_fields:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_x(info_x)
        pdf.cell(info_w, 6, label, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", size=11)
        pdf.set_x(info_x)
        pdf.multi_cell(
            info_w, 6, _safe_text(value), new_x=XPos.LMARGIN, new_y=YPos.NEXT
        )
        pdf.ln(1)

    pdf.set_y(max(pdf.get_y(), image_box_y + image_box_h + 10))
    pdf.set_fill_color(236, 243, 252)
    pdf.set_draw_color(206, 221, 240)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(
        0,
        11,
        f"Total vulnerabilities detected: {len(vulnerabilities)}",
        border=1,
        fill=True,
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )


def _render_summary(pdf: FPDF, vulnerabilities: list):
    counts = _count_by_severity(vulnerabilities)
    total = len(vulnerabilities)

    pdf.add_page()
    _render_section_header(pdf, "Executive Summary")

    pdf.set_font("Helvetica", size=11)
    summary_text = (
        "This report consolidates the automated pentest findings collected for the "
        "current scan target. Prioritize remediation from CRITICAL to LOW severity "
        "and validate fixes with a follow-up scan."
    )
    pdf.multi_cell(0, 7, summary_text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    pdf.set_fill_color(237, 244, 253)
    pdf.set_draw_color(206, 221, 240)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(
        0,
        11,
        f"Total vulnerabilities: {total}",
        border=1,
        fill=True,
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Severity Breakdown", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)

    for severity in SEVERITY_DISPLAY_ORDER:
        severity_color = _severity_fill_color(severity)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fill_color(*severity_color)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(
            38, 8, severity, align="C", fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP
        )
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", size=10)
        pdf.cell(
            0,
            8,
            f"{counts.get(severity, 0)} finding(s)",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )


def _render_vulnerability_table(pdf: FPDF, vulnerabilities: list):
    pdf.add_page()
    _render_section_header(pdf, "Vulnerability Summary")

    if not vulnerabilities:
        pdf.set_font("Helvetica", "I", 11)
        pdf.multi_cell(0, 7, "No vulnerabilities were reported for this scan.")
        return

    heading_style = FontFace(emphasis="BOLD", fill_color=(235, 241, 249))
    epw = pdf.epw
    col_widths = (epw * 0.24, epw * 0.14, epw * 0.27, epw * 0.35)

    with pdf.table(
        width=epw,
        col_widths=col_widths,
        line_height=6,
        text_align=("L", "C", "L", "L"),
        first_row_as_headings=True,
        headings_style=heading_style,
    ) as table:
        heading = table.row()
        heading.cell("Vulnerability Type")
        heading.cell("Severity")
        heading.cell("Endpoint")
        heading.cell("Short Description")

        for vulnerability in vulnerabilities:
            severity = _normalize_severity(vulnerability.get("severity"))
            severity_style = FontFace(
                emphasis="BOLD",
                color=(255, 255, 255),
                fill_color=_severity_fill_color(severity),
            )

            row = table.row()
            row.cell(_safe_text(vulnerability.get("vuln_type"), default="Unknown"))
            row.cell(severity, style=severity_style)
            row.cell(_safe_text(vulnerability.get("target_endpoint")))
            row.cell(_truncate_text(vulnerability.get("description"), max_len=110))


def _render_boxed_block(pdf: FPDF, title: str, content: str):
    _ensure_space(pdf, required_space=22)
    pdf.set_fill_color(*SECTION_FILL_COLOR)
    pdf.set_draw_color(206, 221, 240)
    pdf.set_font("Helvetica", "B", 10)
    pdf.multi_cell(
        0, 7, title, border=1, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT
    )
    pdf.set_font("Courier", size=9)
    pdf.multi_cell(
        0,
        5.5,
        _safe_text(content, default="N/A"),
        border=1,
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(1)


def _render_vulnerability_detail(pdf: FPDF, index: int, vulnerability: dict):
    _ensure_space(pdf, required_space=50)

    title = _safe_text(
        vulnerability.get("title") or vulnerability.get("vuln_type"),
        default="Untitled vulnerability",
    )
    severity = _normalize_severity(vulnerability.get("severity"))
    endpoint = _safe_text(vulnerability.get("target_endpoint"))
    description = _safe_text(
        vulnerability.get("description"), default="No description provided."
    )
    evidences = vulnerability.get("evidences", []) or []

    pdf.set_fill_color(245, 248, 252)
    pdf.set_draw_color(206, 221, 240)
    pdf.set_font("Helvetica", "B", 12)
    pdf.multi_cell(
        0,
        8,
        f"{index}. {title}",
        border=1,
        fill=True,
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(1)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(24, 7, "Severity:", new_x=XPos.RIGHT, new_y=YPos.TOP)
    badge_width = max(25, pdf.get_string_width(severity) + 8)
    pdf.set_fill_color(*_severity_fill_color(severity))
    pdf.set_text_color(255, 255, 255)
    pdf.cell(
        badge_width,
        7,
        severity,
        align="C",
        fill=True,
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.set_text_color(0, 0, 0)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Endpoint", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(0, 6, endpoint, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Description", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(0, 6, description, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)

    payload_blocks = []
    loot_blocks = []
    for evidence_index, evidence in enumerate(evidences, start=1):
        payload_blocks.append(
            f"[{evidence_index}] "
            f"{_safe_text(evidence.get('payload_used'), default='No payload recorded.')}"
        )
        loot_blocks.append(
            f"[{evidence_index}] {_format_loot_data(evidence.get('loot_data'))}"
        )

    _render_boxed_block(
        pdf,
        "Payload Used",
        "\n\n".join(payload_blocks)
        if payload_blocks
        else "No payload recorded for this vulnerability.",
    )
    _render_boxed_block(
        pdf,
        "Evidence / Loot",
        "\n\n".join(loot_blocks)
        if loot_blocks
        else "No evidence or loot data captured.",
    )
    pdf.ln(2)


def _build_pdf_report_bytes(scan_id: str, vulnerabilities: list) -> bytes:
    """Builds a pentest-style PDF report and returns it as bytes."""
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    pdf = FPDF(format="A4")
    pdf.set_margins(left=18, top=18, right=18)
    pdf.set_auto_page_break(auto=True, margin=18)

    _render_cover_page(pdf, scan_id, vulnerabilities, generated_at)
    _render_summary(pdf, vulnerabilities)
    _render_vulnerability_table(pdf, vulnerabilities)

    pdf.add_page()
    _render_section_header(pdf, "Detailed Vulnerability Findings")
    if not vulnerabilities:
        pdf.set_font("Helvetica", "I", 11)
        pdf.multi_cell(0, 7, "No vulnerabilities were reported for this scan.")
    else:
        for idx, vulnerability in enumerate(vulnerabilities, start=1):
            _render_vulnerability_detail(pdf, idx, vulnerability)

    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()


def _execute_generate_and_store_pdf_report(scan_id: str, vulnerabilities: list):
    """Generates PDF bytes in memory and stores them in scans.report_pdf."""
    conn = get_db_connection()
    if not conn:
        raise Exception("Database connection failed")

    report_pdf = build_report(scan_id, vulnerabilities)

    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE scans SET report_pdf = %s WHERE id = %s", (report_pdf, scan_id)
        )

        if cur.rowcount == 0:
            raise Exception(f"Scan ID {scan_id} not found to store PDF report")

        conn.commit()
        cur.close()
        logger.info(f"Stored PDF report for scan {scan_id} ({len(report_pdf)} bytes)")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error storing PDF report for scan {scan_id}: {e}")
        raise e
    finally:
        conn.close()


@activity.defn
async def generate_and_store_pdf_report(scan_id: str, vulnerabilities: list) -> str:
    """
    Generates a structured PDF report in memory and stores it in scans.report_pdf.
    """
    _execute_generate_and_store_pdf_report(scan_id, vulnerabilities)
    return f"Successfully generated and stored PDF report for scan {scan_id}"
