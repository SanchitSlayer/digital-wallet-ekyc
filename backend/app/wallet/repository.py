import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.wallet.models import Transfer, Wallet


def get_wallet(db: Session, wallet_id: uuid.UUID) -> Wallet | None:
    return db.get(Wallet, wallet_id)


def get_wallet_by_user(db: Session, user_id: uuid.UUID) -> Wallet | None:
    return db.scalar(select(Wallet).where(Wallet.user_id == user_id))


def create_wallet(db: Session, user_id: uuid.UUID) -> Wallet:
    wallet = Wallet(user_id=user_id, balance_paise=0)
    db.add(wallet)
    db.flush()
    return wallet


def lock_wallets(db: Session, wallet_ids: list[uuid.UUID]) -> dict[uuid.UUID, Wallet]:
    # Rows are locked in ascending id order, so two transfers between the same pair of wallets always queue
    # for the locks in the same sequence and cannot deadlock. populate_existing refreshes any copy of these
    # wallets already loaded in the session, so the balance read here is the locked, current value.
    wallets = db.scalars(
        select(Wallet)
        .where(Wallet.id.in_(wallet_ids))
        .order_by(Wallet.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return {wallet.id: wallet for wallet in wallets}


def change_balance(db: Session, wallet: Wallet, delta_paise: int) -> None:
    wallet.balance_paise += delta_paise
    db.flush()


def get_transfer_by_idempotency_key(db: Session, sender_wallet_id: uuid.UUID, idempotency_key: str) -> Transfer | None:
    return db.scalar(
        select(Transfer).where(
            Transfer.sender_wallet_id == sender_wallet_id, Transfer.idempotency_key == idempotency_key
        )
    )


def create_transfer(
    db: Session, *, sender_wallet_id: uuid.UUID, receiver_wallet_id: uuid.UUID, amount_paise: int, idempotency_key: str
) -> Transfer:
    transfer = Transfer(
        sender_wallet_id=sender_wallet_id,
        receiver_wallet_id=receiver_wallet_id,
        amount_paise=amount_paise,
        idempotency_key=idempotency_key,
    )
    db.add(transfer)
    db.flush()
    return transfer
