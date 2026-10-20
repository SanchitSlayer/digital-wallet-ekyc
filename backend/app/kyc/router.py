import uuid
from typing import Annotated

from fastapi import APIRouter, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.auth.dependencies import AdminUser, CurrentUser
from app.core.config import settings
from app.core.database import DbSession
from app.kyc import service
from app.kyc.models import KycStatus
from app.kyc.schemas import AdminKycSubmissionResponse, KycSubmissionResponse, RejectKycRequest

router = APIRouter(prefix="/kyc", tags=["kyc"])
admin_router = APIRouter(prefix="/admin/kyc", tags=["admin kyc"])


@router.post("/submissions", status_code=status.HTTP_201_CREATED)
def submit(image: UploadFile, user: CurrentUser, db: DbSession) -> KycSubmissionResponse:
    # Reading one byte past the limit is enough to tell an oversized file apart without loading all of it.
    data = image.file.read(settings.max_upload_bytes + 1)
    return KycSubmissionResponse.model_validate(service.submit_kyc(db, user, data))


@router.get("/submissions/me")
def my_latest_submission(user: CurrentUser, db: DbSession) -> KycSubmissionResponse | None:
    submission = service.get_latest_submission(db, user)
    return KycSubmissionResponse.model_validate(submission) if submission else None


@admin_router.get("/submissions")
def list_submissions(
    _: AdminUser,
    db: DbSession,
    status_filter: Annotated[KycStatus, Query(alias="status")] = KycStatus.PENDING,
) -> list[AdminKycSubmissionResponse]:
    submissions = service.list_submissions(db, status_filter)
    return [AdminKycSubmissionResponse.model_validate(submission) for submission in submissions]


@admin_router.get("/submissions/{submission_id}/image", response_class=FileResponse)
def submission_image(submission_id: uuid.UUID, _: AdminUser, db: DbSession) -> FileResponse:
    return FileResponse(service.get_submission_image_path(db, submission_id))


@admin_router.post("/submissions/{submission_id}/approve")
def approve(submission_id: uuid.UUID, admin: AdminUser, db: DbSession) -> AdminKycSubmissionResponse:
    return AdminKycSubmissionResponse.model_validate(service.approve_submission(db, admin, submission_id))


@admin_router.post("/submissions/{submission_id}/reject")
def reject(
    submission_id: uuid.UUID, request: RejectKycRequest, admin: AdminUser, db: DbSession
) -> AdminKycSubmissionResponse:
    return AdminKycSubmissionResponse.model_validate(
        service.reject_submission(db, admin, submission_id, request.reason)
    )
