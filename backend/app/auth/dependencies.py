import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth import repository
from app.auth.models import User, UserRole
from app.core.database import DbSession
from app.core.security import decode_access_token

# auto_error is off so a missing token gets our own 401 message instead of FastAPI's generic one.
bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"})


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)], db: DbSession
) -> User:
    if credentials is None:
        raise _unauthorized("Authentication required: missing bearer token in the Authorization header")
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Authentication failed: token has expired, please log in again")
    except jwt.InvalidTokenError:
        raise _unauthorized("Authentication failed: token is invalid")

    user = repository.get_user_by_id(db, uuid.UUID(payload["sub"]))
    if user is None:
        raise _unauthorized("Authentication failed: the account for this token no longer exists")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied: this action requires the admin role")
    return user


AdminUser = Annotated[User, Depends(require_admin)]
