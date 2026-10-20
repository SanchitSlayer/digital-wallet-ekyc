import base64
import json
import uuid

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ledger import service as ledger_service
from app.ledger.models import LedgerEntry, LedgerEntryType
from app.wallet.models import Wallet


def top_up(client: TestClient, headers: dict[str, str], amount_paise: int) -> Response:
    return client.post("/wallet/top-up", headers=headers, json={"amount_paise": amount_paise})


def create_qr(client: TestClient, headers: dict[str, str], amount_paise: int | None) -> str:
    return client.post("/payments/qr", headers=headers, json={"amount_paise": amount_paise}).json()["qr_payload"]


def pay(client: TestClient, headers: dict[str, str], qr_payload: str, idempotency_key: str) -> Response:
    return client.post(
        "/payments/qr/pay",
        headers={**headers, "Idempotency-Key": idempotency_key},
        json={"qr_payload": qr_payload},
    )


def balance(client: TestClient, headers: dict[str, str]) -> int:
    return client.get("/wallet", headers=headers).json()["balance_paise"]


def test_payment_blocked_before_kyc(
    client: TestClient, user_headers: dict[str, str], receiver_headers: dict[str, str]
) -> None:
    qr_payload = create_qr(client, receiver_headers, 500)

    responses = [
        client.get("/wallet", headers=user_headers),
        client.post("/payments/qr", headers=user_headers, json={"amount_paise": 500}),
        pay(client, user_headers, qr_payload, "unverified-attempt-1"),
    ]

    for response in responses:
        assert response.status_code == 403
        assert response.json()["detail"] == (
            "Wallet unavailable: payments require verified KYC, and you have not submitted KYC yet"
        )


def test_successful_payment(
    client: TestClient, payer_headers: dict[str, str], receiver_headers: dict[str, str]
) -> None:
    top_up(client, payer_headers, 10_000)
    qr_payload = create_qr(client, receiver_headers, 2_500)

    response = pay(client, payer_headers, qr_payload, "payment-success-1")

    assert response.status_code == 200
    assert response.json()["receiver_name"] == "Ravi Kumar"
    assert response.json()["amount_paise"] == 2_500
    assert balance(client, payer_headers) == 7_500
    assert balance(client, receiver_headers) == 2_500
    history = client.get("/wallet/transactions", headers=payer_headers).json()
    assert [(entry["entry_type"], entry["amount_paise"]) for entry in history] == [
        ("TRANSFER_DEBIT", -2_500),
        ("TOP_UP", 10_000),
    ]
    assert history[0]["counterparty_name"] == "Ravi Kumar"


def test_insufficient_balance(
    client: TestClient, payer_headers: dict[str, str], receiver_headers: dict[str, str]
) -> None:
    top_up(client, payer_headers, 1_000)
    qr_payload = create_qr(client, receiver_headers, 5_000)

    response = pay(client, payer_headers, qr_payload, "insufficient-1")

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Payment failed: insufficient balance, available Rs 10.00, required Rs 50.00"
    )
    assert balance(client, payer_headers) == 1_000
    assert balance(client, receiver_headers) == 0


def test_expired_qr_is_rejected(
    client: TestClient,
    payer_headers: dict[str, str],
    receiver_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    top_up(client, payer_headers, 10_000)
    monkeypatch.setattr(settings, "qr_expire_minutes", -1)
    qr_payload = create_qr(client, receiver_headers, 1_000)

    response = pay(client, payer_headers, qr_payload, "expired-qr-1")

    assert response.status_code == 410
    assert response.json()["detail"].startswith("Payment QR expired at")
    assert balance(client, payer_headers) == 10_000


def test_tampered_qr_is_rejected(
    client: TestClient, payer_headers: dict[str, str], receiver_headers: dict[str, str]
) -> None:
    top_up(client, payer_headers, 10_000)
    encoded_payload, signature = create_qr(client, receiver_headers, 5_000).split(".")
    payload = json.loads(base64.urlsafe_b64decode(encoded_payload + "=" * (-len(encoded_payload) % 4)))
    payload["amount_paise"] = 1
    forged_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()

    response = pay(client, payer_headers, f"{forged_payload}.{signature}", "tampered-qr-1")

    assert response.status_code == 400
    assert "signature does not match" in response.json()["detail"]
    assert balance(client, payer_headers) == 10_000


def test_idempotent_retry_applies_payment_once(
    client: TestClient, payer_headers: dict[str, str], receiver_headers: dict[str, str]
) -> None:
    top_up(client, payer_headers, 10_000)
    qr_payload = create_qr(client, receiver_headers, 3_000)

    first = pay(client, payer_headers, qr_payload, "retry-key-1")
    retry = pay(client, payer_headers, qr_payload, "retry-key-1")

    assert first.status_code == retry.status_code == 200
    assert first.json()["id"] == retry.json()["id"]
    assert balance(client, payer_headers) == 7_000
    assert balance(client, receiver_headers) == 3_000


def test_failed_transfer_leaves_no_partial_update(
    client: TestClient,
    payer_headers: dict[str, str],
    receiver_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    top_up(client, payer_headers, 10_000)
    qr_payload = create_qr(client, receiver_headers, 4_000)
    real_append_entry = ledger_service.append_entry

    def fail_on_credit(
        db: Session, *, wallet: Wallet, transfer_id: uuid.UUID | None, entry_type: LedgerEntryType, amount_paise: int
    ) -> LedgerEntry:
        # By the time the credit entry is written, the sender has already been debited and its ledger entry added.
        if entry_type == LedgerEntryType.TRANSFER_CREDIT:
            raise RuntimeError("simulated crash after the debit")
        return real_append_entry(
            db, wallet=wallet, transfer_id=transfer_id, entry_type=entry_type, amount_paise=amount_paise
        )

    monkeypatch.setattr(ledger_service, "append_entry", fail_on_credit)

    with pytest.raises(RuntimeError, match="simulated crash"):
        pay(client, payer_headers, qr_payload, "atomicity-1")

    monkeypatch.setattr(ledger_service, "append_entry", real_append_entry)
    assert balance(client, payer_headers) == 10_000
    assert balance(client, receiver_headers) == 0
    assert len(client.get("/wallet/transactions", headers=payer_headers).json()) == 1


def test_top_up_disabled_without_flag(
    client: TestClient, payer_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "enable_dev_topup", False)

    response = top_up(client, payer_headers, 1_000)

    assert response.status_code == 403
    assert response.json()["detail"].startswith("Top-up is disabled")
    assert balance(client, payer_headers) == 0
