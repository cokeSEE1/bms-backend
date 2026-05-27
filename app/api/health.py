from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db

router = APIRouter()


@router.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello, BMS"}


@router.get("/db/ping")
async def db_ping(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, int]:
    result = await db.execute(text("SELECT 1"))
    return {"db": result.scalar_one()}
