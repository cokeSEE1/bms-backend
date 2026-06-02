from pypinyin import lazy_pinyin
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.entities.knowledge_item import KnowledgeItem


class KnowledgeItemModel:
    _entity = KnowledgeItem

    @staticmethod
    async def get_by_id(db: AsyncSession, item_id: int) -> KnowledgeItem | None:
        result = await db.execute(
            select(KnowledgeItem).where(
                KnowledgeItem.id == item_id,
                KnowledgeItem.is_delete == 0,
            ),
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_list_by_kb_id(
        db: AsyncSession, kb_id: int, *, limit: int = 20, offset: int = 0,
    ) -> tuple[int, list[KnowledgeItem]]:
        conditions = [KnowledgeItem.kb_id == kb_id, KnowledgeItem.is_delete == 0]
        count_stmt = (
            select(func.count())
            .select_from(KnowledgeItem)
            .where(*conditions)
        )
        total = (await db.execute(count_stmt)).scalar() or 0

        items_stmt = (
            select(KnowledgeItem)
            .where(*conditions)
            .order_by(
                KnowledgeItem.is_top.desc(),
                KnowledgeItem.update_time.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        items = (await db.execute(items_stmt)).scalars().all()
        return total, list(items)

    @staticmethod
    async def create(db: AsyncSession, **kwargs) -> KnowledgeItem:
        if "name" in kwargs and not kwargs.get("name_sort_key"):
            kwargs["name_sort_key"] = "".join(
                lazy_pinyin(str(kwargs["name"])),
            )[:200]
        item = KnowledgeItem(**kwargs)
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return item

    @staticmethod
    async def soft_delete(db: AsyncSession, item_id: int) -> None:
        stmt = (
            update(KnowledgeItem)
            .where(KnowledgeItem.id == item_id)
            .values(is_delete=1)
        )
        await db.execute(stmt)
        await db.commit()

    @staticmethod
    async def update_item(
        db: AsyncSession, item_id: int, **kwargs,
    ) -> KnowledgeItem | None:
        if "name" in kwargs and not kwargs.get("name_sort_key"):
            kwargs["name_sort_key"] = "".join(
                lazy_pinyin(str(kwargs["name"])),
            )[:200]
        await db.execute(
            update(KnowledgeItem)
            .where(KnowledgeItem.id == item_id, KnowledgeItem.is_delete == 0)
            .values(**kwargs),
        )
        await db.commit()
        return await KnowledgeItemModel.get_by_id(db, item_id)

    @staticmethod
    async def get_list_with_filters(
        db: AsyncSession,
        *,
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
    ) -> tuple[int, list[KnowledgeItem]]:
        conditions = [KnowledgeItem.is_delete == 0]

        if cate_id is not None:
            conditions.append(KnowledgeItem.cate_id == cate_id)
        if cate_ids is not None:
            conditions.append(KnowledgeItem.cate_id.in_(cate_ids))
        if status is not None:
            conditions.append(KnowledgeItem.status == status)
        if author is not None:
            conditions.append(KnowledgeItem.author == author)
        if search is not None:
            conditions.append(
                KnowledgeItem.name.like(f"%{search}%"),
            )
        if start_time is not None:
            conditions.append(KnowledgeItem.update_time >= start_time)
        if end_time is not None:
            conditions.append(KnowledgeItem.update_time <= end_time)

        count_stmt = select(func.count()).select_from(KnowledgeItem).where(*conditions)
        total = (await db.execute(count_stmt)).scalar() or 0

        sort_mapping = {
            1: KnowledgeItem.favorite_count,
            2: KnowledgeItem.last_release_time,
            3: KnowledgeItem.create_time,
            4: KnowledgeItem.view_count,
            5: KnowledgeItem.name_sort_key,
            6: KnowledgeItem.sort_order,
        }
        sort_col = sort_mapping.get(sort_by, KnowledgeItem.is_top)
        if order_by == 0:
            sort_col = sort_col.desc()
        else:
            sort_col = sort_col.asc()

        items_stmt = (
            select(KnowledgeItem)
            .where(*conditions)
            .order_by(KnowledgeItem.is_top.desc(), sort_col, KnowledgeItem.update_time.desc())
            .limit(limit)
            .offset(offset)
        )
        items = (await db.execute(items_stmt)).scalars().all()
        return total, list(items)

    @staticmethod
    async def increment_view_count(db: AsyncSession, item_id: int) -> None:
        await db.execute(
            update(KnowledgeItem)
            .where(KnowledgeItem.id == item_id, KnowledgeItem.is_delete == 0)
            .values(view_count=KnowledgeItem.view_count + 1),
        )
        await db.commit()

    @staticmethod
    async def increment_like_count(db: AsyncSession, item_id: int) -> None:
        await db.execute(
            update(KnowledgeItem)
            .where(KnowledgeItem.id == item_id, KnowledgeItem.is_delete == 0)
            .values(like_count=KnowledgeItem.like_count + 1),
        )
        await db.commit()

    @staticmethod
    async def decrement_like_count(db: AsyncSession, item_id: int) -> None:
        await db.execute(
            update(KnowledgeItem)
            .where(KnowledgeItem.id == item_id, KnowledgeItem.is_delete == 0)
            .values(like_count=KnowledgeItem.like_count - 1),
        )
        await db.commit()

    @staticmethod
    async def increment_favorite_count(db: AsyncSession, item_id: int) -> None:
        await db.execute(
            update(KnowledgeItem)
            .where(KnowledgeItem.id == item_id, KnowledgeItem.is_delete == 0)
            .values(favorite_count=KnowledgeItem.favorite_count + 1),
        )
        await db.commit()

    @staticmethod
    async def decrement_favorite_count(db: AsyncSession, item_id: int) -> None:
        await db.execute(
            update(KnowledgeItem)
            .where(KnowledgeItem.id == item_id, KnowledgeItem.is_delete == 0)
            .values(favorite_count=KnowledgeItem.favorite_count - 1),
        )
        await db.commit()

    @staticmethod
    async def count_items_by_creator(db: AsyncSession, creator: str) -> int:
        """统计某用户创建的知识条目数"""
        from app.entities.knowledge_item import KnowledgeItem

        stmt = select(func.count()).select_from(KnowledgeItem).where(
            KnowledgeItem.creator == creator,
            KnowledgeItem.is_delete == 0,
        )
        result = await db.execute(stmt)
        return result.scalar() or 0

    @staticmethod
    async def sum_view_count_by_creator(db: AsyncSession, creator: str) -> int:
        """统计某用户创建的知识条目总阅读量"""
        from app.entities.knowledge_item import KnowledgeItem

        stmt = (
            select(func.coalesce(func.sum(KnowledgeItem.view_count), 0))
            .select_from(KnowledgeItem)
            .where(
                KnowledgeItem.creator == creator,
                KnowledgeItem.is_delete == 0,
            )
        )
        result = await db.execute(stmt)
        return result.scalar() or 0

    @staticmethod
    async def list_participated(
        db: AsyncSession, creator: str, limit: int = 10,
    ) -> list[KnowledgeItem]:
        """获取用户参与的知识列表（按更新时间倒序）"""
        from app.entities.knowledge_item import KnowledgeItem

        stmt = (
            select(KnowledgeItem)
            .where(KnowledgeItem.creator == creator, KnowledgeItem.is_delete == 0)
            .order_by(KnowledgeItem.update_time.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_top_by_field(
        db: AsyncSession,
        field: str,  # 'view_count' | 'like_count' | 'favorite_count'
        limit: int = 10,
    ) -> list:
        """获取指定字段排名前N的知识条目"""
        from sqlalchemy import desc, select
        from app.entities.knowledge_item import KnowledgeItem

        allowed = {'view_count', 'like_count', 'favorite_count'}
        if field not in allowed:
            raise ValueError(f"Invalid ranking field: {field}")

        col = getattr(KnowledgeItem, field)
        stmt = (
            select(KnowledgeItem)
            .where(KnowledgeItem.is_delete == 0, KnowledgeItem.status == 3)
            .order_by(desc(col))
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def increment_share_num(db: AsyncSession, item_id: int) -> None:
        await db.execute(
            update(KnowledgeItem)
            .where(KnowledgeItem.id == item_id, KnowledgeItem.is_delete == 0)
            .values(share_num=KnowledgeItem.share_num + 1),
        )
        await db.commit()
