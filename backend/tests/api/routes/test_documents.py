from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import settings


def _install_storage_mocks(monkeypatch: Any) -> dict[str, tuple[bytes, str]]:
    store: dict[str, tuple[bytes, str]] = {}

    class _Stored:
        def __init__(self, object_key: str, content_hash: str, size_bytes: int) -> None:
            self.object_key = object_key
            self.content_hash = content_hash
            self.size_bytes = size_bytes

    def upload(uploader_id: Any, filename: str, content: bytes) -> _Stored:
        object_key = f"{uploader_id}/{uuid4()}-{filename}"
        store[object_key] = (content, "application/pdf")
        return _Stored(object_key, "fakehash", len(content))

    def exists(object_key: str) -> bool:
        return object_key in store

    def stream(object_key: str, chunk_size: int = 1024 * 1024) -> tuple[Any, str]:
        content, content_type = store[object_key]

        def _iter() -> Any:
            for i in range(0, len(content), chunk_size):
                yield content[i : i + chunk_size]

        return _iter(), content_type

    def delete(object_key: str) -> None:
        store.pop(object_key, None)

    monkeypatch.setattr("app.api.routes.documents.upload_document", upload)
    monkeypatch.setattr("app.api.routes.documents.object_exists", exists)
    monkeypatch.setattr("app.api.routes.documents.stream_document_chunks", stream)
    monkeypatch.setattr("app.api.routes.documents.remove_document", delete)
    return store


def _create_document(
    client: TestClient,
    headers: dict[str, str],
    filename: str = "contract.pdf",
    content: bytes = b"pdf-bytes",
) -> dict[str, Any]:
    response = client.post(
        f"{settings.API_V1_STR}/documents/upload",
        headers=headers,
        files={"file": (filename, content, "application/pdf")},
    )
    assert response.status_code == 200
    return response.json()


def test_upload_and_list_documents(
    client: TestClient, normal_user_token_headers: dict[str, str], monkeypatch: Any
) -> None:
    _install_storage_mocks(monkeypatch)
    created = _create_document(client, normal_user_token_headers)
    assert created["file_name"] == "contract.pdf"
    assert created["size_bytes"] == len(b"pdf-bytes")

    response = client.get(
        f"{settings.API_V1_STR}/documents/", headers=normal_user_token_headers
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] >= 1
    assert any(item["id"] == created["id"] for item in payload["data"])


def test_access_link_and_download(
    client: TestClient, normal_user_token_headers: dict[str, str], monkeypatch: Any
) -> None:
    _install_storage_mocks(monkeypatch)
    created = _create_document(client, normal_user_token_headers)

    link_response = client.get(
        f"{settings.API_V1_STR}/documents/{created['id']}/access-link",
        headers=normal_user_token_headers,
    )
    assert link_response.status_code == 200
    link_payload = link_response.json()
    assert link_payload["url"] == f"{settings.API_V1_STR}/documents/{created['id']}/download"

    download_response = client.get(
        f"{settings.API_V1_STR}/documents/{created['id']}/download",
        headers=normal_user_token_headers,
    )
    assert download_response.status_code == 200
    assert download_response.content == b"pdf-bytes"


def test_document_org_level_access(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    superuser_token_headers: dict[str, str],
    monkeypatch: Any,
) -> None:
    _install_storage_mocks(monkeypatch)
    created = _create_document(client, superuser_token_headers)

    allowed = client.get(
        f"{settings.API_V1_STR}/documents/{created['id']}",
        headers=normal_user_token_headers,
    )
    assert allowed.status_code == 200


def test_delete_document(
    client: TestClient, normal_user_token_headers: dict[str, str], monkeypatch: Any
) -> None:
    _install_storage_mocks(monkeypatch)
    created = _create_document(client, normal_user_token_headers)

    delete_response = client.delete(
        f"{settings.API_V1_STR}/documents/{created['id']}",
        headers=normal_user_token_headers,
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Document deleted successfully"
