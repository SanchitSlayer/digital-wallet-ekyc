import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.config import settings
from app.kyc import repository as kyc_repository
from app.ledger import service as ledger_service
from app.ledger.models import LedgerEntry, LedgerEntryType
from app.wallet import repository
from app.wallet.models import Transfer, Wallet

logger = logging.getLogger(__name__)


def format_rupees(paise: int) -> str:
    return f"Rs {paise // 100:,}.{paise % 100:02d}"


def open_wallet(db: Session, user_id: uuid.UUID) -> Wallet:
    return repository.create_wallet(db, user_id)


def get_active_wallet(db: Session, user: User) -> Wallet:
    wallet = repository.get_wallet_by_user(db, user.id)
    if wallet is not None:
        return wallet
    latest = kyc_repository.get_latest_submission_for_user(db, user.id)
    kyc_state = "you have not submitted KYC yet" if latest is None else f"your KYC status is {latest.status}"
    raise HTTPException(
        status.HTTP_403_FORBIDDEN, f"Wallet unavailable: payments require verified KYC, and {kyc_state}"
    )


def get_wallet_or_404(db: Session, wallet_id: uuid.UUID) -> Wallet:
    wallet = repository.get_wallet(db, wallet_id)
    if wallet is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Wallet {wallet_id} does not exist")
    return wallet


def list_transactions(db: Session, user: User) -> list[LedgerEntry]:
    return ledger_service.list_wallet_entries(db, get_active_wallet(db, user))


def top_up(db: Session, user: User, amount_paise: int) -> Wallet:
    if not settings.enable_dev_topup:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Top-up is disabled: it is a development-only feature, enabled with ENABLE_DEV_TOPUP=true",
        )
    wallet_id = get_active_wallet(db, user).id
    wallet = repository.lock_wallets(db, [wallet_id])[wallet_id]
    repository.change_balance(db, wallet, amount_paise)
    ledger_service.append_entry(
        db, wallet=wallet, transfer_id=None, entry_type=LedgerEntryType.TOP_UP, amount_paise=amount_paise
    )
    db.commit()
    logger.info("Wallet %s topped up by %d paise", wallet.id, amount_paise)
    return wallet


def transfer(
    db: Session, sender: User, receiver_wallet_id: uuid.UUID, amount_paise: int, idempotency_key: str
) -> Transfer:
    sender_wallet_id = get_active_wallet(db, sender).id
    if receiver_wallet_id == sender_wallet_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Payment failed: you cannot pay your own wallet")

    wallets = repository.lock_wallets(db, [sender_wallet_id, receiver_wallet_id])
    sender_wallet = wallets[sender_wallet_id]
    receiver_wallet = wallets.get(receiver_wallet_id)
    if receiver_wallet is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"Payment failed: receiver wallet {receiver_wallet_id} does not exist"
        )

    # Checked only after the sender's wallet is locked: a retry that raced the original request waits on that
    # lock, and by the time it gets it the original transfer is committed and visible here.
    existing = repository.get_transfer_by_idempotency_key(db, sender_wallet_id, idempotency_key)
    if existing is not None:
        if existing.receiver_wallet_id != receiver_wallet_id or existing.amount_paise != amount_paise:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Payment failed: this idempotency key was already used for a different payment",
            )
        logger.info("Replayed transfer %s for idempotency key retry", existing.id)
        return existing

    if sender_wallet.balance_paise < amount_paise:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Payment failed: insufficient balance, available {format_rupees(sender_wallet.balance_paise)}, "
            f"required {format_rupees(amount_paise)}",
        )

    new_transfer = repository.create_transfer(
        db,
        sender_wallet_id=sender_wallet_id,
        receiver_wallet_id=receiver_wallet_id,
        amount_paise=amount_paise,
        idempotency_key=idempotency_key,
    )
    repository.change_balance(db, sender_wallet, -amount_paise)
    ledger_service.append_entry(
        db,
        wallet=sender_wallet,
        transfer_id=new_transfer.id,
        entry_type=LedgerEntryType.TRANSFER_DEBIT,
        amount_paise=-amount_paise,
    )
    repository.change_balance(db, receiver_wallet, amount_paise)
    ledger_service.append_entry(
        db,
        wallet=receiver_wallet,
        transfer_id=new_transfer.id,
        entry_type=LedgerEntryType.TRANSFER_CREDIT,
        amount_paise=amount_paise,
    )
    db.commit()
    logger.info(
        "Transfer %s of %d paise from wallet %s to wallet %s",
        new_transfer.id,
        amount_paise,
        sender_wallet_id,
        receiver_wallet_id,
    )
    return new_transfer
