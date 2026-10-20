import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.auth.models import User
from app.core.database import Base


class Wallet(Base):
    __tablename__ = "wallets"
    # Even if a bug skipped the service's balance check, the database would refuse to store a negative balance.
    __table_args__ = (CheckConstraint("balance_paise >= 0", name="balance_not_negative"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    # Integer paise, never floats: 0.1 + 0.2 is not exactly 0.3 in binary floating point.
    balance_paise: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship()


class Transfer(Base):
    __tablename__ = "transfers"
    __table_args__ = (
        UniqueConstraint("sender_wallet_id", "idempotency_key", name="uq_transfers_sender_idempotency_key"),
        CheckConstraint("amount_paise > 0", name="amount_positive"),
        CheckConstraint("sender_wallet_id <> receiver_wallet_id", name="distinct_wallets"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    sender_wallet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wallets.id"), index=True)
    receiver_wallet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wallets.id"), index=True)
    amount_paise: Mapped[int] = mapped_column(BigInteger)
    idempotency_key: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sender_wallet: Mapped[Wallet] = relationship(foreign_keys=[sender_wallet_id])
    receiver_wallet: Mapped[Wallet] = relationship(foreign_keys=[receiver_wallet_id])
