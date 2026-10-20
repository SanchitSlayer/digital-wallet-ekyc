import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, StringConstraints

from app.kyc.models import KycStatus


def mask_id_number(value: str) -> str:
    return "*" * max(len(value) - 4, 0) + value[-4:]


MaskedIdNumber = Annotated[str, PlainSerializer(mask_id_number)]


class KycSubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: KycStatus
    id_number: MaskedIdNumber | None = Field(description="Only the last 4 characters are visible")
    name_match_score: float = Field(description="Similarity between the registered name and the card, 0 to 100")
    rejection_reason: str | None
    created_at: datetime
    reviewed_at: datetime | None


class KycUserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str


class AdminKycSubmissionResponse(KycSubmissionResponse):
    user: KycUserSummary
    extracted_name: str | None
    ocr_text: str


class RejectKycRequest(BaseModel):
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=500)]
