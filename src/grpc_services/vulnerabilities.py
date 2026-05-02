import asyncio
import json
import logging
import grpc
from config.db import get_db_connection
import aegis.v2.vulnerability_pb2 as vulnerability_pb2
import aegis.v2.vulnerability_pb2_grpc as vulnerability_pb2_grpc
from .utils import to_pb_timestamp, with_identity

logger = logging.getLogger("aegis_brain_grpc")


class VulnerabilityService(vulnerability_pb2_grpc.VulnerabilityServiceServicer):
    def _get_vulns_db(self, scan_id, company_id):
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                """
                SELECT v.id, v.vuln_type, v.severity, v.target_endpoint, v.description, v.discovered_at
                FROM vulnerabilities v
                JOIN scans s ON v.scan_id = s.id
                WHERE v.scan_id = %s AND s.company_id = %s
                ORDER BY v.discovered_at DESC
                """,
                (scan_id, company_id),
            )
            rows = cur.fetchall()
            cur.close()
            return rows
        finally:
            if conn is not None:
                conn.close()

    @with_identity
    async def GetVulnerabilities(self, request, context, identity):
        company_id = identity.get("company_id")
        if not company_id:
            await context.abort(
                grpc.StatusCode.UNAUTHENTICATED, "Authentication required"
            )

        rows = await asyncio.to_thread(self._get_vulns_db, request.scan_id, company_id)
        vulns = []
        for row in rows:
            v_id, v_type, severity, endpoint, desc, disco = row
            v = vulnerability_pb2.Vulnerability(
                id=str(v_id),
                vuln_type=str(v_type) if v_type is not None else "",
                severity=str(severity) if severity is not None else "",
                target_endpoint=endpoint if endpoint else "",
                description=desc if desc else "",
            )
            if disco:
                v.discovered_at.CopyFrom(to_pb_timestamp(disco))
            vulns.append(v)
        return vulnerability_pb2.GetVulnerabilitiesResponse(vulnerabilities=vulns)

    def _get_evidences_db(self, vuln_id, company_id):
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                """
                SELECT e.id, e.payload_used, e.loot_data, e.captured_at
                FROM evidences e
                JOIN vulnerabilities v ON e.vulnerability_id = v.id
                JOIN scans s ON v.scan_id = s.id
                WHERE e.vulnerability_id = %s AND s.company_id = %s
                ORDER BY e.captured_at DESC
                """,
                (vuln_id, company_id),
            )
            rows = cur.fetchall()
            cur.close()
            return rows
        finally:
            if conn is not None:
                conn.close()

    @with_identity
    async def GetEvidences(self, request, context, identity):
        company_id = identity.get("company_id")
        if not company_id:
            await context.abort(
                grpc.StatusCode.UNAUTHENTICATED, "Authentication required"
            )

        rows = await asyncio.to_thread(
            self._get_evidences_db, request.vulnerability_id, company_id
        )
        evs = []
        for row in rows:
            e_id, payload, loot, captured = row
            e = vulnerability_pb2.Evidence(
                id=str(e_id),
                vulnerability_id=request.vulnerability_id,
                payload_used=str(payload) if payload is not None else "",
                loot_data=json.dumps(loot) if loot else "",
            )
            if captured:
                e.captured_at.CopyFrom(to_pb_timestamp(captured))
            evs.append(e)
        return vulnerability_pb2.GetEvidencesResponse(evidences=evs)
