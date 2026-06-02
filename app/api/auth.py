from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from jose import jwt

from app.api.deps import get_auth_service, get_current_user
from app.config import ALGORITHM, SECRET_KEY
from app.models.user import User
from app.schemas.auth import LogoutOut, TokenOut
from app.schemas.change_password import ChangePasswordOut, ChangePasswordRequest
from app.schemas.user import UserLogin, UserOut, UserRegister
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


@router.post("/logout", response_model=LogoutOut)
async def logout(
    current_user: Annotated[User, Depends(get_current_user)],
    authorization: Annotated[str, Header()],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> LogoutOut:
    _, _, token = authorization.partition(" ")
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return await service.logout(payload["jti"], payload["exp"])


@router.put("/change-password", response_model=ChangePasswordOut)
async def change_password(
    body: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> ChangePasswordOut:
    return await service.change_password(current_user, body)
