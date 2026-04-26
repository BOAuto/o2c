"""Make documents org-scoped and keep uploader as audit field

Revision ID: 7db0a1e0a0b2
Revises: c4c097f7f8b1
Create Date: 2026-04-26 10:28:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7db0a1e0a0b2"
down_revision = "c4c097f7f8b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("document_owner_id_fkey", "document", type_="foreignkey")
    op.drop_index(op.f("ix_document_owner_id"), table_name="document")
    op.alter_column("document", "owner_id", new_column_name="uploaded_by_user_id")
    op.create_index(
        op.f("ix_document_uploaded_by_user_id"),
        "document",
        ["uploaded_by_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_document_uploaded_by_user_id"), table_name="document")
    op.alter_column("document", "uploaded_by_user_id", new_column_name="owner_id")
    op.create_index(op.f("ix_document_owner_id"), "document", ["owner_id"], unique=False)
    op.create_foreign_key(
        "document_owner_id_fkey",
        "document",
        "user",
        ["owner_id"],
        ["id"],
        ondelete="CASCADE",
    )
