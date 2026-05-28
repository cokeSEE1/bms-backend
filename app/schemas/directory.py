from pydantic import BaseModel, ConfigDict, Field


class DirectoryTreeRequest(BaseModel):
    dir_id: int = Field(..., description="根目录id")
    level: int = Field(..., ge=-1, le=1, description="-1=完整树, 1=直接子节点")


class DirectoryTreeOut(BaseModel):
    id: int
    dir_name: str
    dir_type: int
    level: int
    parent_id: int | None
    children: list["DirectoryTreeOut"] = []

    model_config = ConfigDict(from_attributes=True)
