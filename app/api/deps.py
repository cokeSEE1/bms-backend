from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import ALGORITHM, SECRET_KEY
from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis
from app.entities.user import User
from app.services.auth import AuthService
from app.services.comment import CommentService
from app.services.knowledge_directory import KnowledgeDirectoryService
from app.services.knowledge_item import KnowledgeItemService
from app.services.user_stats import UserStatsService


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭据",
        )
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证格式无效",
        )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="凭据无效",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="凭据无效或已过期",
        ) from None

    # 检查 Redis 黑名单
    redis_client = get_redis()
    if redis_client is not None:
        jti: str | None = payload.get("jti")
        if jti:
            try:
                if await redis_client.exists(f"bl:{jti}"):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="凭据已失效",
                    )
            except RedisError:
                pass  # Redis 不可达时降级放行

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )
    return user


def get_auth_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthService:
    return AuthService(db)


def get_directory_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KnowledgeDirectoryService:
    return KnowledgeDirectoryService(db)


def get_knowledge_item_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KnowledgeItemService:
    return KnowledgeItemService(db)


def get_comment_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CommentService:
    return CommentService(db)


def get_user_stats_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserStatsService:
    return UserStatsService(db)
