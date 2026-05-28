from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.entities.base import BaseEntity


class KnowledgeBase(BaseEntity):
    __tablename__ = "kms_knowledge_base"
    __table_args__ = {"comment": "知识库表"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    appid: Mapped[int] = mapped_column(Integer, comment="应用id", index=True)
    name: Mapped[str] = mapped_column(String(255), comment="知识库名称")
    description: Mapped[str | None] = mapped_column(Text, comment="简介")
    cover: Mapped[str | None] = mapped_column(String(255), comment="封面图片路径")
    creator: Mapped[str] = mapped_column(String(255), comment="创建人")
    item_count: Mapped[int] = mapped_column(Integer, default=1, comment="知识数量")
    view_count: Mapped[int] = mapped_column(Integer, default=0, comment="浏览量")
    is_online: Mapped[int] = mapped_column(Integer, default=0, comment="是否发布：1-已发布，2-未发布")
    kb_type: Mapped[int] = mapped_column(Integer, default=0, comment="类型：0-个人，1-企业")
    is_top: Mapped[int] = mapped_column(Integer, default=0, comment="是否置顶：0-否，1-是")
    tag_ids: Mapped[str | None] = mapped_column(String(255), comment="标签ids，逗号分隔")
    cate_id: Mapped[int | None] = mapped_column(Integer, comment="根目录id")
