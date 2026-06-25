import json
import logging
from urllib.parse import urlparse

from minio import Minio
from temporalio import activity

from config.config import (
    MINIO_ACCESS_KEY,
    MINIO_ENDPOINT,
    MINIO_INGEST_BUCKET,
    MINIO_SECRET_KEY,
    MINIO_SECURE,
)

logger = logging.getLogger("aegis_brain.minio_artifacts")


def parse_minio_reference(reference: str) -> tuple[str, str] | None:
    value = (reference or "").strip()
    if not value:
        return None

    lowered = value.lower()
    if lowered.startswith(("minio://", "s3://")):
        parsed = urlparse(value)
        bucket = parsed.netloc.strip()
        key = parsed.path.lstrip("/").strip()
        if bucket and key:
            return bucket, key
        return None

    if lowered.startswith("minio:"):
        key = value.split(":", 1)[1].strip().lstrip("/")
        if key:
            return MINIO_INGEST_BUCKET, key
    return None


def _artifact_payload(bucket: str, key: str, content: str) -> dict:
    stripped = content.strip()
    payload = {
        "bucket": bucket,
        "key": key,
        "content": stripped,
    }
    if not stripped:
        return payload

    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        payload["target_image"] = stripped
        return payload

    if not isinstance(data, dict):
        payload["target_image"] = stripped
        return payload

    sandbox_request = data.get("sandbox_request")
    if isinstance(sandbox_request, dict):
        payload["sandbox_request"] = sandbox_request
        payload["target_image"] = str(
            sandbox_request.get("target_image") or data.get("target_image") or ""
        ).strip()
        return payload

    if isinstance(data.get("topology"), dict):
        payload["sandbox_request"] = {
            "topology_json": json.dumps(data["topology"], separators=(",", ":")),
            "preferred_endpoint_workload": str(
                data.get("preferred_endpoint_workload") or ""
            ).strip(),
        }
        payload["target_image"] = str(data.get("target_image") or "topology:minio").strip()
        return payload

    if isinstance(data.get("topology_json"), str):
        payload["sandbox_request"] = {
            "topology_json": data["topology_json"],
            "preferred_endpoint_workload": str(
                data.get("preferred_endpoint_workload") or ""
            ).strip(),
        }
        payload["target_image"] = str(data.get("target_image") or "topology:minio").strip()
        return payload

    target_image = str(data.get("target_image") or data.get("image") or "").strip()
    if target_image:
        payload["target_image"] = target_image
    return payload


@activity.defn(name="DownloadMinIOArtifact")
async def download_minio_artifact(reference: str) -> dict:
    parsed = parse_minio_reference(reference)
    if not parsed:
        raise ValueError(f"unsupported MinIO artifact reference: {reference}")

    bucket, key = parsed
    logger.info("Downloading MinIO artifact bucket=%s key=%s", bucket, key)
    client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE,
    )
    response = client.get_object(bucket, key)
    try:
        content = response.read().decode("utf-8")
    finally:
        response.close()
        response.release_conn()

    payload = _artifact_payload(bucket, key, content)
    if not payload.get("target_image") and not payload.get("sandbox_request"):
        raise ValueError(f"MinIO artifact {bucket}/{key} does not describe a deployable target")
    return payload
