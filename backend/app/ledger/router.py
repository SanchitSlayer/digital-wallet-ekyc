from fastapi import APIRouter

from app.auth.dependencies import AdminUser
from app.core.database import DbSession
from app.ledger import service
from app.ledger.schemas import LedgerVerificationResponse

admin_router = APIRouter(prefix="/admin/ledger", tags=["admin ledger"])


@admin_router.get("/verify")
def verify_ledger(_: AdminUser, db: DbSession) -> LedgerVerificationResponse:
    return service.verify_chain(db)
