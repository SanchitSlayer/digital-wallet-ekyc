import io
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.auth.models import UserRole
from app.auth.schemas import RegisterRequest
from app.auth.service import register_user
from app.core.config import settings
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


@pytest.fixture
def db() -> Iterator[Session]:
    # Fresh tables for every test, so no test can pass or fail because of data another test left behind.
    Base.metadata.create_all(test_engine)
    with TestSessionLocal() as session:
        yield session
    Base.metadata.drop_all(test_engine)


@pytest.fixture
def client(db: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    def get_test_db() -> Iterator[Session]:
        with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = get_test_db
    monkeypatch.setattr(settings, "upload_dir", tmp_path)
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
