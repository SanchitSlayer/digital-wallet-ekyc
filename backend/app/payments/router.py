from typing import Annotated

from fastapi import APIRouter, Header, status

from app.auth.dependencies import CurrentUser
from app.core.database import DbSession
from app.payments import service
from app.payments.schemas import (
    CreatePaymentQrRequest,
    PaymentPreviewResponse,
    PaymentQrResponse,
    PayWithQrRequest,
    QrPayloadRequest,
)
from app.wallet.schemas import TransferResponse

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/qr", status_code=status.HTTP_201_CREATED)
def create_payment_qr(request: CreatePaymentQrRequest, user: CurrentUser, db: DbSession) -> PaymentQrResponse:
    return service.create_payment_qr(db, user, request.amount_paise)


@router.post("/qr/preview")
def preview_payment(request: QrPayloadRequest, user: CurrentUser, db: DbSession) -> PaymentPreviewResponse:
    return service.preview_payment(db, user, request.qr_payload)


@router.post("/qr/pay")
def pay_with_qr(
    request: PayWithQrRequest,
    idempotency_key: Annotated[str, Header(min_length=8, max_length=64)],
    user: CurrentUser,
    db: DbSession,
) -> TransferResponse:
    transfer = service.pay_with_qr(db, user, request.qr_payload, request.amount_paise, idempotency_key)
    return TransferResponse.from_transfer(transfer)
