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
