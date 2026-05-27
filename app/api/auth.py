from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import get_auth_service, get_current_user
from app.models.user import User
from app.schemas.auth import TokenOut
from app.schemas.user import UserLogin, UserRegister, UserOut
from app.services.auth import AuthService

router = APIRouter(prefix="/auth")


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    body: UserRegister,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserOut:
    return await service.register(body)


@router.post("/login", response_model=TokenOut)
async def login(
    body: UserLogin,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenOut:
    return await service.login(body)


@router.get("/me", response_model=UserOut)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserOut:
    return UserOut.model_validate(current_user)
