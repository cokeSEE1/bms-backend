from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.entities.comment import Comment


class CommentModel:
    _entity = Comment

    @staticmethod
    async def get_by_id(db: AsyncSession, comment_id: int) -> Comment | None:
        result = await db.execute(
            select(Comment).where(Comment.id == comment_id, Comment.is_delete == 0),
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        db: AsyncSession, knowledge_id: int, user_id: int, content: str,
    ) -> Comment:
        comment = Comment(knowledge_id=knowledge_id, user_id=user_id, content=content)
        db.add(comment)
        await db.commit()
        await db.refresh(comment)
        return comment

    @staticmethod
    async def list_by_knowledge(
        db: AsyncSession, knowledge_id: int, *, limit: int = 20, offset: int = 0,
    ) -> tuple[int, list[Comment]]:
        conditions = [Comment.knowledge_id == knowledge_id, Comment.is_delete == 0]
        count_stmt = select(func.count()).select_from(Comment).where(*conditions)
        total = (await db.execute(count_stmt)).scalar() or 0

        items_stmt = (
            select(Comment)
            .where(*conditions)
            .order_by(Comment.create_time.desc())
            .limit(limit)
            .offset(offset)
        )
        items = (await db.execute(items_stmt)).scalars().all()
        return total, list(items)

    @staticmethod
    async def soft_delete(db: AsyncSession, comment_id: int) -> None:
        await db.execute(
            update(Comment).where(Comment.id == comment_id).values(is_delete=1),
        )
        await db.commit()
