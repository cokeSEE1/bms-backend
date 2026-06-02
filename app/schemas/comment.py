from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CommentCreate(BaseModel):
    knowledge_id: int = Field(..., description="知识条目ID")
    content: str = Field(..., min_length=1, max_length=2000, description="评论内容")


class CommentOut(BaseModel):
    id: int
    knowledge_id: int
    user_id: int
    content: str
    create_time: datetime
    update_time: datetime

    model_config = ConfigDict(from_attributes=True)


class CommentListResponse(BaseModel):
    total: int
    items: list[CommentOut]
