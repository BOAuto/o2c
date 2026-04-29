"""add order ingestion and rejected central sender tables

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-27 20:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "orderingestionrun",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("central_mailbox_config_id", sa.Uuid(), nullable=False),
        sa.Column("source_message_id_norm", sa.String(length=512), nullable=False),
        sa.Column("source_imap_uid", sa.String(length=32), nullable=False),
        sa.Column("no_attachment_order", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("external_correspondent_from", sa.String(length=1024), nullable=True),
        sa.Column("external_correspondent_cc", sa.String(length=4096), nullable=True),
        sa.Column("temporal_workflow_id", sa.String(length=255), nullable=True),
        sa.Column("temporal_run_id", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.String(length=2048), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["central_mailbox_config_id"],
            ["mailboxconfig.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "central_mailbox_config_id",
            "source_message_id_norm",
            name="uq_order_ingestion_source_msg",
        ),
    )
    op.create_index(
        op.f("ix_orderingestionrun_central_mailbox_config_id"),
        "orderingestionrun",
        ["central_mailbox_config_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_orderingestionrun_source_message_id_norm"),
        "orderingestionrun",
        ["source_message_id_norm"],
        unique=False,
    )

    op.create_table(
        "orderingestionartifact",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_ingestion_id", sa.Uuid(), nullable=False),
        sa.Column("artifact_kind", sa.String(length=32), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["order_ingestion_id"],
            ["orderingestionrun.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_orderingestionartifact_object_key"),
        "orderingestionartifact",
        ["object_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_orderingestionartifact_order_ingestion_id"),
        "orderingestionartifact",
        ["order_ingestion_id"],
        unique=False,
    )

    op.create_table(
        "rejectedcentralsender",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("central_mailbox_config_id", sa.Uuid(), nullable=False),
        sa.Column("from_address", sa.String(length=512), nullable=False),
        sa.Column("subject", sa.String(length=998), nullable=True),
        sa.Column("message_id_norm", sa.String(length=512), nullable=True),
        sa.Column("imap_uid", sa.String(length=32), nullable=False),
        sa.Column("rejection_reason", sa.String(length=32), nullable=False),
        sa.Column("temporal_workflow_id", sa.String(length=255), nullable=True),
        sa.Column("temporal_run_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["central_mailbox_config_id"],
            ["mailboxconfig.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_rejectedcentralsender_central_mailbox_config_id"),
        "rejectedcentralsender",
        ["central_mailbox_config_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rejectedcentralsender_from_address"),
        "rejectedcentralsender",
        ["from_address"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rejectedcentralsender_message_id_norm"),
        "rejectedcentralsender",
        ["message_id_norm"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_rejectedcentralsender_message_id_norm"), table_name="rejectedcentralsender")
    op.drop_index(op.f("ix_rejectedcentralsender_from_address"), table_name="rejectedcentralsender")
    op.drop_index(
        op.f("ix_rejectedcentralsender_central_mailbox_config_id"),
        table_name="rejectedcentralsender",
    )
    op.drop_table("rejectedcentralsender")

    op.drop_index(
        op.f("ix_orderingestionartifact_order_ingestion_id"),
        table_name="orderingestionartifact",
    )
    op.drop_index(op.f("ix_orderingestionartifact_object_key"), table_name="orderingestionartifact")
    op.drop_table("orderingestionartifact")

    op.drop_index(
        op.f("ix_orderingestionrun_source_message_id_norm"),
        table_name="orderingestionrun",
    )
    op.drop_index(
        op.f("ix_orderingestionrun_central_mailbox_config_id"),
        table_name="orderingestionrun",
    )
    op.drop_table("orderingestionrun")
