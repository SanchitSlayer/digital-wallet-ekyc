"""create wallets transfers and ledger

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-20 21:37:53.053284
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "wallets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("balance_paise", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("balance_paise >= 0", name=op.f("ck_wallets_balance_not_negative")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_wallets_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_wallets")),
        sa.UniqueConstraint("user_id", name=op.f("uq_wallets_user_id")),
    )
    op.create_table(
        "transfers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sender_wallet_id", sa.Uuid(), nullable=False),
        sa.Column("receiver_wallet_id", sa.Uuid(), nullable=False),
        sa.Column("amount_paise", sa.BigInteger(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("amount_paise > 0", name=op.f("ck_transfers_amount_positive")),
        sa.CheckConstraint("sender_wallet_id <> receiver_wallet_id", name=op.f("ck_transfers_distinct_wallets")),
        sa.ForeignKeyConstraint(
            ["receiver_wallet_id"], ["wallets.id"], name=op.f("fk_transfers_receiver_wallet_id_wallets")
        ),
        sa.ForeignKeyConstraint(
            ["sender_wallet_id"], ["wallets.id"], name=op.f("fk_transfers_sender_wallet_id_wallets")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transfers")),
        sa.UniqueConstraint("sender_wallet_id", "idempotency_key", name="uq_transfers_sender_idempotency_key"),
    )
    op.create_index(op.f("ix_transfers_receiver_wallet_id"), "transfers", ["receiver_wallet_id"], unique=False)
    op.create_index(op.f("ix_transfers_sender_wallet_id"), "transfers", ["sender_wallet_id"], unique=False)
    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("wallet_id", sa.Uuid(), nullable=False),
        sa.Column("transfer_id", sa.Uuid(), nullable=True),
        sa.Column(
            "entry_type",
            sa.Enum(
                "TOP_UP",
                "TRANSFER_DEBIT",
                "TRANSFER_CREDIT",
                name="ledger_entry_type",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("amount_paise", sa.BigInteger(), nullable=False),
        sa.Column("balance_after_paise", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("previous_hash", sa.String(length=64), nullable=False),
        sa.Column("entry_hash", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["transfer_id"], ["transfers.id"], name=op.f("fk_ledger_entries_transfer_id_transfers")
        ),
        sa.ForeignKeyConstraint(["wallet_id"], ["wallets.id"], name=op.f("fk_ledger_entries_wallet_id_wallets")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ledger_entries")),
        sa.UniqueConstraint("entry_hash", name=op.f("uq_ledger_entries_entry_hash")),
    )
    op.create_index(op.f("ix_ledger_entries_wallet_id"), "ledger_entries", ["wallet_id"], unique=False)

    # The database itself refuses to change or remove ledger rows, so not even a bug in the app or a careless
    # manual query can rewrite history; corrections must be new entries.
    op.execute(
        """
        CREATE FUNCTION ledger_entries_reject_changes() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'ledger_entries is append-only: % is not allowed', TG_OP;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER ledger_entries_append_only
        BEFORE UPDATE OR DELETE ON ledger_entries
        FOR EACH ROW EXECUTE FUNCTION ledger_entries_reject_changes()
        """
    )

    # Users verified during Phase 1 already passed KYC, so they get the wallet that approval now creates.
    op.execute(
        """
        INSERT INTO wallets (id, user_id, balance_paise)
        SELECT gen_random_uuid(), user_id, 0 FROM kyc_submissions WHERE status = 'VERIFIED'
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER ledger_entries_append_only ON ledger_entries")
    op.execute("DROP FUNCTION ledger_entries_reject_changes()")
    op.drop_index(op.f("ix_ledger_entries_wallet_id"), table_name="ledger_entries")
    op.drop_table("ledger_entries")
    op.drop_index(op.f("ix_transfers_sender_wallet_id"), table_name="transfers")
    op.drop_index(op.f("ix_transfers_receiver_wallet_id"), table_name="transfers")
    op.drop_table("transfers")
    op.drop_table("wallets")
