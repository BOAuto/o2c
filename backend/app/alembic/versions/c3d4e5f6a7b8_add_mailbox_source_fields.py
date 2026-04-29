"""add source mailbox fields for ingestion runs

Revision ID: d4e5f6a7b8c1
Revises: b2c3d4e5f6a7
Create Date: 2026-04-28 16:55:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c1"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("orderingestionrun", sa.Column("source_from", sa.String(length=1024), nullable=True))
    op.add_column("orderingestionrun", sa.Column("source_subject", sa.String(length=998), nullable=True))
    op.add_column(
        "orderingestionrun",
        sa.Column("source_received_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("orderingestionrun", "source_received_at")
    op.drop_column("orderingestionrun", "source_subject")
    op.drop_column("orderingestionrun", "source_from")
