from fastapi import APIRouter

from app.auth.dependencies import CurrentUser
from app.core.config import settings
from app.core.database import DbSession
from app.wallet import service
from app.wallet.schemas import LedgerEntryResponse, TopUpRequest, WalletResponse

router = APIRouter(prefix="/wallet", tags=["wallet"])


@router.get("")
def my_wallet(user: CurrentUser, db: DbSession) -> WalletResponse:
    return WalletResponse.from_wallet(service.get_active_wallet(db, user), settings.enable_dev_topup)


@router.get("/transactions")
def my_transactions(user: CurrentUser, db: DbSession) -> list[LedgerEntryResponse]:
    return [LedgerEntryResponse.from_entry(entry) for entry in service.list_transactions(db, user)]


@router.post("/top-up")
def top_up(request: TopUpRequest, user: CurrentUser, db: DbSession) -> WalletResponse:
    return WalletResponse.from_wallet(service.top_up(db, user, request.amount_paise), settings.enable_dev_topup)
