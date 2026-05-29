from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.entities.knowledge_base import KnowledgeBase


class KnowledgeBaseModel:
    _entity = KnowledgeBase

    @staticmethod
    async def get_by_id(db: AsyncSession, kb_id: int) -> KnowledgeBase | None:
        result = await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id,
                KnowledgeBase.is_delete == 0,
            ),
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_list(
        db: AsyncSession,
        *,
        appid: int | None = None,
        kb_type: int | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[int, list[KnowledgeBase]]:
        conditions = [KnowledgeBase.is_delete == 0]
        if appid is not None:
            conditions.append(KnowledgeBase.appid == appid)
        if kb_type is not None:
            conditions.append(KnowledgeBase.kb_type == kb_type)

        count_stmt = select(func.count()).select_from(KnowledgeBase).where(*conditions)
        total = (await db.execute(count_stmt)).scalar() or 0

        items_stmt = (
            select(KnowledgeBase)
            .where(*conditions)
            .order_by(
                KnowledgeBase.is_top.desc(),
                KnowledgeBase.update_time.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        items = (await db.execute(items_stmt)).scalars().all()
        return total, list(items)

    @staticmethod
    async def create(db: AsyncSession, **kwargs) -> KnowledgeBase:
        kb = KnowledgeBase(**kwargs)
        db.add(kb)
        await db.commit()
        await db.refresh(kb)
        return kb
