import os
import uuid

import pytest
from minio.error import S3Error

from app.core.config import settings
from app.storage.documents import (
    object_exists,
    remove_document,
    stream_document_chunks,
    upload_document,
)


@pytest.mark.integration
def test_minio_upload_stream_delete_roundtrip() -> None:
    """Live MinIO integration check for storage helpers."""
    original_endpoint = settings.MINIO_ENDPOINT
    original_access_key = settings.MINIO_ACCESS_KEY
    original_secret_key = settings.MINIO_SECRET_KEY
    try:
        settings.MINIO_ENDPOINT = os.getenv("MINIO_INTEGRATION_ENDPOINT", "localhost:9000")
        settings.MINIO_ACCESS_KEY = os.getenv("MINIO_INTEGRATION_ACCESS_KEY", "minioapp")
        settings.MINIO_SECRET_KEY = os.getenv(
            "MINIO_INTEGRATION_SECRET_KEY", "minioapp123"
        )

        payload = (b"minio-integration-roundtrip-" + uuid.uuid4().hex.encode()) * 32
        stored = upload_document(uuid.uuid4(), "integration.bin", payload)
        assert object_exists(stored.object_key) is True

        stream, _content_type = stream_document_chunks(stored.object_key, chunk_size=1024)
        downloaded = b"".join(stream)
        assert downloaded == payload

        remove_document(stored.object_key)
        assert object_exists(stored.object_key) is False
    except S3Error as exc:
        pytest.skip(f"MinIO integration unavailable: {exc}")
    finally:
        settings.MINIO_ENDPOINT = original_endpoint
        settings.MINIO_ACCESS_KEY = original_access_key
        settings.MINIO_SECRET_KEY = original_secret_key
