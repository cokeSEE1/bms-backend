from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_directory_service
from app.entities.user import User
from app.schemas.directory import DirectoryCreateRequest, DirectoryDeleteRequest, DirectoryDeleteResponse, DirectoryTreeOut, DirectoryTreeRequest, DirectoryUpdateRequest
from app.services.knowledge_directory import KnowledgeDirectoryService

router = APIRouter(prefix="/v1/directory")


@router.post("/tree", response_model=DirectoryTreeOut)
async def get_directory_tree(
    body: DirectoryTreeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[KnowledgeDirectoryService, Depends(get_directory_service)],
) -> DirectoryTreeOut:
    return await service.get_tree(body.dir_id, body.level)


@router.get("/trees", response_model=list[DirectoryTreeOut])
async def get_all_trees(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[KnowledgeDirectoryService, Depends(get_directory_service)],
) -> list[DirectoryTreeOut]:
    return await service.get_all_trees()


@router.post("/node", response_model=DirectoryTreeOut, status_code=200)
async def create_directory_node(
    body: DirectoryCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[KnowledgeDirectoryService, Depends(get_directory_service)],
) -> DirectoryTreeOut:
    return await service.add_node(body)


@router.delete("/node", response_model=DirectoryDeleteResponse)
async def delete_directory_node(
    body: DirectoryDeleteRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[KnowledgeDirectoryService, Depends(get_directory_service)],
) -> DirectoryDeleteResponse:
    return await service.delete_node(body)


@router.put("/node", response_model=DirectoryTreeOut)
async def update_directory_node(
    body: DirectoryUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[KnowledgeDirectoryService, Depends(get_directory_service)],
) -> DirectoryTreeOut:
    return await service.update_node(body)
