import logging
import uuid
from io import BytesIO
from pathlib import Path

import pytesseract
from fastapi import HTTPException, status
from PIL import Image
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.config import settings
from app.kyc import ocr, repository
from app.kyc.models import KycStatus, KycSubmission
from app.kyc.schemas import mask_id_number
from app.wallet import service as wallet_service

logger = logging.getLogger(__name__)

_FILE_EXTENSIONS = {"JPEG": "jpg", "PNG": "png"}


def _open_image(data: bytes) -> Image.Image:
    if not data:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Upload failed: the image file is empty")
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"Upload failed: the image is larger than the {settings.max_upload_bytes // (1024 * 1024)} MB limit",
        )
    try:
        image = Image.open(BytesIO(data))
        image.load()
    except (OSError, Image.DecompressionBombError):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Upload failed: the file could not be read as an image, it may be corrupted or not an image at all",
        ) from None
    if image.format not in _FILE_EXTENSIONS:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Upload failed: {image.format} images are not supported, upload a JPEG or PNG",
        )
    return image


def get_latest_submission(db: Session, user: User) -> KycSubmission | None:
    return repository.get_latest_submission_for_user(db, user.id)


def submit_kyc(db: Session, user: User, data: bytes) -> KycSubmission:
    latest = repository.get_latest_submission_for_user(db, user.id)
    if latest is not None and latest.status == KycStatus.VERIFIED:
        raise HTTPException(status.HTTP_409_CONFLICT, "KYC submission not allowed: this account is already verified")
    if latest is not None and latest.status == KycStatus.PENDING:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "KYC submission not allowed: a submission is already pending review, "
            "you can resubmit only after a rejection",
        )

    image = _open_image(data)
    try:
        result = ocr.analyze_id_image(image, user.full_name)
    except pytesseract.TesseractNotFoundError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "KYC check unavailable: the Tesseract OCR engine is not installed on the server",
        ) from None
    if not result.text:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "No text could be read from the image, upload a sharper, well-lit photo of the whole ID card",
        )

    ocr_text = result.text
    if result.id_number is not None:
        ocr_text = ocr_text.replace(result.id_number, mask_id_number(result.id_number))

    image_filename = f"{uuid.uuid4().hex}.{_FILE_EXTENSIONS[image.format]}"
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    (settings.upload_dir / image_filename).write_bytes(data)

    submission = repository.create_submission(
        db,
        user_id=user.id,
        image_filename=image_filename,
        ocr_text=ocr_text,
        id_number=result.id_number.upper() if result.id_number else None,
        extracted_name=result.matched_name,
        name_match_score=result.name_match_score,
    )
    db.commit()
    logger.info(
        "KYC submission %s created for user %s, id number %s, name match %.1f",
        submission.id,
        user.id,
        mask_id_number(submission.id_number) if submission.id_number else "not found",
        submission.name_match_score,
    )
    return submission


def list_submissions(db: Session, status_filter: KycStatus) -> list[KycSubmission]:
    return repository.list_submissions_by_status(db, status_filter)


def _get_submission_or_404(db: Session, submission_id: uuid.UUID) -> KycSubmission:
    submission = repository.get_submission(db, submission_id)
    if submission is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"KYC submission {submission_id} not found")
    return submission


def _get_reviewable_submission(db: Session, admin: User, submission_id: uuid.UUID) -> KycSubmission:
    submission = _get_submission_or_404(db, submission_id)
    if submission.user_id == admin.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Review failed: admins cannot review their own KYC submission")
    if submission.status != KycStatus.PENDING:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Review failed: this submission is already {submission.status}"
        )
    return submission


def approve_submission(db: Session, admin: User, submission_id: uuid.UUID) -> KycSubmission:
    submission = _get_reviewable_submission(db, admin, submission_id)
    repository.record_review(
        db, submission, status=KycStatus.VERIFIED, reviewer_id=admin.id, rejection_reason=None
    )
    wallet_service.open_wallet(db, submission.user_id)
    db.commit()
    logger.info("KYC submission %s approved by admin %s", submission.id, admin.id)
    return submission


def reject_submission(db: Session, admin: User, submission_id: uuid.UUID, reason: str) -> KycSubmission:
    submission = _get_reviewable_submission(db, admin, submission_id)
    repository.record_review(
        db, submission, status=KycStatus.REJECTED, reviewer_id=admin.id, rejection_reason=reason
    )
    db.commit()
    logger.info("KYC submission %s rejected by admin %s", submission.id, admin.id)
    return submission


def get_submission_image_path(db: Session, submission_id: uuid.UUID) -> Path:
    submission = _get_submission_or_404(db, submission_id)
    path = settings.upload_dir / submission.image_filename
    if not path.is_file():
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"Image for KYC submission {submission_id} is missing from storage"
        )
    return path
