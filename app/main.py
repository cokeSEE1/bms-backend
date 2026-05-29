from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import api_router
from app.config import DATABASE_URL, DB_CHECK_ON_STARTUP
from app.core.database import Base, engine
from app.core.elasticsearch import close_es, init_es
from app.core.es_index import ensure_index
from app.core.redis import close_redis, init_redis
from app.models import base as _models_base  # noqa: F401 — 确保所有 entity 被导入后再 create_all


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    if DB_CHECK_ON_STARTUP:
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
                await conn.run_sync(Base.metadata.create_all)
        except SQLAlchemyError as exc:
            raise RuntimeError(
                f"Database connection failed. DATABASE_URL={DATABASE_URL}",
            ) from exc
    await init_redis()
    await init_es()
    await ensure_index()
    yield
    await engine.dispose()
    await close_redis()
    await close_es()


def create_app() -> FastAPI:
    app = FastAPI(title="KMS", version="0.1.0", lifespan=lifespan)
    app.include_router(api_router)
    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, reload=True)
