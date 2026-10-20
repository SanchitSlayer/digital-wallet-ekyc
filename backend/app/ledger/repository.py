import uuid
from collections.abc import Iterator

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.ledger.models import LedgerEntry
from app.wallet.models import Transfer, Wallet

# Any fixed number works; every transaction that appends to the ledger asks Postgres for this same lock.
_LEDGER_APPEND_LOCK_ID = 7_202_610


def lock_ledger_for_append(db: Session) -> None:
    # Each entry stores the previous entry's hash, so two transactions appending at the same moment would both
    # chain onto the same predecessor. This transaction-scoped lock makes appends take turns; it is released
    # automatically on commit or rollback.
    db.execute(select(func.pg_advisory_xact_lock(_LEDGER_APPEND_LOCK_ID)))


def get_last_entry(db: Session) -> LedgerEntry | None:
    return db.scalar(select(LedgerEntry).order_by(LedgerEntry.id.desc()).limit(1))


def add_entry(db: Session, entry: LedgerEntry) -> LedgerEntry:
    db.add(entry)
    db.flush()
    return entry


def iterate_entries_in_order(db: Session) -> Iterator[LedgerEntry]:
    # yield_per streams entries in batches, so verifying a large ledger never loads every row into memory at once.
    yield from db.scalars(select(LedgerEntry).order_by(LedgerEntry.id).execution_options(yield_per=500))


def list_entries_for_wallet(db: Session, wallet_id: uuid.UUID) -> list[LedgerEntry]:
    return list(
        db.scalars(
            select(LedgerEntry)
            .where(LedgerEntry.wallet_id == wallet_id)
            .options(
                selectinload(LedgerEntry.transfer).selectinload(Transfer.sender_wallet).selectinload(Wallet.user),
                selectinload(LedgerEntry.transfer).selectinload(Transfer.receiver_wallet).selectinload(Wallet.user),
            )
            .order_by(LedgerEntry.id.desc())
        )
    )
