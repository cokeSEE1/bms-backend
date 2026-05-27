from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import TokenOut
from app.schemas.user import UserLogin, UserRegister, UserOut


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register(self, body: UserRegister) -> UserOut:
        result = await self.db.execute(
            select(User).where(User.username == body.username)
        )
        if result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="用户名已存在",
            )
        user = User(username=body.username, password=hash_password(body.password))
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return UserOut.model_validate(user)

    async def login(self, body: UserLogin) -> TokenOut:
        result = await self.db.execute(
            select(User).where(User.username == body.username)
        )
        user = result.scalar_one_or_none()
        if user is None or not verify_password(body.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
            )
        token = create_access_token(user.id)
        return TokenOut(access_token=token, user=UserOut.model_validate(user))
