"""Add order-user Message-ID storage table

Stores both raw and normalized RFC 5322 Message-ID values from the order-user
mailbox copy that we used for artifact persistence.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0d3d6f1c2a3b"
down_revision: str | None = "f8a9b0c1d2e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "orderusermessageid",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_ingestion_id", sa.Uuid(), nullable=False),
        sa.Column("message_id_raw", sa.String(length=512), nullable=True),
        sa.Column("message_id_normalized", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["order_ingestion_id"],
            ["orderingestionrun.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_orderusermessageid_message_id_normalized"),
        "orderusermessageid",
        ["message_id_normalized"],
        unique=False,
    )

    op.create_unique_constraint(
        "uq_orderusermessage_order_ingestion",
        "orderusermessageid",
        ["order_ingestion_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_orderusermessage_order_ingestion",
        "orderusermessageid",
        type_="unique",
    )
    op.drop_index(
        op.f("ix_orderusermessageid_message_id_normalized"),
        table_name="orderusermessageid",
    )
    op.drop_table("orderusermessageid")

