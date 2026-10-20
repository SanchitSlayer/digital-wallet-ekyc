import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.wallet.schemas import AmountPaise


class QrPayload(BaseModel):
    wallet_id: uuid.UUID
    amount_paise: int | None
    expires_at: datetime


class CreatePaymentQrRequest(BaseModel):
    amount_paise: AmountPaise | None = None


class PaymentQrResponse(BaseModel):
    qr_payload: str = Field(description="The signed text encoded in the QR image")
    qr_png_base64: str
    wallet_id: uuid.UUID
    amount_paise: int | None
    expires_at: datetime


class QrPayloadRequest(BaseModel):
    qr_payload: str = Field(max_length=1000)


class PaymentPreviewResponse(BaseModel):
    receiver_wallet_id: uuid.UUID
    receiver_name: str
    amount_paise: int | None
    expires_at: datetime


class PayWithQrRequest(QrPayloadRequest):
    amount_paise: AmountPaise | None = Field(default=None, description="Required only when the QR has no amount")
