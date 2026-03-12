from temporalio import activity
from config.db import get_db_connection
import logging
import json
from reports.engine import build_report

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
