import hashlib
import io
import uuid
from dataclasses import dataclass
from typing import Iterator

from minio.error import S3Error

from app.core.config import settings
from app.storage.minio_client import get_minio_client


@dataclass
class StoredObject:
    object_key: str
    content_hash: str
    size_bytes: int


def _sanitize_filename(filename: str) -> str:
    cleaned = filename.strip().replace("\\", "_").replace("/", "_")
    return cleaned or "document.bin"


def build_object_key(uploader_id: uuid.UUID, filename: str) -> str:
    cleaned_name = _sanitize_filename(filename)
    return f"{uploader_id}/{uuid.uuid4()}-{cleaned_name}"


def ensure_bucket() -> None:
    client = get_minio_client()
    if not client.bucket_exists(settings.MINIO_BUCKET):
        client.make_bucket(settings.MINIO_BUCKET)


def upload_document(uploader_id: uuid.UUID, filename: str, content: bytes) -> StoredObject:
    ensure_bucket()
    client = get_minio_client()
    object_key = build_object_key(uploader_id, filename)
    content_hash = hashlib.sha256(content).hexdigest()
    client.put_object(
        settings.MINIO_BUCKET,
        object_key,
        data=io.BytesIO(content),
        length=len(content),
    )
    return StoredObject(object_key=object_key, content_hash=content_hash, size_bytes=len(content))


def remove_document(object_key: str) -> None:
    client = get_minio_client()
    client.remove_object(settings.MINIO_BUCKET, object_key)


def stream_document_chunks(
    object_key: str, chunk_size: int = 1024 * 1024
) -> tuple[Iterator[bytes], str | None]:
    client = get_minio_client()
    response = client.get_object(settings.MINIO_BUCKET, object_key)
    content_type = response.headers.get("Content-Type")

    def _stream() -> Iterator[bytes]:
        try:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                yield chunk
        finally:
            response.close()
            response.release_conn()

    return _stream(), content_type


def object_exists(object_key: str) -> bool:
    client = get_minio_client()
    try:
        client.stat_object(settings.MINIO_BUCKET, object_key)
        return True
    except S3Error as exc:
        if exc.code in {"NoSuchKey", "NoSuchObject"}:
            return False
        raise
