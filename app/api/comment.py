from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_comment_service, get_current_user
from app.entities.user import User
from app.schemas.comment import CommentCreate, CommentListResponse, CommentOut
from app.services.comment import CommentService

router = APIRouter(prefix="/v1/comments")


@router.post("", response_model=CommentOut, status_code=201)
async def create_comment(
    body: CommentCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CommentService, Depends(get_comment_service)],
) -> CommentOut:
    return await service.create_comment(body, current_user.id)


@router.get("", response_model=CommentListResponse)
async def list_comments(
    knowledge_id: Annotated[int, Query(description="知识条目ID")],
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CommentService, Depends(get_comment_service)],
    page: Annotated[int, Query(ge=1, description="页码")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="每页条数")] = 20,
) -> CommentListResponse:
    return await service.list_comments(knowledge_id, page, page_size)


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CommentService, Depends(get_comment_service)],
) -> None:
    await service.delete_comment(comment_id)
