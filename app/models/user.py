from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.entities.user import User


class UserModel:
    _entity = User

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: int) -> User | None:
        result = await db.execute(
            select(User).where(User.id == user_id, User.is_delete == 0)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_username(db: AsyncSession, username: str) -> User | None:
        result = await db.execute(
            select(User).where(User.username == username, User.is_delete == 0)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, username: str, password: str) -> User:
        user = User(username=username, password=password)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
