from temporalio import activity
from config.db import get_db_connection


@activity.defn
async def update_scan_status(args: list) -> str:
    """
    Updates the status of a specific scan in the PostgreSQL database.
    Args format: [scan_id, new_status]
    """
    scan_id = args[0]
    new_status = args[1]

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
        return f"Successfully updated scan {scan_id} to status {new_status}"
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
