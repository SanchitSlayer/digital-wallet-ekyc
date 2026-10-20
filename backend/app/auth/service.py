import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth import repository
from app.auth.models import User, UserRole
from app.auth.schemas import LoginRequest, RegisterRequest
from app.core.security import create_access_token, hash_password, verify_password

logger = logging.getLogger(__name__)

# Checked against when the email is unknown, so a missing account takes as long to reject as a wrong password
# and response timing cannot reveal which emails are registered.
_UNKNOWN_USER_HASH = hash_password("placeholder-for-unknown-users")


def register_user(db: Session, request: RegisterRequest, role: UserRole = UserRole.USER) -> User:
    if repository.get_user_by_email(db, request.email) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Registration failed: this email is already registered")
    if repository.get_user_by_phone(db, request.phone) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Registration failed: this phone number is already registered")

    user = repository.create_user(
        db,
        full_name=request.full_name,
        email=request.email,
        phone=request.phone,
        password_hash=hash_password(request.password),
        role=role,
    )
    db.commit()
    logger.info("Registered user %s with role %s", user.id, user.role)
    return user


def login(db: Session, request: LoginRequest) -> str:
    user = repository.get_user_by_email(db, request.email)
    password_hash = user.password_hash if user is not None else _UNKNOWN_USER_HASH
    if not verify_password(request.password, password_hash) or user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Login failed: email or password is incorrect")
    return create_access_token(str(user.id))
