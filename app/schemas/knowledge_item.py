from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeItemCreate(BaseModel):
    kb_id: int = Field(..., description="所属知识库id")
    cate_id: int | None = Field(None, description="目录id")
    name: str = Field(..., min_length=1, max_length=255, description="知识名称")
    content: str | None = Field(None, description="知识内容（富文本）")
    abstract: str | None = Field(None, description="知识摘要")
    author: str | None = Field(None, description="作者")
    knowledge_type: int = Field(default=0, ge=0, le=2, description="0-富文本 1-纯文本 2-文件")
    dir_type: int = Field(default=2, ge=0, le=2, description="0-富文本知识 1-分组 2-文件")
    tag_ids: str | None = Field(None, description="标签ids，逗号分隔")
    attachment_ids: str | None = Field(None, description="附件ids，逗号分隔")


class KnowledgeItemUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255, description="知识名称")
    content: str | None = Field(None, description="知识内容")
    abstract: str | None = Field(None, description="知识摘要")
    cate_id: int | None = Field(None, description="目录id")
    author: str | None = Field(None, description="作者")
    knowledge_type: int | None = Field(None, ge=0, le=2, description="知识类型")
    tag_ids: str | None = Field(None, description="标签ids，逗号分隔")
    attachment_ids: str | None = Field(None, description="附件ids，逗号分隔")


class KnowledgeItemOut(BaseModel):
    id: int
    appid: int
    kb_id: int
    cate_id: int | None
    name: str
    content: str | None
    abstract: str | None
    author: str | None
    creator: str
    last_modify_user: str | None
    version: int
    max_version: int
    status: int
    is_online: int
    first_release_time: datetime | None
    last_release_time: datetime | None
    view_count: int
    like_count: int
    favorite_count: int
    share_num: int
    download_num: int
    is_top: int
    sort_order: int | None
    name_sort_key: str | None
    knowledge_type: int
    dir_type: int
    tag_ids: str | None
    attachment_ids: str | None
    create_time: datetime
    update_time: datetime

    model_config = ConfigDict(from_attributes=True)


class KnowledgeItemListResponse(BaseModel):
    total: int
    items: list[KnowledgeItemOut]
