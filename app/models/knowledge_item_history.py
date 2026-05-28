from pypinyin import lazy_pinyin
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.entities.knowledge_item_history import KnowledgeItemHistory


class KnowledgeItemHistoryModel:
    _entity = KnowledgeItemHistory

    @staticmethod
    async def get_by_knowledge_id(
        db: AsyncSession, knowledge_id: int
    ) -> list[KnowledgeItemHistory]:
        stmt = (
            select(KnowledgeItemHistory)
            .where(
                KnowledgeItemHistory.knowledge_id == knowledge_id,
                KnowledgeItemHistory.is_delete == 0,
            )
            .order_by(KnowledgeItemHistory.version.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def create(db: AsyncSession, **kwargs) -> KnowledgeItemHistory:
        if "name" in kwargs and not kwargs.get("name_sort_key"):
            kwargs["name_sort_key"] = "".join(
                lazy_pinyin(str(kwargs["name"]))
            )[:200]
        history = KnowledgeItemHistory(**kwargs)
        db.add(history)
        await db.commit()
        await db.refresh(history)
        return history
