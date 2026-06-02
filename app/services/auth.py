from datetime import UTC, datetime

from fastapi import HTTPException, status
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.core.security import create_access_token, hash_password, verify_password
from app.entities.user import User
from app.schemas.auth import LogoutOut, TokenOut
from app.schemas.change_password import ChangePasswordOut, ChangePasswordRequest
from app.schemas.user import UserLogin, UserOut, UserRegister


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register(self, body: UserRegister) -> UserOut:
        result = await self.db.execute(
            select(User).where(User.username == body.username),
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
            select(User).where(User.username == body.username),
        )
        user = result.scalar_one_or_none()
        if user is None or not verify_password(body.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
            )
        token = create_access_token(user.id)
        return TokenOut(access_token=token, user=UserOut.model_validate(user))

    async def logout(self, jti: str, exp: int) -> LogoutOut:
        redis_client = get_redis()
        if redis_client is not None:
            remaining = exp - int(datetime.now(UTC).timestamp())
            if remaining > 0:
                try:
                    await redis_client.set(f"bl:{jti}", "1", ex=remaining)
                except RedisError:
                    pass  # Redis 不可达时降级，不影响退出响应
        return LogoutOut(message="已退出登录")

    async def change_password(self, user: User, body: ChangePasswordRequest) -> ChangePasswordOut:
        if not verify_password(body.old_password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="旧密码错误",
            )
        user.password = hash_password(body.new_password)
        await self.db.commit()
        return ChangePasswordOut(message="密码修改成功")
