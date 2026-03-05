from temporalio import activity
from config.db import get_db_connection
import logging

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
