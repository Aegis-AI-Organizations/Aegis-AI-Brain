import asyncio
import logging
import uuid
import grpc
from config.db import get_db_connection
import aegis.v2.scan_pb2 as scan_pb2
import aegis.v2.scan_pb2_grpc as scan_pb2_grpc
from .utils import to_pb_timestamp
from .broadcaster import broadcaster
from config.config import BRAIN_TASK_QUEUE

logger = logging.getLogger("aegis_brain_grpc")


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

    def _update_scan_status_db(self, scan_id, status):
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE scans SET status = %s WHERE id = %s",
                (status, scan_id),
            )
            conn.commit()
            cur.close()
        finally:
            conn.close()

    async def StartScan(self, request, context):
        scan_id = str(uuid.uuid4())
        workflow_id = f"pentest-workflow-{scan_id}"

        started_at = await asyncio.to_thread(
            self._start_scan_db, scan_id, workflow_id, request.target_image
        )

        try:
            await self.temporal_client.start_workflow(
                "PentestWorkflow",
                args=[scan_id, request.target_image],
                id=workflow_id,
                task_queue=BRAIN_TASK_QUEUE,
            )
        except Exception as e:
            logger.error(f"Failed to start workflow: {e}")
            # Compensation: Update DB status to FAILED
            await asyncio.to_thread(self._update_scan_status_db, scan_id, "FAILED")
            await context.abort(grpc.StatusCode.INTERNAL, "Failed to start workflow")

        logger.info(f"Started scan {scan_id} for image: {request.target_image}")
        return scan_pb2.StartScanResponse(
            scan_id=scan_id, status="PENDING", started_at=to_pb_timestamp(started_at)
        )

    def _get_scan_status_db(self, scan_id):
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT status, started_at, completed_at, target_image, temporal_workflow_id FROM scans WHERE id = %s",
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
            await context.abort(grpc.StatusCode.NOT_FOUND, "Scan not found")

        status, started_at, completed_at, target_image, wf_id = row
        resp = scan_pb2.GetScanStatusResponse(
            scan_id=str(request.scan_id),
            status=str(status) if status else "",
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
            await context.abort(grpc.StatusCode.NOT_FOUND, "Scan or report not found")
        return scan_pb2.GetScanReportResponse(pdf_data=pdf_bytes)

    async def WatchScanStatus(self, request, context):
        q = broadcaster.register()
        try:
            while True:
                scan_id, status = await q.get()
                if not request.scan_id or request.scan_id == scan_id:
                    yield scan_pb2.WatchScanStatusResponse(
                        scan_id=scan_id, status=status
                    )
        finally:
            broadcaster.unregister(q)
