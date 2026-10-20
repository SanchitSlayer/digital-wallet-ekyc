import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User, UserRole


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def get_user_by_phone(db: Session, phone: str) -> User | None:
    return db.scalar(select(User).where(User.phone == phone))


def create_user(
    db: Session, *, full_name: str, email: str, phone: str, password_hash: str, role: UserRole
) -> User:
    user = User(full_name=full_name, email=email, phone=phone, password_hash=password_hash, role=role)
    db.add(user)
    db.flush()
    return user
