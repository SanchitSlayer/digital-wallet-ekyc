from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    database_url: str
    test_database_url: str
    jwt_secret_key: str
    jwt_algorithm: str
    jwt_expire_minutes: int
    cors_origin: str
    upload_dir: Path
    max_upload_bytes: int
    enable_dev_topup: bool
    qr_signing_key: str
    qr_expire_minutes: int

    @field_validator("upload_dir")
    @classmethod
    def resolve_upload_dir(cls, value: Path) -> Path:
        # Anchored to backend/ so uploads land in the same place no matter which folder the server is started from.
        return BACKEND_DIR / value


settings = Settings()
