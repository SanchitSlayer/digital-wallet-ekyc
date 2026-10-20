import io
import os
import subprocess
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.auth.models import UserRole
from app.auth.schemas import RegisterRequest
from app.auth.service import register_user
from app.core.config import BACKEND_DIR, settings
from app.core.database import Base, get_db
from app.kyc import ocr
from app.main import app

test_engine = create_engine(settings.test_database_url)
TestSessionLocal = sessionmaker(bind=test_engine)

USER_EMAIL = "jane@example.com"
USER_PASSWORD = "user-password-1"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin-password-1"
FAKE_OCR_TEXT = "SAMPLE NATIONAL ID\nName: JANE DOE\nID No: AB12345678"


@pytest.fixture(scope="session")
def migrated_database() -> None:
    # The real migrations run instead of create_all, because the ledger's append-only trigger exists only in a
    # migration.
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env={**os.environ, "DATABASE_URL": settings.test_database_url},
        check=True,
        capture_output=True,
    )


@pytest.fixture
def db(migrated_database: None) -> Iterator[Session]:
    # Emptied before every test, so no test can pass or fail because of data another test left behind.
    # TRUNCATE does not fire the ledger's row-level UPDATE/DELETE trigger.
    table_names = ", ".join(table.name for table in Base.metadata.sorted_tables)
    with test_engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))
    with TestSessionLocal() as session:
        yield session


@pytest.fixture
def client(db: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    def get_test_db() -> Iterator[Session]:
        with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = get_test_db
    monkeypatch.setattr(settings, "upload_dir", tmp_path)
    monkeypatch.setattr(settings, "enable_dev_topup", True)
    monkeypatch.setattr(ocr, "extract_text", lambda image: FAKE_OCR_TEXT)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def user_payload() -> dict[str, str]:
    return {"full_name": "Jane Doe", "email": USER_EMAIL, "phone": "9876543210", "password": USER_PASSWORD}


@pytest.fixture
def login(client: TestClient) -> Callable[[str, str], dict[str, str]]:
    def login_as(email: str, password: str) -> dict[str, str]:
        response = client.post("/auth/login", json={"email": email, "password": password})
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return login_as


@pytest.fixture
def user_headers(
    client: TestClient, user_payload: dict[str, str], login: Callable[[str, str], dict[str, str]]
) -> dict[str, str]:
    client.post("/auth/register", json=user_payload)
    return login(USER_EMAIL, USER_PASSWORD)


@pytest.fixture
def admin_headers(db: Session, login: Callable[[str, str], dict[str, str]]) -> dict[str, str]:
    admin = RegisterRequest(full_name="Admin One", email=ADMIN_EMAIL, phone="9000000000", password=ADMIN_PASSWORD)
    register_user(db, admin, role=UserRole.ADMIN)
    return login(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture
def card_image() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (640, 400), "white").save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def make_verified_user(
    client: TestClient,
    login: Callable[[str, str], dict[str, str]],
    admin_headers: dict[str, str],
    card_image: bytes,
) -> Callable[[str, str, str], dict[str, str]]:
    def register_and_verify(full_name: str, email: str, phone: str) -> dict[str, str]:
        client.post(
            "/auth/register",
            json={"full_name": full_name, "email": email, "phone": phone, "password": USER_PASSWORD},
        )
        headers = login(email, USER_PASSWORD)
        submission = client.post(
            "/kyc/submissions", headers=headers, files={"image": ("card.png", card_image, "image/png")}
        ).json()
        client.post(f"/admin/kyc/submissions/{submission['id']}/approve", headers=admin_headers)
        return headers

    return register_and_verify


@pytest.fixture
def payer_headers(make_verified_user: Callable[[str, str, str], dict[str, str]]) -> dict[str, str]:
    return make_verified_user("Jane Doe", "payer@example.com", "9111111111")


@pytest.fixture
def receiver_headers(make_verified_user: Callable[[str, str, str], dict[str, str]]) -> dict[str, str]:
    return make_verified_user("Ravi Kumar", "receiver@example.com", "9222222222")
