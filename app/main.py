import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, String, func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# 按需修改，或通过环境变量 DATABASE_URL 覆盖
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+aiomysql://root:zl123456@127.0.0.1:3307/test_db?charset=utf8mb4",
)
DB_CHECK_ON_STARTUP = os.getenv("DB_CHECK_ON_STARTUP", "1") == "1"

engine = create_async_engine(DATABASE_URL, echo=True, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


class Book(Base):
    __tablename__ = "book"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[str] = mapped_column(String(100), nullable=False)


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(60), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class BookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str


class UserRegister(BaseModel):
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    user: UserOut


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    # 启动时做一次连通性校验并自动建表，可通过 DB_CHECK_ON_STARTUP=0 关闭
    if DB_CHECK_ON_STARTUP:
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
                await conn.run_sync(Base.metadata.create_all)
        except SQLAlchemyError as exc:
            raise RuntimeError(
                f"Database connection failed. DATABASE_URL={DATABASE_URL}",
            ) from exc
    yield
    await engine.dispose()


app = FastAPI(title="FastAPI Starter", version="0.1.0", lifespan=lifespan)


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


class BookService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_books(self, limit: int = 20) -> list[Book]:
        stmt = select(Book).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


def get_book_service(db: Annotated[AsyncSession, Depends(get_db)]) -> BookService:
    return BookService(db)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello, FastAPI"}


@app.get("/db/ping")
async def db_ping(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, int]:
    result = await db.execute(text("SELECT 1"))
    return {"db": result.scalar_one()}


@app.get("/books")
async def list_books(
    service: Annotated[BookService, Depends(get_book_service)],
    limit: int = 20,
) -> list[BookOut]:
    books = await service.list_books(limit=limit)
    return [BookOut.model_validate(book) for book in books]


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, reload=True)
