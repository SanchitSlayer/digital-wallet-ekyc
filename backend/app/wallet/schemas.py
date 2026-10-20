import uuid
from datetime import datetime
from typing import Annotated, Self

from pydantic import BaseModel, Field

from app.ledger.models import LedgerEntry, LedgerEntryType
from app.wallet.models import Transfer, Wallet

# 1,00,000 rupees: a cap that keeps fake-money test values readable and far from BigInteger limits.
MAX_AMOUNT_PAISE = 10_000_000

AmountPaise = Annotated[int, Field(gt=0, le=MAX_AMOUNT_PAISE, description="Amount in paise (100 paise = 1 rupee)")]


class WalletResponse(BaseModel):
    id: uuid.UUID
    balance_paise: int
    top_up_enabled: bool
    created_at: datetime

    @classmethod
    def from_wallet(cls, wallet: Wallet, top_up_enabled: bool) -> Self:
        return cls(
            id=wallet.id,
            balance_paise=wallet.balance_paise,
            top_up_enabled=top_up_enabled,
            created_at=wallet.created_at,
        )


class TopUpRequest(BaseModel):
    amount_paise: AmountPaise


class LedgerEntryResponse(BaseModel):
    id: int
    entry_type: LedgerEntryType
    amount_paise: int = Field(description="Positive for money in, negative for money out")
    balance_after_paise: int
    counterparty_name: str | None
    created_at: datetime

    @classmethod
    def from_entry(cls, entry: LedgerEntry) -> Self:
        counterparty_name = None
        if entry.transfer is not None:
            other_wallet = (
                entry.transfer.receiver_wallet
                if entry.entry_type == LedgerEntryType.TRANSFER_DEBIT
                else entry.transfer.sender_wallet
            )
            counterparty_name = other_wallet.user.full_name
        return cls(
            id=entry.id,
            entry_type=entry.entry_type,
            amount_paise=entry.amount_paise,
            balance_after_paise=entry.balance_after_paise,
            counterparty_name=counterparty_name,
            created_at=entry.created_at,
        )


class TransferResponse(BaseModel):
    id: uuid.UUID
    receiver_wallet_id: uuid.UUID
    receiver_name: str
    amount_paise: int
    created_at: datetime

    @classmethod
    def from_transfer(cls, transfer: Transfer) -> Self:
        return cls(
            id=transfer.id,
            receiver_wallet_id=transfer.receiver_wallet_id,
            receiver_name=transfer.receiver_wallet.user.full_name,
            amount_paise=transfer.amount_paise,
            created_at=transfer.created_at,
        )
