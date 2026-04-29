"""Add order_user_email to orderusermessageid

So we can associate the stored Message-ID headers with the specific order-user
mailbox address that we extracted them from.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "1b2c3d4e5f6"
down_revision: str | None = "0d3d6f1c2a3b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "orderusermessageid",
        # Keep nullable for safety: if there are already rows created before this
        # column existed, we don't want the migration to fail.
        sa.Column("order_user_email", sa.String(length=255), nullable=True),
    )

    # Replace old uniqueness (order_ingestion_id only) with
    # (order_ingestion_id, order_user_email).
    #
    # Existing migrations may have created this constraint.
    op.drop_constraint(
        "uq_orderusermessage_order_ingestion",
        "orderusermessageid",
        type_="unique",
    )

    op.create_unique_constraint(
        "uq_orderusermessage_order_ingestion_email",
        "orderusermessageid",
        ["order_ingestion_id", "order_user_email"],
    )

    op.create_index(
        op.f("ix_orderusermessageid_order_user_email"),
        "orderusermessageid",
        ["order_user_email"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_orderusermessageid_order_user_email"),
        table_name="orderusermessageid",
    )

    op.drop_constraint(
        "uq_orderusermessage_order_ingestion_email",
        "orderusermessageid",
        type_="unique",
    )

    op.create_unique_constraint(
        "uq_orderusermessage_order_ingestion",
        "orderusermessageid",
        ["order_ingestion_id"],
    )

    op.drop_column("orderusermessageid", "order_user_email")

