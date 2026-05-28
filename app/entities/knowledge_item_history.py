from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.entities.base import BaseEntity


class KnowledgeItemHistory(BaseEntity):
    __tablename__ = "kms_knowledge_item_history"
    __table_args__ = {"comment": "知识版本历史表"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    knowledge_id: Mapped[int] = mapped_column(Integer, comment="知识id", index=True)
    kb_id: Mapped[int] = mapped_column(Integer, comment="所属知识库id")
    appid: Mapped[int] = mapped_column(Integer, comment="应用id")
    name: Mapped[str] = mapped_column(String(255), comment="知识名称")
    content: Mapped[str | None] = mapped_column(Text, comment="知识内容快照")
    abstract: Mapped[str | None] = mapped_column(Text, comment="知识摘要")
    version: Mapped[int] = mapped_column(Integer, comment="版本号")
    current_use: Mapped[int] = mapped_column(Integer, default=0, comment="是否当前版本：0-否，1-是")
    create_user: Mapped[str] = mapped_column(String(255), comment="此版本创建人")
    tag_ids: Mapped[str | None] = mapped_column(String(255), comment="标签ids")
    attachment_ids: Mapped[str | None] = mapped_column(String(255), comment="附件ids")
    status: Mapped[int] = mapped_column(
        Integer, default=1,
        comment="知识状态：1-拟稿 2-审核中 3-已发布 4-已下线",
    )
    name_sort_key: Mapped[str | None] = mapped_column(String(255), comment="名称拼音首字母")
