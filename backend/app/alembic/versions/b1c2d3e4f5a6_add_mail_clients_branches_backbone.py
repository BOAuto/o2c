"""add mail clients branches backbone

Revision ID: b1c2d3e4f5a6
Revises: 7db0a1e0a0b2
Create Date: 2026-04-27 14:30:00.000000
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: str | None = "7db0a1e0a0b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mailboxconfig",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scope_type", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("imap_host", sa.String(length=255), nullable=False),
        sa.Column("imap_port", sa.Integer(), nullable=False),
        sa.Column("imap_ssl", sa.Boolean(), nullable=False),
        sa.Column("smtp_host", sa.String(length=255), nullable=False),
        sa.Column("smtp_port", sa.Integer(), nullable=False),
        sa.Column("smtp_ssl", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("encrypted_app_password", sa.String(length=1024), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope_type", "email", name="uq_mailbox_scope_email"),
    )
    op.create_index(op.f("ix_mailboxconfig_email"), "mailboxconfig", ["email"], unique=False)

    op.create_table(
        "usermailaccess",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("mailbox_config_id", sa.Uuid(), nullable=False),
        sa.Column("access_type", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["mailbox_config_id"], ["mailboxconfig.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_user_mail_access_user"),
    )
    op.create_index(op.f("ix_usermailaccess_user_id"), "usermailaccess", ["user_id"], unique=False)
    op.create_index(
        op.f("ix_usermailaccess_mailbox_config_id"),
        "usermailaccess",
        ["mailbox_config_id"],
        unique=False,
    )

    op.create_table(
        "company",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("payment_term", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_company_name"), "company", ["name"], unique=False)

    op.create_table(
        "companyemaildomain",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("domain_pattern", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "domain_pattern", name="uq_company_domain_pattern"),
    )
    op.create_index(
        op.f("ix_companyemaildomain_company_id"), "companyemaildomain", ["company_id"], unique=False
    )

    op.create_table(
        "clientratecontract",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("sku", sa.String(length=128), nullable=False),
        sa.Column("agreed_rate", sa.Numeric(12, 2), nullable=False),
        sa.Column("gst_rate", sa.Numeric(5, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "sku", name="uq_client_contract_company_sku"),
    )
    op.create_index(
        op.f("ix_clientratecontract_company_id"), "clientratecontract", ["company_id"], unique=False
    )

    op.create_table(
        "validationrule",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("definition_json", sa.String(length=5000), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_index(op.f("ix_validationrule_key"), "validationrule", ["key"], unique=False)

    op.create_table(
        "companyvalidationassignment",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("validation_rule_id", sa.Uuid(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["validation_rule_id"], ["validationrule.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id", "validation_rule_id", name="uq_company_validation_assignment"
        ),
    )
    op.create_index(
        op.f("ix_companyvalidationassignment_company_id"),
        "companyvalidationassignment",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_companyvalidationassignment_validation_rule_id"),
        "companyvalidationassignment",
        ["validation_rule_id"],
        unique=False,
    )

    op.create_table(
        "branch",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("branch_gstin", sa.String(length=15), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("branch_gstin"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_branch_name"), "branch", ["name"], unique=False)
    op.create_index(op.f("ix_branch_slug"), "branch", ["slug"], unique=False)
    op.create_index(op.f("ix_branch_branch_gstin"), "branch", ["branch_gstin"], unique=False)

    op.create_table(
        "gststatecode",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=2), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_gststatecode_code"), "gststatecode", ["code"], unique=False)

    op.create_table(
        "branchgststate",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("gst_state_code_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branch.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["gst_state_code_id"], ["gststatecode.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("branch_id", "gst_state_code_id", name="uq_branch_gst_state"),
    )
    op.create_index(op.f("ix_branchgststate_branch_id"), "branchgststate", ["branch_id"], unique=False)
    op.create_index(
        op.f("ix_branchgststate_gst_state_code_id"),
        "branchgststate",
        ["gst_state_code_id"],
        unique=False,
    )

    state_rows = [
        ("01", "Jammu And Kashmir"),
        ("02", "Himachal Pradesh"),
        ("03", "Punjab"),
        ("04", "Chandigarh"),
        ("05", "Uttarakhand"),
        ("06", "Haryana"),
        ("07", "Delhi"),
        ("08", "Rajasthan"),
        ("09", "Uttar Pradesh"),
        ("10", "Bihar"),
        ("11", "Sikkim"),
        ("12", "Arunachal Pradesh"),
        ("13", "Nagaland"),
        ("14", "Manipur"),
        ("15", "Mizoram"),
        ("16", "Tripura"),
        ("17", "Meghalaya"),
        ("18", "Assam"),
        ("19", "West Bengal"),
        ("20", "Jharkhand"),
        ("21", "Orissa"),
        ("22", "Chhattisgarh"),
        ("23", "Madhya Pradesh"),
        ("24", "Gujarat"),
        ("26", "Dadra And Nagar Haveli & Daman And Diu"),
        ("27", "Maharashtra"),
        ("29", "Karnataka"),
        ("30", "Goa"),
        ("31", "Lakshadweep"),
        ("32", "Kerala"),
        ("33", "Tamil Nadu"),
        ("34", "Puducherry"),
        ("35", "Andaman And Nicobar"),
        ("36", "Telangana"),
        ("37", "Andhra Pradesh"),
        ("38", "Ladakh"),
        ("97", "Other Territory"),
        ("99", "Other Country"),
    ]
    table = sa.table(
        "gststatecode",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("description", sa.String()),
    )
    op.bulk_insert(
        table,
        [
            {"id": uuid.uuid4(), "code": code, "description": description}
            for code, description in state_rows
        ],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_branchgststate_gst_state_code_id"), table_name="branchgststate")
    op.drop_index(op.f("ix_branchgststate_branch_id"), table_name="branchgststate")
    op.drop_table("branchgststate")
    op.drop_index(op.f("ix_gststatecode_code"), table_name="gststatecode")
    op.drop_table("gststatecode")
    op.drop_index(op.f("ix_branch_branch_gstin"), table_name="branch")
    op.drop_index(op.f("ix_branch_slug"), table_name="branch")
    op.drop_index(op.f("ix_branch_name"), table_name="branch")
    op.drop_table("branch")
    op.drop_index(
        op.f("ix_companyvalidationassignment_validation_rule_id"),
        table_name="companyvalidationassignment",
    )
    op.drop_index(
        op.f("ix_companyvalidationassignment_company_id"), table_name="companyvalidationassignment"
    )
    op.drop_table("companyvalidationassignment")
    op.drop_index(op.f("ix_validationrule_key"), table_name="validationrule")
    op.drop_table("validationrule")
    op.drop_index(op.f("ix_clientratecontract_company_id"), table_name="clientratecontract")
    op.drop_table("clientratecontract")
    op.drop_index(op.f("ix_companyemaildomain_company_id"), table_name="companyemaildomain")
    op.drop_table("companyemaildomain")
    op.drop_index(op.f("ix_company_name"), table_name="company")
    op.drop_table("company")
    op.drop_index(op.f("ix_usermailaccess_mailbox_config_id"), table_name="usermailaccess")
    op.drop_index(op.f("ix_usermailaccess_user_id"), table_name="usermailaccess")
    op.drop_table("usermailaccess")
    op.drop_index(op.f("ix_mailboxconfig_email"), table_name="mailboxconfig")
    op.drop_table("mailboxconfig")
