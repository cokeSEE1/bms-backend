from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_item import KnowledgeItemModel
from app.schemas.knowledge_item import (
    KnowledgeItemCreate,
    KnowledgeItemListResponse,
    KnowledgeItemOut,
    KnowledgeItemUpdate,
)
from app.services.es_sync import delete_from_es, sync_knowledge_item


class KnowledgeItemService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_item(self, item_id: int) -> KnowledgeItemOut:
        item = await KnowledgeItemModel.get_by_id(self.db, item_id)
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="知识条目不存在",
            )
        return KnowledgeItemOut.model_validate(item)

    async def create_item(
        self, req: KnowledgeItemCreate, appid: int, creator: str
    ) -> KnowledgeItemOut:
        item = await KnowledgeItemModel.create(
            self.db,
            appid=appid,
            creator=creator,
            kb_id=req.kb_id,
            cate_id=req.cate_id,
            name=req.name,
            content=req.content,
            abstract=req.abstract,
            author=req.author,
            knowledge_type=req.knowledge_type,
            dir_type=req.dir_type,
            tag_ids=req.tag_ids,
            attachment_ids=req.attachment_ids,
        )
        result = KnowledgeItemOut.model_validate(item)
        await sync_knowledge_item(item)
        return result

    async def update_item(self, item_id: int, req: KnowledgeItemUpdate) -> KnowledgeItemOut:
        update_data = req.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="没有需要更新的字段",
            )
        item = await KnowledgeItemModel.update_item(self.db, item_id, **update_data)
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="知识条目不存在",
            )
        result = KnowledgeItemOut.model_validate(item)
        await sync_knowledge_item(item)
        return result

    async def delete_item(self, item_id: int) -> None:
        item = await KnowledgeItemModel.get_by_id(self.db, item_id)
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="知识条目不存在",
            )
        await KnowledgeItemModel.soft_delete(self.db, item_id)
        await delete_from_es(item_id)

    async def list_items(
        self,
        cate_id: int | None = None,
        cate_ids: list[int] | None = None,
        search: str | None = None,
        status: int | None = None,
        author: str | None = None,
        sort_by: int | None = None,
        order_by: int | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> KnowledgeItemListResponse:
        total, items = await KnowledgeItemModel.get_list_with_filters(
            self.db,
            cate_id=cate_id,
            cate_ids=cate_ids,
            search=search,
            status=status,
            author=author,
            sort_by=sort_by,
            order_by=order_by,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )
        return KnowledgeItemListResponse(
            total=total,
            items=[KnowledgeItemOut.model_validate(item) for item in items],
        )
