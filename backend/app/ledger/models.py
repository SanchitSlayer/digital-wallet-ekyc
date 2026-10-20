import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Identity, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.wallet.models import Transfer


class LedgerEntryType(StrEnum):
    TOP_UP = "TOP_UP"
    TRANSFER_DEBIT = "TRANSFER_DEBIT"
    TRANSFER_CREDIT = "TRANSFER_CREDIT"


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    # A sequential id, not a UUID, because the hash chain needs an unambiguous order.
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    wallet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wallets.id"), index=True)
    transfer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("transfers.id"))
    entry_type: Mapped[LedgerEntryType] = mapped_column(
        Enum(
            LedgerEntryType,
            name="ledger_entry_type",
            native_enum=False,
            create_constraint=True,
            length=20,
            values_callable=lambda types: [entry_type.value for entry_type in types],
        )
    )
    amount_paise: Mapped[int] = mapped_column(BigInteger)
    balance_after_paise: Mapped[int] = mapped_column(BigInteger)
    # Set in Python rather than by the database, because it is part of the hashed data and must be known before insert.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    previous_hash: Mapped[str] = mapped_column(String(64))
    entry_hash: Mapped[str] = mapped_column(String(64), unique=True)

    transfer: Mapped[Transfer | None] = relationship()
