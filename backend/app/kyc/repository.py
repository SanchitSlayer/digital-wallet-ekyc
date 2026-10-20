import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.kyc.models import KycStatus, KycSubmission


def get_submission(db: Session, submission_id: uuid.UUID) -> KycSubmission | None:
    return db.get(KycSubmission, submission_id)


def get_latest_submission_for_user(db: Session, user_id: uuid.UUID) -> KycSubmission | None:
    return db.scalar(
        select(KycSubmission)
        .where(KycSubmission.user_id == user_id)
        .order_by(KycSubmission.created_at.desc())
        .limit(1)
    )


def list_submissions_by_status(db: Session, status: KycStatus) -> list[KycSubmission]:
    # selectinload fetches every submitter in one extra query instead of one query per submission.
    return list(
        db.scalars(
            select(KycSubmission)
            .where(KycSubmission.status == status)
            .options(selectinload(KycSubmission.user))
            .order_by(KycSubmission.created_at)
        )
    )


def create_submission(
    db: Session,
    *,
    user_id: uuid.UUID,
    image_filename: str,
    ocr_text: str,
    id_number: str | None,
    extracted_name: str | None,
    name_match_score: float,
) -> KycSubmission:
    submission = KycSubmission(
        user_id=user_id,
        image_filename=image_filename,
        ocr_text=ocr_text,
        id_number=id_number,
        extracted_name=extracted_name,
        name_match_score=name_match_score,
    )
    db.add(submission)
    db.flush()
    return submission


def record_review(
    db: Session,
    submission: KycSubmission,
    *,
    status: KycStatus,
    reviewer_id: uuid.UUID,
    rejection_reason: str | None,
) -> None:
    submission.status = status
    submission.reviewed_by_id = reviewer_id
    submission.reviewed_at = datetime.now(UTC)
    submission.rejection_reason = rejection_reason
    db.flush()
