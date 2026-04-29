import uuid
from datetime import datetime
from enum import Enum

from pydantic import EmailStr
from sqlalchemy import DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.base import get_datetime_utc


class MailAccessType(str, Enum):
    ORDER_USER = "OrderUser"
    ORDER_INTERNAL_USER = "OrderInternalUser"


class MailboxScopeType(str, Enum):
    CENTRAL_ORDER_MAIL = "centralOrderMail"
    USER_LINKED = "userLinked"


class MailboxConfigBase(SQLModel):
    scope_type: MailboxScopeType
    email: EmailStr = Field(max_length=255)
    imap_host: str = Field(default="imap.mail.yahoo.com", max_length=255)
    imap_port: int = 993
    imap_ssl: bool = True
    smtp_host: str = Field(default="smtp.bizmail.yahoo.com", max_length=255)
    smtp_port: int = 465
    smtp_ssl: bool = True
    ingestion_retrieval_period: str | None = Field(default=None, max_length=64)
    is_active: bool = True


class MailboxConfigCreate(SQLModel):
    email: EmailStr = Field(max_length=255)
    app_password: str = Field(min_length=8, max_length=255)
    ingestion_retrieval_period: str | None = Field(default=None, max_length=64)


class MailboxConfigUpdate(SQLModel):
    email: EmailStr | None = Field(default=None, max_length=255)
    app_password: str | None = Field(default=None, min_length=8, max_length=255)
    ingestion_retrieval_period: str | None = Field(default=None, max_length=64)
    is_active: bool | None = None


class MailboxConfig(MailboxConfigBase, table=True):
    __table_args__ = (
        UniqueConstraint("scope_type", "email", name="uq_mailbox_scope_email"),
        UniqueConstraint("user_id", name="uq_mailboxconfig_user_id"),
    )
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    mail_access_type: MailAccessType | None = Field(default=None, max_length=255)
    user_id: uuid.UUID | None = Field(default=None, foreign_key="user.id", index=True)
    encrypted_app_password: str = Field(max_length=1024)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class MailboxConfigPublic(MailboxConfigBase):
    id: uuid.UUID
    mail_access_type: MailAccessType | None = None
    user_id: uuid.UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserMailAccessBase(SQLModel):
    user_id: uuid.UUID = Field(index=True)
    mailbox_config_id: uuid.UUID = Field(index=True)
    access_type: MailAccessType
    is_active: bool = True


class UserMailAccessCreate(SQLModel):
    user_id: uuid.UUID
    access_type: MailAccessType
    app_password: str = Field(min_length=8, max_length=255)


class UserMailAccessUpdate(SQLModel):
    access_type: MailAccessType | None = None
    app_password: str | None = Field(default=None, min_length=8, max_length=255)
    is_active: bool | None = None


class UserMailAccessPublic(UserMailAccessBase):
    id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


def user_mail_access_public_from_mailbox(m: MailboxConfig) -> UserMailAccessPublic:
    if m.user_id is None or m.mail_access_type is None:
        raise ValueError("mailbox is not a user-linked mail access row")
    return UserMailAccessPublic(
        id=m.id,
        user_id=m.user_id,
        mailbox_config_id=m.id,
        access_type=m.mail_access_type,
        is_active=m.is_active,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class MailboxConfigsPublic(SQLModel):
    data: list[MailboxConfigPublic]
    count: int


class UserMailAccessesPublic(SQLModel):
    data: list[UserMailAccessPublic]
    count: int
