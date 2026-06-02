from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.entities.user import User
from app.schemas.ranking import RankItemOut as RankItemSchema
from app.schemas.ranking import RankingResponse
from app.services.ranking import RankingService

router = APIRouter(prefix="/v1/rankings")


def _to_response(service_items) -> RankingResponse:
    """将 service dataclass 列表转为 Pydantic schema 响应"""
    return RankingResponse(
        items=[RankItemSchema(rank=i.rank, name=i.name, department=i.department, count=i.count)
               for i in service_items]
    )


@router.get("/reading-stars", response_model=RankingResponse)
async def get_reading_stars(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> RankingResponse:
    service = RankingService(db)
    items = await service.get_reading_stars(limit)
    return _to_response(items)


@router.get("/original-stars", response_model=RankingResponse)
async def get_original_stars(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> RankingResponse:
    service = RankingService(db)
    items = await service.get_original_stars(limit)
    return _to_response(items)


@router.get("/hot-stars", response_model=RankingResponse)
async def get_hot_stars(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> RankingResponse:
    service = RankingService(db)
    items = await service.get_hot_stars(limit)
    return _to_response(items)
