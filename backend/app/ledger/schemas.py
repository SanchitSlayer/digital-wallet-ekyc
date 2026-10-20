from typing import Self

from pydantic import BaseModel


class LedgerVerificationResponse(BaseModel):
    intact: bool
    entries_checked: int
    broken_entry_id: int | None
    reason: str | None

    @classmethod
    def broken(cls, entries_checked: int, entry_id: int, reason: str) -> Self:
        return cls(
            intact=False,
            entries_checked=entries_checked,
            broken_entry_id=entry_id,
            reason=f"Ledger chain broken at entry {entry_id}: {reason}",
        )
