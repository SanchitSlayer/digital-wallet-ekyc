from fastapi import APIRouter, status

from app.auth import service
from app.auth.dependencies import CurrentUser
from app.auth.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.core.database import DbSession

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: DbSession) -> UserResponse:
    return UserResponse.model_validate(service.register_user(db, request))


@router.post("/login")
def login(request: LoginRequest, db: DbSession) -> TokenResponse:
    return TokenResponse(access_token=service.login(db, request))


@router.get("/me")
def me(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)
