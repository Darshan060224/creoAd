"""
MinIO storage helpers for final video artifacts.
"""

from __future__ import annotations

import shutil
from datetime import timedelta
from pathlib import Path
import uuid

try:
    from minio import Minio
except Exception:
    Minio = None

try:
    from ..config import settings
except ImportError:
    from config import settings


def _client() -> Minio:
    if Minio is None:
        raise RuntimeError("MinIO client is unavailable")
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def ensure_bucket() -> None:
    client = _client()
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)


def upload_video_return_url(local_video_path: str, campaign_id: str) -> str:
    """Upload a local video to MinIO and return a pre-signed URL."""

    object_name = f"ads/{campaign_id}/final_{uuid.uuid4().hex[:8]}.mp4"
    file_path = Path(local_video_path)

    if Minio is None:
        fallback_dir = Path("output") / campaign_id
        fallback_dir.mkdir(parents=True, exist_ok=True)
        fallback_name = object_name.replace("/", "_")
        fallback_path = fallback_dir / fallback_name
        shutil.copy2(file_path, fallback_path)
        return f"/output/{campaign_id}/{fallback_name}"

    try:
        ensure_bucket()
        client = _client()

        client.fput_object(
            bucket_name=settings.minio_bucket,
            object_name=object_name,
            file_path=str(file_path),
            content_type="video/mp4",
        )

        return client.presigned_get_object(
            bucket_name=settings.minio_bucket,
            object_name=object_name,
            expires=timedelta(days=7),
        )
    except Exception:
        fallback_dir = Path("output") / campaign_id
        fallback_dir.mkdir(parents=True, exist_ok=True)
        fallback_name = object_name.replace("/", "_")
        fallback_path = fallback_dir / fallback_name
        shutil.copy2(file_path, fallback_path)
        return f"/output/{campaign_id}/{fallback_name}"