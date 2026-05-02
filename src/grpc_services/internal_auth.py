import logging
from config.db import get_db_connection

logger = logging.getLogger(__name__)

class InternalAuthService:
    """Internal service for verifying agent deployment tokens."""

    def _verify_token_db_sync(self, token: str) -> str:
        """Synchronously verifies an agent token and returns the company_id."""
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            # Assuming a table 'deployment_tokens' exists with columns 'token' and 'company_id'
            # and that it's active.
            cur.execute(
                "SELECT company_id FROM deployment_tokens WHERE token = %s AND is_active = TRUE",
                (token,),
            )
            row = cur.fetchone()
            cur.close()
            if row:
                return str(row[0])
            return None
        except Exception as e:
            logger.error(f"Database error during token verification: {e}")
            return None
        finally:
            if conn:
                conn.close()
