import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session


@pytest.fixture
def ledger_with_payment(
    client: TestClient, payer_headers: dict[str, str], receiver_headers: dict[str, str]
) -> None:
    client.post("/wallet/top-up", headers=payer_headers, json={"amount_paise": 10_000})
    client.post("/wallet/top-up", headers=receiver_headers, json={"amount_paise": 500})
    qr_payload = client.post("/payments/qr", headers=receiver_headers, json={"amount_paise": 2_000}).json()[
        "qr_payload"
    ]
    client.post(
        "/payments/qr/pay",
        headers={**payer_headers, "Idempotency-Key": "ledger-fixture-1"},
        json={"qr_payload": qr_payload},
    )


def test_ledger_chain_verifies_as_intact(
    client: TestClient, admin_headers: dict[str, str], ledger_with_payment: None
) -> None:
    response = client.get("/admin/ledger/verify", headers=admin_headers)

    assert response.status_code == 200
    assert response.json() == {"intact": True, "entries_checked": 4, "broken_entry_id": None, "reason": None}


def test_ledger_rejects_update_and_delete(db: Session, ledger_with_payment: None) -> None:
    for statement in ("UPDATE ledger_entries SET amount_paise = 1 WHERE id = 1", "DELETE FROM ledger_entries"):
        with pytest.raises(ProgrammingError, match="ledger_entries is append-only"):
            db.execute(text(statement))
        db.rollback()


def test_ledger_tampering_is_detected(
    client: TestClient, db: Session, admin_headers: dict[str, str], ledger_with_payment: None
) -> None:
    # Simulates someone with direct database access: the trigger is switched off only for this one edit.
    db.execute(text("ALTER TABLE ledger_entries DISABLE TRIGGER ledger_entries_append_only"))
    db.execute(text("UPDATE ledger_entries SET amount_paise = 999999 WHERE id = 2"))
    db.execute(text("ALTER TABLE ledger_entries ENABLE TRIGGER ledger_entries_append_only"))
    db.commit()

    response = client.get("/admin/ledger/verify", headers=admin_headers)

    body = response.json()
    assert body["intact"] is False
    assert body["broken_entry_id"] == 2
    assert body["entries_checked"] == 2
    assert body["reason"] == (
        "Ledger chain broken at entry 2: its stored hash does not match its data, so the entry was modified"
    )
