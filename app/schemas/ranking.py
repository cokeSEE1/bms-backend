from pydantic import BaseModel


class RankItemOut(BaseModel):
    rank: int
    name: str
    department: str
    count: int


class RankingResponse(BaseModel):
    items: list[RankItemOut]
