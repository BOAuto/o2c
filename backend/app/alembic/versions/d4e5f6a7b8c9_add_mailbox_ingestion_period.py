"""add mailbox ingestion retrieval period

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-27 16:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "mailboxconfig",
        sa.Column("ingestion_retrieval_period", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("mailboxconfig", "ingestion_retrieval_period")
