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
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_list_by_kb_id(
        db: AsyncSession, kb_id: int, *, limit: int = 20, offset: int = 0
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
                lazy_pinyin(str(kwargs["name"]))
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
