"""merge mail access into mailboxconfig; drop usermailaccess

Revision ID: f7g8h9i0j1k2
Revises: e5f6a7b8c9d0
Create Date: 2026-04-28 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f7g8h9i0j1k2"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "mailboxconfig",
        sa.Column("mail_access_type", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "mailboxconfig",
        sa.Column("user_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        op.f("ix_mailboxconfig_user_id"),
        "mailboxconfig",
        ["user_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_mailboxconfig_user_id",
        "mailboxconfig",
        ["user_id"],
    )
    op.create_foreign_key(
        "fk_mailboxconfig_user_id_user",
        "mailboxconfig",
        "user",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.execute(
        sa.text(
            """
            UPDATE mailboxconfig AS m
            SET
                mail_access_type = uma.access_type,
                user_id = uma.user_id
            FROM usermailaccess AS uma
            WHERE m.id = uma.mailbox_config_id
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE mailboxconfig AS m
            SET user_id = u.id
            FROM "user" AS u
            WHERE m.scope_type = 'userLinked'
              AND m.user_id IS NULL
              AND m.email = u.email
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE mailboxconfig
            SET mail_access_type = 'OrderUser'
            WHERE scope_type = 'userLinked'
              AND mail_access_type IS NULL
              AND user_id IS NOT NULL
            """
        )
    )

    op.drop_table("usermailaccess")


def downgrade() -> None:
    op.create_table(
        "usermailaccess",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("mailbox_config_id", sa.Uuid(), nullable=False),
        sa.Column("access_type", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["mailbox_config_id"],
            ["mailboxconfig.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_user_mail_access_user"),
    )
    op.create_index(
        op.f("ix_usermailaccess_user_id"),
        "usermailaccess",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_usermailaccess_mailbox_config_id"),
        "usermailaccess",
        ["mailbox_config_id"],
        unique=False,
    )

    op.execute(
        sa.text(
            """
            INSERT INTO usermailaccess (
                id, user_id, mailbox_config_id, access_type, is_active, created_at, updated_at
            )
            SELECT
                gen_random_uuid(),
                m.user_id,
                m.id,
                m.mail_access_type,
                m.is_active,
                m.created_at,
                m.updated_at
            FROM mailboxconfig AS m
            WHERE m.scope_type = 'userLinked'
              AND m.user_id IS NOT NULL
              AND m.mail_access_type IS NOT NULL
            """
        )
    )

    op.drop_constraint("fk_mailboxconfig_user_id_user", "mailboxconfig", type_="foreignkey")
    op.drop_constraint("uq_mailboxconfig_user_id", "mailboxconfig", type_="unique")
    op.drop_index(op.f("ix_mailboxconfig_user_id"), table_name="mailboxconfig")
    op.drop_column("mailboxconfig", "user_id")
    op.drop_column("mailboxconfig", "mail_access_type")
