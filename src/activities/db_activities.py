from temporalio import activity
from config.db import get_db_connection
import logging
from datetime import datetime, timezone
from io import BytesIO
from fpdf import FPDF
from fpdf.enums import XPos, YPos

logger = logging.getLogger(__name__)


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
    import json

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


def _build_pdf_report_bytes(scan_id: str, vulnerabilities: list) -> bytes:
    """Builds a PDF vulnerability report and returns it as bytes."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Aegis AI - Scan Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 8, f"Scan ID: {scan_id}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    pdf.cell(0, 8, f"Generated at: {generated_at}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(
        0,
        8,
        f"Total vulnerabilities: {len(vulnerabilities)}",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(3)

    if not vulnerabilities:
        pdf.set_font("Helvetica", "I", 11)
        pdf.multi_cell(0, 7, "No vulnerabilities were reported for this scan.")
    else:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Vulnerabilities", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1)

        for idx, vuln in enumerate(vulnerabilities, start=1):
            pdf.set_font("Helvetica", "B", 11)
            vuln_type = vuln.get("vuln_type", "UNKNOWN")
            severity = vuln.get("severity", "UNKNOWN")
            pdf.multi_cell(
                0,
                7,
                f"{idx}. [{severity}] {vuln_type}",
                border=0,
                align="L",
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )

            pdf.set_font("Helvetica", size=10)
            target_endpoint = vuln.get("target_endpoint", "N/A")
            description = vuln.get("description", "N/A")
            pdf.multi_cell(
                0,
                6,
                f"Target endpoint: {target_endpoint}",
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
            pdf.multi_cell(
                0,
                6,
                f"Description: {description}",
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )

            evidences = vuln.get("evidences", [])
            if evidences:
                pdf.multi_cell(
                    0,
                    6,
                    f"Evidences ({len(evidences)}):",
                    new_x=XPos.LMARGIN,
                    new_y=YPos.NEXT,
                )
                for evidence_index, evidence in enumerate(evidences, start=1):
                    payload = evidence.get("payload_used", "N/A")
                    loot_data = evidence.get("loot_data")
                    loot_repr = str(loot_data) if loot_data is not None else "N/A"
                    pdf.multi_cell(
                        0,
                        6,
                        (
                            f"  - #{evidence_index} payload={payload}; "
                            f"loot_data={loot_repr}"
                        ),
                        new_x=XPos.LMARGIN,
                        new_y=YPos.NEXT,
                    )
            else:
                pdf.multi_cell(
                    0, 6, "Evidences: none", new_x=XPos.LMARGIN, new_y=YPos.NEXT
                )

            pdf.ln(2)

    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()


def _execute_generate_and_store_pdf_report(scan_id: str, vulnerabilities: list):
    """Generates PDF bytes in memory and stores them in scans.report_pdf."""
    conn = get_db_connection()
    if not conn:
        raise Exception("Database connection failed")

    report_pdf = _build_pdf_report_bytes(scan_id, vulnerabilities)

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
