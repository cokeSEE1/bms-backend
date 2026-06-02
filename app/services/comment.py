from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import CommentModel
from app.schemas.comment import CommentCreate, CommentListResponse, CommentOut


class CommentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_comment(self, req: CommentCreate, user_id: int) -> CommentOut:
        comment = await CommentModel.create(
            self.db,
            knowledge_id=req.knowledge_id,
            user_id=user_id,
            content=req.content,
        )
        return CommentOut.model_validate(comment)

    async def list_comments(
        self, knowledge_id: int, page: int = 1, page_size: int = 20,
    ) -> CommentListResponse:
        offset = (page - 1) * page_size
        total, items = await CommentModel.list_by_knowledge(
            self.db, knowledge_id, limit=page_size, offset=offset,
        )
        return CommentListResponse(
            total=total,
            items=[CommentOut.model_validate(item) for item in items],
        )

    async def delete_comment(self, comment_id: int) -> None:
        comment = await CommentModel.get_by_id(self.db, comment_id)
        if comment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="评论不存在",
            )
        await CommentModel.soft_delete(self.db, comment_id)
