import pytest
from fastapi.testclient import TestClient
from httpx import Response

from app.core.config import settings

UNKNOWN_SUBMISSION_ID = "00000000-0000-0000-0000-000000000000"


def upload(client: TestClient, headers: dict[str, str], image: bytes) -> Response:
    return client.post("/kyc/submissions", headers=headers, files={"image": ("card.png", image, "image/png")})


@pytest.fixture
def pending_submission(client: TestClient, user_headers: dict[str, str], card_image: bytes) -> dict[str, object]:
    return upload(client, user_headers, card_image).json()


def test_upload_creates_pending_submission(
    client: TestClient, user_headers: dict[str, str], card_image: bytes
) -> None:
    response = upload(client, user_headers, card_image)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["id_number"] == "******5678"
    assert body["name_match_score"] == 100.0
    stored_files = list(settings.upload_dir.iterdir())
    assert len(stored_files) == 1
    assert stored_files[0].name != "card.png"


def test_admin_approve_sets_verified(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    pending_submission: dict[str, object],
) -> None:
    response = client.post(f"/admin/kyc/submissions/{pending_submission['id']}/approve", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["status"] == "VERIFIED"
    assert client.get("/kyc/submissions/me", headers=user_headers).json()["status"] == "VERIFIED"


def test_admin_reject_sets_rejected_with_reason(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    pending_submission: dict[str, object],
) -> None:
    response = client.post(
        f"/admin/kyc/submissions/{pending_submission['id']}/reject",
        headers=admin_headers,
        json={"reason": "Photo is blurry, please retake"},
    )

    assert response.status_code == 200
    mine = client.get("/kyc/submissions/me", headers=user_headers).json()
    assert mine["status"] == "REJECTED"
    assert mine["rejection_reason"] == "Photo is blurry, please retake"


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/admin/kyc/submissions"),
        ("GET", f"/admin/kyc/submissions/{UNKNOWN_SUBMISSION_ID}/image"),
        ("POST", f"/admin/kyc/submissions/{UNKNOWN_SUBMISSION_ID}/approve"),
        ("POST", f"/admin/kyc/submissions/{UNKNOWN_SUBMISSION_ID}/reject"),
        ("GET", "/admin/ledger/verify"),
    ],
)
def test_normal_user_cannot_access_admin_endpoints(
    client: TestClient, user_headers: dict[str, str], method: str, path: str
) -> None:
    response = client.request(method, path, headers=user_headers, json={"reason": "Not allowed to do this"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Access denied: this action requires the admin role"


def test_resubmission_blocked_while_pending(
    client: TestClient, user_headers: dict[str, str], card_image: bytes, pending_submission: dict[str, object]
) -> None:
    response = upload(client, user_headers, card_image)

    assert response.status_code == 409
    assert "already pending review" in response.json()["detail"]


def test_resubmission_allowed_after_rejection(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    card_image: bytes,
    pending_submission: dict[str, object],
) -> None:
    client.post(
        f"/admin/kyc/submissions/{pending_submission['id']}/reject",
        headers=admin_headers,
        json={"reason": "Name does not match the card"},
    )

    response = upload(client, user_headers, card_image)

    assert response.status_code == 201
    assert response.json()["status"] == "PENDING"
