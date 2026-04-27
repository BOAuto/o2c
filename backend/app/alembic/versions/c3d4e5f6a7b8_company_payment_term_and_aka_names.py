"""add company payment_term integer and aka_names

Revision ID: c3d4e5f6a7b8
Revises: b1c2d3e4f5a6
Create Date: 2026-04-27 16:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b1c2d3e4f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "company",
        sa.Column("aka_names", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
    )
    op.alter_column("company", "aka_names", server_default=None)

    op.alter_column(
        "company",
        "payment_term",
        existing_type=sa.String(length=255),
        type_=sa.Integer(),
        existing_nullable=True,
        postgresql_using=(
            "CASE "
            "WHEN payment_term ~ '^[0-9]+$' THEN payment_term::integer "
            "ELSE NULL "
            "END"
        ),
    )


def downgrade() -> None:
    op.alter_column(
        "company",
        "payment_term",
        existing_type=sa.Integer(),
        type_=sa.String(length=255),
        existing_nullable=True,
        postgresql_using="payment_term::text",
    )
    op.drop_column("company", "aka_names")
