from pydantic import BaseModel, ConfigDict, Field


class DirectoryTreeRequest(BaseModel):
    dir_id: int = Field(..., description="根目录id")
    level: int = Field(..., ge=-1, le=1, description="-1=完整树, 1=直接子节点")


class DirectoryCreateRequest(BaseModel):
    parent_id: int = Field(..., description="父目录id")
    dir_name: str = Field(..., min_length=1, max_length=256, description="目录名称")
    dir_type: int = Field(..., ge=0, le=1, description="0=目录, 1=分组")
    km_id: int | None = Field(None, description="关联知识id")


class DirectoryDeleteRequest(BaseModel):
    dir_id: int = Field(..., description="要删除的目录节点id")
    delete_type: int = Field(..., ge=1, le=2, description="1=软删除(可恢复), 2=彻底删除(不可恢复)")


class DirectoryUpdateRequest(BaseModel):
    dir_id: int = Field(..., description="要更新的目录节点id")
    dir_name: str = Field(..., min_length=1, max_length=256, description="新目录名称")


class DirectoryTreeOut(BaseModel):
    id: int
    dir_name: str
    dir_type: int
    level: int
    parent_id: int | None
    children: list["DirectoryTreeOut"] = []

    model_config = ConfigDict(from_attributes=True)


class DirectoryDeleteResponse(BaseModel):
    deleted_count: int
    deleted_ids: list[int]
    dir_name: str
