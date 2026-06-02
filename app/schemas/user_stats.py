from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserStatsOut(BaseModel):
    read_count: int
    original_count: int
    total_read_count: int


class ParticipatedItemOut(BaseModel):
    id: int
    name: str
    update_time: datetime

    model_config = ConfigDict(from_attributes=True)


class ParticipatedListOut(BaseModel):
    items: list[ParticipatedItemOut]
