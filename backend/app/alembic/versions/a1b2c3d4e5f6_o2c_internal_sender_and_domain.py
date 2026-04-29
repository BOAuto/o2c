"""add o2c internal sender reporting and external domain

Revision ID: a1b2c3d4e5f6
Revises: f7g8h9i0j1k2
Create Date: 2026-04-28 12:05:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "f7g8h9i0j1k2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "orderingestionrun",
        sa.Column("external_correspondent_domain", sa.String(length=255), nullable=True),
    )

    op.create_table(
        "internalunmappedsender",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("central_mailbox_config_id", sa.Uuid(), nullable=False),
        sa.Column("from_address", sa.String(length=512), nullable=False),
        sa.Column("subject", sa.String(length=998), nullable=True),
        sa.Column("message_id_norm", sa.String(length=512), nullable=True),
        sa.Column("imap_uid", sa.String(length=32), nullable=False),
        sa.Column("temporal_workflow_id", sa.String(length=255), nullable=True),
        sa.Column("temporal_run_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["central_mailbox_config_id"],
            ["mailboxconfig.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "central_mailbox_config_id",
            "imap_uid",
            name="uq_internal_unmapped_sender_uid",
        ),
    )
    op.create_index(
        op.f("ix_internalunmappedsender_central_mailbox_config_id"),
        "internalunmappedsender",
        ["central_mailbox_config_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_internalunmappedsender_from_address"),
        "internalunmappedsender",
        ["from_address"],
        unique=False,
    )
    op.create_index(
        op.f("ix_internalunmappedsender_message_id_norm"),
        "internalunmappedsender",
        ["message_id_norm"],
        unique=False,
    )

def downgrade() -> None:
    op.drop_index(
        op.f("ix_internalunmappedsender_message_id_norm"),
        table_name="internalunmappedsender",
    )
    op.drop_index(
        op.f("ix_internalunmappedsender_from_address"),
        table_name="internalunmappedsender",
    )
    op.drop_index(
        op.f("ix_internalunmappedsender_central_mailbox_config_id"),
        table_name="internalunmappedsender",
    )
    op.drop_table("internalunmappedsender")

    op.drop_column("orderingestionrun", "external_correspondent_domain")
