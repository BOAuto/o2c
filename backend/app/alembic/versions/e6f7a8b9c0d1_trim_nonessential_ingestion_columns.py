"""trim non-essential ingestion columns

Revision ID: e6f7a8b9c0d1
Revises: d4e5f6a7b8c1
Create Date: 2026-04-28 20:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e6f7a8b9c0d1"
down_revision: str | None = "d4e5f6a7b8c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("orderingestionrun", "source_imap_uid")
    op.drop_column("orderingestionrun", "temporal_workflow_id")
    op.drop_column("orderingestionrun", "temporal_run_id")
    op.drop_column("orderingestionrun", "error_message")

    op.drop_column("rejectedcentralsender", "temporal_workflow_id")
    op.drop_column("rejectedcentralsender", "temporal_run_id")

    op.drop_column("internalunmappedsender", "temporal_workflow_id")
    op.drop_column("internalunmappedsender", "temporal_run_id")


def downgrade() -> None:
    op.add_column(
        "internalunmappedsender",
        sa.Column("temporal_run_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "internalunmappedsender",
        sa.Column("temporal_workflow_id", sa.String(length=255), nullable=True),
    )

    op.add_column(
        "rejectedcentralsender",
        sa.Column("temporal_run_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "rejectedcentralsender",
        sa.Column("temporal_workflow_id", sa.String(length=255), nullable=True),
    )

    op.add_column(
        "orderingestionrun",
        sa.Column("error_message", sa.String(length=2048), nullable=True),
    )
    op.add_column(
        "orderingestionrun",
        sa.Column("temporal_run_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "orderingestionrun",
        sa.Column("temporal_workflow_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "orderingestionrun",
        sa.Column("source_imap_uid", sa.String(length=32), nullable=True),
    )
