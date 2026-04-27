import uuid
from datetime import datetime

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel

from app.models.base import get_datetime_utc


class DocumentBase(SQLModel):
    file_name: str = Field(max_length=255)
    mime_type: str | None = Field(default=None, max_length=255)


class Document(DocumentBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    uploaded_by_user_id: uuid.UUID = Field(index=True, nullable=False)
    object_key: str = Field(unique=True, index=True, max_length=512)
    size_bytes: int
    content_hash: str = Field(max_length=64)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class DocumentPublic(DocumentBase):
    id: uuid.UUID
    uploaded_by_user_id: uuid.UUID
    size_bytes: int
    created_at: datetime | None = None


class DocumentsPublic(SQLModel):
    data: list[DocumentPublic]
    count: int


class DocumentAccessLink(SQLModel):
    url: str
