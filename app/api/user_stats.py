from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_user_stats_service
from app.entities.user import User
from app.schemas.user_stats import ParticipatedItemOut, ParticipatedListOut, UserStatsOut
from app.services.user_stats import UserStatsService

router = APIRouter(prefix="/v1/user")


@router.get("/stats", response_model=UserStatsOut)
async def get_user_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UserStatsService, Depends(get_user_stats_service)],
) -> UserStatsOut:
    return await service.get_stats(current_user.username)


@router.get("/participated", response_model=ParticipatedListOut)
async def get_participated(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UserStatsService, Depends(get_user_stats_service)],
) -> ParticipatedListOut:
    items = await service.get_participated(current_user.username)
    return ParticipatedListOut(
        items=[ParticipatedItemOut.model_validate(item) for item in items],
    )
