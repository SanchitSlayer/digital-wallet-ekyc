"""create kyc submissions

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-20 20:48:09.977394
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "kyc_submissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "VERIFIED",
                "REJECTED",
                name="kyc_status",
                native_enum=False,
                create_constraint=True,
                length=10,
            ),
            nullable=False,
        ),
        sa.Column("image_filename", sa.String(length=64), nullable=False),
        sa.Column("ocr_text", sa.Text(), nullable=False),
        sa.Column("id_number", sa.String(length=12), nullable=True),
        sa.Column("extracted_name", sa.String(length=255), nullable=True),
        sa.Column("name_match_score", sa.Float(), nullable=False),
        sa.Column("rejection_reason", sa.String(length=500), nullable=True),
        sa.Column("reviewed_by_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["reviewed_by_id"], ["users.id"], name=op.f("fk_kyc_submissions_reviewed_by_id_users")
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_kyc_submissions_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kyc_submissions")),
    )
    op.create_index(op.f("ix_kyc_submissions_user_id"), "kyc_submissions", ["user_id"], unique=False)
    op.create_index(
        "uq_kyc_submissions_one_active_per_user",
        "kyc_submissions",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDING', 'VERIFIED')"),
    )


def downgrade() -> None:
    op.drop_index("uq_kyc_submissions_one_active_per_user", table_name="kyc_submissions")
    op.drop_index(op.f("ix_kyc_submissions_user_id"), table_name="kyc_submissions")
    op.drop_table("kyc_submissions")
