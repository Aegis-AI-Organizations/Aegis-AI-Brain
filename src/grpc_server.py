import asyncio
import logging
import grpc
import uuid
import json
from google.protobuf.timestamp_pb2 import Timestamp

from config.db import get_db_connection

import aegis.v2.ping_pb2 as ping_pb2
import aegis.v2.ping_pb2_grpc as ping_pb2_grpc
import aegis.v2.scan_pb2 as scan_pb2
import aegis.v2.scan_pb2_grpc as scan_pb2_grpc
import aegis.v2.vulnerability_pb2 as vulnerability_pb2
import aegis.v2.vulnerability_pb2_grpc as vulnerability_pb2_grpc

logger = logging.getLogger("aegis_brain_grpc")


def to_pb_timestamp(dt):
    if dt is None:
        return None
    ts = Timestamp()
    ts.FromDatetime(dt)
    return ts


class PingService(ping_pb2_grpc.PingServiceServicer):
    async def Ping(self, request, context):
        return ping_pb2.PingResponse(message="pong")


class ScanService(scan_pb2_grpc.ScanServiceServicer):
    def __init__(self, temporal_client):
        self.temporal_client = temporal_client

    def _start_scan_db(self, scan_id, workflow_id, target_image):
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO scans (id, temporal_workflow_id, target_image, status) VALUES (%s, %s, %s, 'PENDING') RETURNING started_at",
                (scan_id, workflow_id, target_image),
            )
            started_at = cur.fetchone()[0]
            conn.commit()
            cur.close()
            return started_at
        finally:
            conn.close()

    async def StartScan(self, request, context):
        scan_id = str(uuid.uuid4())
        workflow_id = f"pentest-workflow-{scan_id}"

        # Save to DB asynchronously and get started_at
        started_at = await asyncio.to_thread(
            self._start_scan_db, scan_id, workflow_id, request.target_image
        )

        # Start temporal workflow
        try:
            await self.temporal_client.execute_workflow(
                "PentestWorkflow",
                args=[scan_id, request.target_image],
                id=workflow_id,
                task_queue="BRAIN_TASK_QUEUE",
            )
        except Exception as e:
            logger.error(f"Failed to start workflow: {e}")
            context.abort(grpc.StatusCode.INTERNAL, "Failed to start workflow")

        logger.info(f"Started scan {scan_id} for image: {request.target_image}")
        return scan_pb2.StartScanResponse(
            scan_id=scan_id, status="PENDING", started_at=to_pb_timestamp(started_at)
        )

    def _get_scan_status_db(self, scan_id):
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT status, started_at, completed_at FROM scans WHERE id = %s",
                (scan_id,),
            )
            row = cur.fetchone()
            cur.close()
            return row
        finally:
            conn.close()

    async def GetScanStatus(self, request, context):
        row = await asyncio.to_thread(self._get_scan_status_db, request.scan_id)
        if not row:
            context.abort(grpc.StatusCode.NOT_FOUND, "Scan not found")

        status, started_at, completed_at = row
        resp = scan_pb2.GetScanStatusResponse(
            scan_id=str(request.scan_id), status=str(status) if status else ""
        )
        if started_at:
            resp.started_at.CopyFrom(to_pb_timestamp(started_at))
        if completed_at:
            resp.completed_at.CopyFrom(to_pb_timestamp(completed_at))
        return resp

    def _list_scans_db(self):
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, temporal_workflow_id, target_image, status, started_at, completed_at FROM scans ORDER BY started_at DESC"
            )
            rows = cur.fetchall()
            cur.close()
            return rows
        finally:
            conn.close()

    async def ListScans(self, request, context):
        rows = await asyncio.to_thread(self._list_scans_db)
        scans = []
        for row in rows:
            scan_id, wf_id, target, status, started, completed = row
            detail = scan_pb2.ScanDetails(
                scan_id=str(scan_id) if scan_id else "",
                temporal_workflow_id=str(wf_id) if wf_id else "",
                target_image=str(target) if target else "",
                status=str(status) if status else "",
            )
            if started:
                detail.started_at.CopyFrom(to_pb_timestamp(started))
            if completed:
                detail.completed_at.CopyFrom(to_pb_timestamp(completed))
            scans.append(detail)
        return scan_pb2.ListScansResponse(scans=scans)

    def _get_scan_report_db(self, scan_id):
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT report_pdf FROM scans WHERE id = %s", (scan_id,))
            row = cur.fetchone()
            cur.close()
            return row[0] if row else None
        finally:
            conn.close()

    async def GetScanReport(self, request, context):
        pdf_bytes = await asyncio.to_thread(self._get_scan_report_db, request.scan_id)
        if pdf_bytes is None:
            context.abort(grpc.StatusCode.NOT_FOUND, "Scan or report not found")
        return scan_pb2.GetScanReportResponse(pdf_data=pdf_bytes)


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


async def serve(port: str, temporal_client=None):
    if temporal_client is None:
        logger.warning("Starting gRPC server without Temporal Client!")

    server = grpc.aio.server()

    ping_pb2_grpc.add_PingServiceServicer_to_server(PingService(), server)
    scan_pb2_grpc.add_ScanServiceServicer_to_server(
        ScanService(temporal_client), server
    )
    vulnerability_pb2_grpc.add_VulnerabilityServiceServicer_to_server(
        VulnerabilityService(), server
    )

    listen_addr = f"[::]:{port}"
    server.add_insecure_port(listen_addr)
    logger.info(f"📡 gRPC server starting on {listen_addr}")
    await server.start()
    await server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Enable gRPC debug logging
    logging.getLogger("grpc").setLevel(logging.DEBUG)
    asyncio.run(serve("50051"))
