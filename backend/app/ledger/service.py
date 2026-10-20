import hashlib
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.ledger import repository
from app.ledger.models import LedgerEntry, LedgerEntryType
from app.ledger.schemas import LedgerVerificationResponse
from app.wallet.models import Wallet

GENESIS_HASH = "0" * 64


def compute_entry_hash(entry: LedgerEntry) -> str:
    # Canonical JSON (sorted keys, no spaces, UTC timestamps) makes the same data always produce the same bytes,
    # so a hash recomputed later matches the one stored at insert time unless something was changed.
    canonical = json.dumps(
        {
            "wallet_id": str(entry.wallet_id),
            "transfer_id": str(entry.transfer_id) if entry.transfer_id else None,
            "entry_type": entry.entry_type.value,
            "amount_paise": entry.amount_paise,
            "balance_after_paise": entry.balance_after_paise,
            "created_at": entry.created_at.astimezone(UTC).isoformat(),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(f"{entry.previous_hash}{canonical}".encode()).hexdigest()


def append_entry(
    db: Session, *, wallet: Wallet, transfer_id: uuid.UUID | None, entry_type: LedgerEntryType, amount_paise: int
) -> LedgerEntry:
    repository.lock_ledger_for_append(db)
    previous = repository.get_last_entry(db)
    entry = LedgerEntry(
        wallet_id=wallet.id,
        transfer_id=transfer_id,
        entry_type=entry_type,
        amount_paise=amount_paise,
        balance_after_paise=wallet.balance_paise,
        created_at=datetime.now(UTC),
        previous_hash=previous.entry_hash if previous else GENESIS_HASH,
    )
    entry.entry_hash = compute_entry_hash(entry)
    return repository.add_entry(db, entry)


def list_wallet_entries(db: Session, wallet: Wallet) -> list[LedgerEntry]:
    return repository.list_entries_for_wallet(db, wallet.id)


def verify_chain(db: Session) -> LedgerVerificationResponse:
    expected_previous_hash = GENESIS_HASH
    entries_checked = 0
    for entry in repository.iterate_entries_in_order(db):
        entries_checked += 1
        if entry.previous_hash != expected_previous_hash:
            return LedgerVerificationResponse.broken(
                entries_checked, entry.id, "its previous_hash does not match the hash of the entry before it"
            )
        if compute_entry_hash(entry) != entry.entry_hash:
            return LedgerVerificationResponse.broken(
                entries_checked, entry.id, "its stored hash does not match its data, so the entry was modified"
            )
        expected_previous_hash = entry.entry_hash
    return LedgerVerificationResponse(
        intact=True, entries_checked=entries_checked, broken_entry_id=None, reason=None
    )
