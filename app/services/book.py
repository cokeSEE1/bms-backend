from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book


class BookService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_books(self, limit: int = 20) -> list[Book]:
        stmt = select(Book).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
