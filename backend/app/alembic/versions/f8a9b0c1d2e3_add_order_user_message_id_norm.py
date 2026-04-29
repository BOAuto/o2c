"""add order_user_message_id_norm to orderingestionrun

Revision ID: f8a9b0c1d2e3
Revises: e6f7a8b9c0d1
Create Date: 2026-04-29 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f8a9b0c1d2e3"
down_revision: str | None = "e6f7a8b9c0d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "orderingestionrun",
        sa.Column("order_user_message_id_norm", sa.String(length=512), nullable=True),
    )
    op.create_index(
        op.f("ix_orderingestionrun_order_user_message_id_norm"),
        "orderingestionrun",
        ["order_user_message_id_norm"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_orderingestionrun_order_user_message_id_norm"),
        table_name="orderingestionrun",
    )
    op.drop_column("orderingestionrun", "order_user_message_id_norm")
