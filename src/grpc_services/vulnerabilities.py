import asyncio
import json
import logging
from config.db import get_db_connection
import aegis.v2.vulnerability_pb2 as vulnerability_pb2
import aegis.v2.vulnerability_pb2_grpc as vulnerability_pb2_grpc
from .utils import to_pb_timestamp

logger = logging.getLogger("aegis_brain_grpc")


class VulnerabilityService(vulnerability_pb2_grpc.VulnerabilityServiceServicer):
    def _get_vulns_db(self, scan_id):
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT id, vuln_type, severity, target_endpoint, description, discovered_at FROM vulnerabilities WHERE scan_id = %s ORDER BY discovered_at DESC",
                (scan_id,),
            )
            rows = cur.fetchall()
            cur.close()
            return rows
        finally:
            if conn is not None:
                conn.close()

    async def GetVulnerabilities(self, request, context):
        rows = await asyncio.to_thread(self._get_vulns_db, request.scan_id)
        vulns = []
        for row in rows:
            v_id, v_type, severity, endpoint, desc, disco = row
            v = vulnerability_pb2.Vulnerability(
                id=str(v_id),
                vuln_type=v_type,
                severity=severity,
                target_endpoint=endpoint if endpoint else "",
                description=desc if desc else "",
            )
            if disco:
                v.discovered_at.CopyFrom(to_pb_timestamp(disco))
            vulns.append(v)
        return vulnerability_pb2.GetVulnerabilitiesResponse(vulnerabilities=vulns)

    def _get_evidences_db(self, vuln_id):
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT id, payload_used, loot_data, captured_at FROM evidences WHERE vulnerability_id = %s ORDER BY captured_at DESC",
                (vuln_id,),
            )
            rows = cur.fetchall()
            cur.close()
            return rows
        finally:
            if conn is not None:
                conn.close()

    async def GetEvidences(self, request, context):
        rows = await asyncio.to_thread(self._get_evidences_db, request.vulnerability_id)
        evs = []
        for row in rows:
            e_id, payload, loot, captured = row
            e = vulnerability_pb2.Evidence(
                id=str(e_id),
                vulnerability_id=request.vulnerability_id,
                payload_used=payload,
                loot_data=json.dumps(loot) if loot else "",
            )
            if captured:
                e.captured_at.CopyFrom(to_pb_timestamp(captured))
            evs.append(e)
        return vulnerability_pb2.GetEvidencesResponse(evidences=evs)
