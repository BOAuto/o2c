"""MinIO object keys and uploads for O2C order ingestion artifacts."""

from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone
from typing import Literal

from minio.error import S3Error

from app.core.config import settings
from app.storage.minio_client import get_minio_client

OrderIngestionStorageType = Literal["eml", "html", "POattachments"]


def build_order_ingestion_object_key(
    *,
    year: int,
    month: int,
    storage_type: OrderIngestionStorageType,
    file_name: str,
) -> str:
    safe_name = file_name.strip().replace("\\", "_").replace("/", "_") or "file"
    return f"{year:04d}/{month:02d}/OrderIngestion/{storage_type}/{safe_name}"


def default_ingestion_timestamp() -> tuple[int, int]:
    now = datetime.now(timezone.utc)
    return now.year, now.month


def ensure_bucket() -> None:
    client = get_minio_client()
    if not client.bucket_exists(settings.MINIO_BUCKET):
        client.make_bucket(settings.MINIO_BUCKET)


def upload_order_ingestion_bytes(
    *,
    storage_type: OrderIngestionStorageType,
    file_name: str,
    content: bytes,
    content_type: str | None = None,
) -> tuple[str, int]:
    """Upload to MinIO; return (object_key, size_bytes)."""
    ensure_bucket()
    year, month = default_ingestion_timestamp()
    unique = uuid.uuid4().hex[:12]
    base, _, ext = file_name.rpartition(".")
    if ext:
        unique_name = f"{base}-{unique}.{ext}" if base else f"{unique}.{ext}"
    else:
        unique_name = f"{file_name}-{unique}" if file_name else unique
    object_key = build_order_ingestion_object_key(
        year=year, month=month, storage_type=storage_type, file_name=unique_name
    )
    client = get_minio_client()
    client.put_object(
        settings.MINIO_BUCKET,
        object_key,
        data=io.BytesIO(content),
        length=len(content),
        content_type=content_type or "application/octet-stream",
    )
    return object_key, len(content)


def stat_object_key(object_key: str) -> bool:
    client = get_minio_client()
    try:
        client.stat_object(settings.MINIO_BUCKET, object_key)
        return True
    except S3Error as exc:
        if exc.code in {"NoSuchKey", "NoSuchObject"}:
            return False
        raise


def read_order_ingestion_object_bytes(object_key: str) -> bytes:
    client = get_minio_client()
    response = client.get_object(settings.MINIO_BUCKET, object_key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()
