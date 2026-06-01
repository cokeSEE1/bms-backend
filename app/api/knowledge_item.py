from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_user, get_knowledge_item_service
from app.entities.user import User
from app.schemas.knowledge_item import (
    KnowledgeItemCreate,
    KnowledgeItemDetailOut,
    KnowledgeItemListResponse,
    KnowledgeItemOut,
    KnowledgeItemUpdate,
)
from app.services.knowledge_item import KnowledgeItemService

router = APIRouter(prefix="/v1/knowledge")


@router.get("/detail", response_model=KnowledgeItemDetailOut)
async def get_knowledge_detail(
    knowledge_id: Annotated[int, Query(description="知识条目ID")],
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[KnowledgeItemService, Depends(get_knowledge_item_service)],
) -> KnowledgeItemDetailOut:
    return await service.get_detail(knowledge_id, current_user)


@router.post("/item", response_model=KnowledgeItemOut, status_code=201)
async def create_knowledge_item(
    body: KnowledgeItemCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[KnowledgeItemService, Depends(get_knowledge_item_service)],
) -> KnowledgeItemOut:
    return await service.create_item(body, appid=0, creator=current_user.username)


@router.get("/item/{item_id}", response_model=KnowledgeItemOut)
async def get_knowledge_item(
    item_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[KnowledgeItemService, Depends(get_knowledge_item_service)],
) -> KnowledgeItemOut:
    return await service.get_item(item_id)


@router.put("/item/{item_id}", response_model=KnowledgeItemOut)
async def update_knowledge_item(
    item_id: int,
    body: KnowledgeItemUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[KnowledgeItemService, Depends(get_knowledge_item_service)],
) -> KnowledgeItemOut:
    return await service.update_item(item_id, body)


@router.delete("/item/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_item(
    item_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[KnowledgeItemService, Depends(get_knowledge_item_service)],
) -> None:
    await service.delete_item(item_id)


@router.get("/list", response_model=KnowledgeItemListResponse)
async def list_knowledge_items(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[KnowledgeItemService, Depends(get_knowledge_item_service)],
    cate_id: Annotated[int | None, Query(description="目录id")] = None,
    search: Annotated[str | None, Query(description="关键词搜索")] = None,
    status: Annotated[
        int | None,
        Query(ge=1, le=4, description="1-拟稿 2-审核中 3-已发布 4-已下线"),
    ] = None,
    author: Annotated[str | None, Query(description="作者")] = None,
    sort_by: Annotated[
        int | None,
        Query(ge=0, le=6, description="排序: 0-推荐 1-收藏 2-上线 3-创建 4-阅读 5-拼音 6-自定义"),
    ] = None,
    order_by: Annotated[int | None, Query(ge=0, le=1, description="0-倒序 1-顺序")] = None,
    start_time: Annotated[str | None, Query(description="更新时间开始")] = None,
    end_time: Annotated[str | None, Query(description="更新时间结束")] = None,
    page: Annotated[int, Query(ge=1, description="页码")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="每页条数")] = 20,
    recursive: Annotated[bool, Query(description="是否递归查询子目录")] = False,
) -> KnowledgeItemListResponse:
    offset = (page - 1) * page_size
    return await service.list_items(
        cate_id=cate_id,
        search=search,
        status=status,
        author=author,
        sort_by=sort_by,
        order_by=order_by,
        start_time=start_time,
        end_time=end_time,
        recursive=recursive,
        limit=page_size,
        offset=offset,
    )
