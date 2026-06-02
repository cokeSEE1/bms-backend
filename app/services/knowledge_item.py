from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.entities.user import User
from app.models.knowledge_base import KnowledgeBaseModel
from app.models.knowledge_item import KnowledgeItemModel
from app.models.user import UserModel
from app.schemas.knowledge_item import (
    KnowledgeItemCreate,
    KnowledgeItemDetailOut,
    KnowledgeItemListResponse,
    KnowledgeItemOut,
    KnowledgeItemUpdate,
    PathNode,
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
        self, req: KnowledgeItemCreate, appid: int, creator: str,
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
            status=req.status,
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
        recursive: bool = False,
    ) -> KnowledgeItemListResponse:
        resolved_cate_ids: list[int] | None = cate_ids
        if recursive and cate_id is not None:
            from app.models.knowledge_directory import KnowledgeDirectoryModel

            directory = await KnowledgeDirectoryModel.get_by_id(self.db, cate_id)
            if directory is None:
                raise HTTPException(
                    status_code=404,
                    detail="目录不存在",
                )
            subtree_nodes = await KnowledgeDirectoryModel.get_subtree_nodes(self.db, directory)
            resolved_cate_ids = [node.id for node in subtree_nodes]
            if not resolved_cate_ids:
                return KnowledgeItemListResponse(total=0, items=[])

        total, items = await KnowledgeItemModel.get_list_with_filters(
            self.db,
            cate_id=cate_id if not recursive else None,
            cate_ids=resolved_cate_ids,
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

    async def toggle_like(self, item_id: int, action: str) -> KnowledgeItemOut:
        item = await KnowledgeItemModel.get_by_id(self.db, item_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识条目不存在")
        if action == "like":
            await KnowledgeItemModel.increment_like_count(self.db, item_id)
        else:
            await KnowledgeItemModel.decrement_like_count(self.db, item_id)
        return KnowledgeItemOut.model_validate(await KnowledgeItemModel.get_by_id(self.db, item_id))

    async def toggle_favorite(self, item_id: int, action: str) -> KnowledgeItemOut:
        item = await KnowledgeItemModel.get_by_id(self.db, item_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识条目不存在")
        if action == "favorite":
            await KnowledgeItemModel.increment_favorite_count(self.db, item_id)
        else:
            await KnowledgeItemModel.decrement_favorite_count(self.db, item_id)
        return KnowledgeItemOut.model_validate(await KnowledgeItemModel.get_by_id(self.db, item_id))

    async def share_item(self, item_id: int) -> KnowledgeItemOut:
        item = await KnowledgeItemModel.get_by_id(self.db, item_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识条目不存在")
        await KnowledgeItemModel.increment_share_num(self.db, item_id)
        return KnowledgeItemOut.model_validate(await KnowledgeItemModel.get_by_id(self.db, item_id))

    async def search_items(
        self,
        keyword: str,
        cate_id: int | None = None,
        status: int | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[int, list]:
        """搜索知识条目（优先 ES，降级 MySQL LIKE）"""
        from app.services.es_search import search_knowledge_items

        result = await search_knowledge_items(
            keyword=keyword,
            cate_id=cate_id,
            status=status,
            limit=limit,
            offset=offset,
        )

        if result is not None:
            total, ids = result
            if not ids:
                return 0, []
            items = []
            for item_id in ids:
                try:
                    item = await self.get_item(item_id)
                    items.append(item)
                except Exception:
                    pass
            return total, items

        # ES 不可达，降级 MySQL LIKE
        response = await self.list_items(
            search=keyword,
            cate_id=cate_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        return response.total, response.items

    async def get_detail(self, knowledge_id: int, current_user: User) -> KnowledgeItemDetailOut:
        item = await KnowledgeItemModel.get_by_id(self.db, knowledge_id)
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="知识条目不存在",
            )

        # 提取 item 数据（必须在 commit 之前，避免 MissingGreenlet）
        item_data = KnowledgeItemOut.model_validate(item).model_dump()

        # 获取知识库名称
        kb_name = ""
        if item.kb_id:
            kb = await KnowledgeBaseModel.get_by_id(self.db, item.kb_id)
            if kb:
                kb_name = kb.name

        # 获取面包屑路径（MPTT 上溯）
        knowledge_path: list[PathNode] = []
        if item.cate_id:
            from app.models.knowledge_directory import KnowledgeDirectoryModel

            dir_node = await KnowledgeDirectoryModel.get_by_id(self.db, item.cate_id)
            if dir_node:
                ancestors = await KnowledgeDirectoryModel.get_ancestors(self.db, dir_node)
                knowledge_path = [
                    PathNode(dir_id=n.id, dir_name=n.dir_name, dir_type=n.dir_type)
                    for n in ancestors
                ]

        # 递增浏览数
        await KnowledgeItemModel.increment_view_count(self.db, knowledge_id)

        creator_user_info = None
        if item.creator:
            creator_user = await UserModel.get_by_username(self.db, item.creator)
            if creator_user:
                creator_user_info = {"username": creator_user.username}

        last_modify_user_info = None
        if item.last_modify_user:
            modifier = await UserModel.get_by_username(self.db, item.last_modify_user)
            if modifier:
                last_modify_user_info = {"username": modifier.username}

        tag_names = item.tag_ids.split(",") if item.tag_ids else []

        is_edit = (item.creator == current_user.username)

        is_download = True

        return KnowledgeItemDetailOut(
            **item_data,
            kb_name=kb_name,
            knowledge_path=knowledge_path,
            creator_user_info=creator_user_info,
            last_modify_user_info=last_modify_user_info,
            tag_names=tag_names,
            is_edit=is_edit,
            is_download=is_download,
        )
