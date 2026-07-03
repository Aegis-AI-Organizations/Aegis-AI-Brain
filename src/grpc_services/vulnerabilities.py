import asyncio
import json
import logging
import grpc
from config.db import get_db_connection
import aegis.v2.vulnerability_pb2 as vulnerability_pb2
import aegis.v2.vulnerability_pb2_grpc as vulnerability_pb2_grpc
from .utils import to_pb_timestamp, with_identity

logger = logging.getLogger("aegis_brain_grpc")


def _extract_loot_fields(loot):
    if not loot:
        return "", ""
    if isinstance(loot, str):
        try:
            loot = json.loads(loot)
        except json.JSONDecodeError:
            return loot, ""
    if not isinstance(loot, dict):
        return "", json.dumps(loot)

    exfiltration = loot.get("exfiltration") or {}
    if not isinstance(exfiltration, dict):
        exfiltration = {}

    loot_proof = (
        loot.get("loot_proof")
        or exfiltration.get("proof_marker")
        or loot.get("sql_error")
        or ""
    )
    exfiltrated_data = (
        loot.get("exfiltrated_data")
        or exfiltration.get("sample_records")
        or loot.get("sample_records")
    )
    return str(loot_proof), json.dumps(exfiltrated_data) if exfiltrated_data else ""


class VulnerabilityService(vulnerability_pb2_grpc.VulnerabilityServiceServicer):
    def _get_vulns_db(self, scan_id, company_id):
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                """
                SELECT v.id, v.vuln_type, v.severity, v.target_endpoint, v.description, v.discovered_at, latest.loot_data
                FROM vulnerabilities v
                JOIN scans s ON v.scan_id = s.id
                LEFT JOIN LATERAL (
                    SELECT e.loot_data
                    FROM evidences e
                    WHERE e.vulnerability_id = v.id AND e.loot_data IS NOT NULL
                    ORDER BY e.captured_at DESC
                    LIMIT 1
                ) latest ON TRUE
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
            v_id, v_type, severity, endpoint, desc, disco, loot = row
            loot_proof, exfiltrated_data = _extract_loot_fields(loot)
            v = vulnerability_pb2.Vulnerability(
                id=str(v_id),
                vuln_type=str(v_type) if v_type is not None else "",
                severity=str(severity) if severity is not None else "",
                target_endpoint=endpoint if endpoint else "",
                description=desc if desc else "",
                loot_proof=loot_proof,
                exfiltrated_data=exfiltrated_data,
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
