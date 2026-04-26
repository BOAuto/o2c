"""Add documents table for private object metadata

Revision ID: c4c097f7f8b1
Revises: fe56fa70289e
Create Date: 2026-04-25 23:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c4c097f7f8b1"
down_revision = "fe56fa70289e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document",
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_document_object_key"), "document", ["object_key"], unique=True)
    op.create_index(op.f("ix_document_owner_id"), "document", ["owner_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_document_owner_id"), table_name="document")
    op.drop_index(op.f("ix_document_object_key"), table_name="document")
    op.drop_table("document")
