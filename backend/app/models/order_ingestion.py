import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.base import get_datetime_utc


class OrderIngestionStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class OrderIngestionArtifactKind(str, Enum):
    EML = "eml"
    HTML = "html"
    PO_ATTACHMENT = "po_attachment"


class RejectedCentralReason(str, Enum):
    NOT_ORDER_USER = "not_order_user"
    EXTERNAL = "external"
    INTERNAL_NOT_MAIL_ACCESS = "internal_not_mail_access"


class OrderIngestionRun(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint(
            "central_mailbox_config_id",
            "source_message_id_norm",
            name="uq_order_ingestion_source_msg",
        ),
    )
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    central_mailbox_config_id: uuid.UUID = Field(foreign_key="mailboxconfig.id", index=True)
    source_message_id_norm: str = Field(max_length=512, index=True)
    #: Normalized Message-ID from the order user's mailbox copy (INBOX/Sent search), when found.
    order_user_message_id_norm: str | None = Field(default=None, max_length=512, index=True)
    source_from: str | None = Field(default=None, max_length=1024)
    source_subject: str | None = Field(default=None, max_length=998)
    source_received_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    no_attachment_order: bool = Field(default=False)
    status: str = Field(default=OrderIngestionStatus.IN_PROGRESS.value, max_length=32)
    external_correspondent_from: str | None = Field(default=None, max_length=1024)
    external_correspondent_cc: str | None = Field(default=None, max_length=4096)
    external_correspondent_domain: str | None = Field(default=None, max_length=255)
    external_correspondent_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class OrderUserMessageId(SQLModel, table=True):
    """
    Stores the Message-ID header from the *order user's mailbox copy* of the same
    anchor message, including both the raw header value and our normalized form.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    order_ingestion_id: uuid.UUID = Field(
        foreign_key="orderingestionrun.id",
        index=True,
    )
    order_user_email: str | None = Field(default=None, max_length=255, index=True)
    message_id_raw: str | None = Field(default=None, max_length=512)
    message_id_normalized: str | None = Field(default=None, max_length=512, index=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    __table_args__ = (
        UniqueConstraint(
            "order_ingestion_id",
            "order_user_email",
            name="uq_orderusermessage_order_ingestion_email",
        ),
    )


class OrderIngestionArtifact(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    order_ingestion_id: uuid.UUID = Field(foreign_key="orderingestionrun.id", index=True)
    artifact_kind: str = Field(max_length=32)
    object_key: str = Field(max_length=512, index=True)
    file_name: str = Field(max_length=255)
    mime_type: str | None = Field(default=None, max_length=255)
    size_bytes: int = Field(default=0)


class RejectedCentralSender(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    central_mailbox_config_id: uuid.UUID = Field(foreign_key="mailboxconfig.id", index=True)
    from_address: str = Field(max_length=512, index=True)
    subject: str | None = Field(default=None, max_length=998)
    message_id_norm: str | None = Field(default=None, max_length=512, index=True)
    imap_uid: str = Field(max_length=32)
    rejection_reason: str = Field(max_length=32)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class InternalUnmappedSender(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    central_mailbox_config_id: uuid.UUID = Field(foreign_key="mailboxconfig.id", index=True)
    from_address: str = Field(max_length=512, index=True)
    subject: str | None = Field(default=None, max_length=998)
    message_id_norm: str | None = Field(default=None, max_length=512, index=True)
    imap_uid: str = Field(max_length=32)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class OrderIngestionRunPublic(SQLModel):
    id: uuid.UUID
    central_mailbox_config_id: uuid.UUID
    source_message_id_norm: str
    order_user_message_id_raw: str | None = None
    order_user_message_id_normalized: str | None = None
    order_user_email: str | None = None
    source_from: str | None
    source_subject: str | None
    source_received_at: datetime | None
    no_attachment_order: bool
    status: str
    external_correspondent_from: str | None
    external_correspondent_cc: str | None
    external_correspondent_domain: str | None
    external_correspondent_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None


class OrderIngestionArtifactPublic(SQLModel):
    id: uuid.UUID
    order_ingestion_id: uuid.UUID
    artifact_kind: str
    object_key: str
    file_name: str
    mime_type: str | None
    size_bytes: int


class RejectedCentralSenderPublic(SQLModel):
    id: uuid.UUID
    central_mailbox_config_id: uuid.UUID
    from_address: str
    subject: str | None
    message_id_norm: str | None
    imap_uid: str
    rejection_reason: str
    created_at: datetime | None


class InternalUnmappedSenderPublic(SQLModel):
    id: uuid.UUID
    central_mailbox_config_id: uuid.UUID
    from_address: str
    subject: str | None
    message_id_norm: str | None
    imap_uid: str
    created_at: datetime | None


class OrderIngestionRunDetailPublic(SQLModel):
    run: OrderIngestionRunPublic
    artifacts: list[OrderIngestionArtifactPublic]


class RejectedCentralSendersPublic(SQLModel):
    data: list[RejectedCentralSenderPublic]
    count: int


class InternalUnmappedSendersPublic(SQLModel):
    data: list[InternalUnmappedSenderPublic]
    count: int


class OrderMailboxItemPublic(SQLModel):
    run: OrderIngestionRunPublic
    html_artifact_id: uuid.UUID | None = None
    html_file_name: str | None = None


class OrderMailboxItemsPublic(SQLModel):
    data: list[OrderMailboxItemPublic]
    count: int


class IngestionStorageSummaryPublic(SQLModel):
    runs: int
    artifacts: int
    rejected_central: int
    internal_unmapped: int


class IngestionMessageComprehensivePublic(SQLModel):
    message_id_norm: str
    runs: list[OrderIngestionRunDetailPublic]
    rejected_central: list[RejectedCentralSenderPublic]
    internal_unmapped: list[InternalUnmappedSenderPublic]
