import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.auth.models import User
from app.core.database import Base


class KycStatus(StrEnum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class KycSubmission(Base):
    __tablename__ = "kyc_submissions"
    # The service already blocks resubmission, but this index makes the database refuse a second active
    # submission even if two uploads from the same user arrive at the same moment.
    __table_args__ = (
        Index(
            "uq_kyc_submissions_one_active_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("status IN ('PENDING', 'VERIFIED')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[KycStatus] = mapped_column(
        Enum(
            KycStatus,
            name="kyc_status",
            native_enum=False,
            create_constraint=True,
            length=10,
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        default=KycStatus.PENDING,
    )
    image_filename: Mapped[str] = mapped_column(String(64))
    ocr_text: Mapped[str] = mapped_column(Text)
    id_number: Mapped[str | None] = mapped_column(String(12))
    extracted_name: Mapped[str | None] = mapped_column(String(255))
    name_match_score: Mapped[float] = mapped_column(Float)
    rejection_reason: Mapped[str | None] = mapped_column(String(500))
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(foreign_keys=[user_id])
