from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.entities.base import BaseEntity


class Comment(BaseEntity):
    __tablename__ = "kms_comment"
    __table_args__ = {"comment": "知识评论表"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    knowledge_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="知识条目ID")
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="评论用户ID")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="评论内容")
