import uuid
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from minio.error import S3Error
from sqlmodel import Session, col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.models import (
    Document,
    DocumentAccessLink,
    DocumentPublic,
    DocumentsPublic,
    Message,
)
from app.storage.documents import (
    object_exists,
    remove_document,
    stream_document_chunks,
    upload_document,
)

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def _get_document_for_user(
    session: Session, _current_user: CurrentUser, document_id: uuid.UUID
) -> Document:
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.post("/upload", response_model=DocumentPublic)
async def upload_private_document(
    *, session: SessionDep, current_user: CurrentUser, file: UploadFile = File(...)
) -> Any:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file is not allowed")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large; max upload size is {MAX_UPLOAD_BYTES} bytes",
        )

    stored = upload_document(current_user.id, file.filename or "document.bin", content)
    document = Document(
        uploaded_by_user_id=current_user.id,
        object_key=stored.object_key,
        file_name=file.filename or "document.bin",
        mime_type=file.content_type,
        size_bytes=stored.size_bytes,
        content_hash=stored.content_hash,
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    return document


@router.get("/", response_model=DocumentsPublic)
def list_documents(
    session: SessionDep, _current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> DocumentsPublic:
    base_statement = select(Document)
    count_statement = select(func.count()).select_from(Document)

    count = session.exec(count_statement).one()
    statement = (
        base_statement.order_by(col(Document.created_at).desc()).offset(skip).limit(limit)
    )
    documents = session.exec(statement).all()
    return DocumentsPublic(
        data=[DocumentPublic.model_validate(document) for document in documents], count=count
    )


@router.get("/{document_id}", response_model=DocumentPublic)
def get_document(
    document_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> DocumentPublic:
    return DocumentPublic.model_validate(
        _get_document_for_user(session, current_user, document_id)
    )


@router.get("/{document_id}/access-link", response_model=DocumentAccessLink)
def get_document_access_link(
    document_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> DocumentAccessLink:
    document = _get_document_for_user(session, current_user, document_id)
    if not object_exists(document.object_key):
        raise HTTPException(status_code=404, detail="Stored object not found")
    return DocumentAccessLink(url=f"{settings.API_V1_STR}/documents/{document_id}/download")


@router.get("/{document_id}/download")
def download_document(
    document_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> StreamingResponse:
    document = _get_document_for_user(session, current_user, document_id)
    try:
        stream, content_type = stream_document_chunks(document.object_key)
    except S3Error as exc:
        raise HTTPException(status_code=404, detail="Stored object not found") from exc

    media_type = content_type or document.mime_type or "application/octet-stream"
    response = StreamingResponse(stream, media_type=media_type)
    response.headers["Content-Disposition"] = f'inline; filename="{document.file_name}"'
    return response


@router.delete("/{document_id}", response_model=Message)
def delete_document(
    document_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> Message:
    document = _get_document_for_user(session, current_user, document_id)
    remove_document(document.object_key)
    session.delete(document)
    session.commit()
    return Message(message="Document deleted successfully")
