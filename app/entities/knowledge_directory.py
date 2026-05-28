from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.entities.base import BaseEntity


class KnowledgeDirectory(BaseEntity):
    __tablename__ = "kms_knowledge_directory"
    __table_args__ = {"comment": "知识目录表"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    appid: Mapped[int] = mapped_column(Integer, comment="应用id", index=True)
    dir_name: Mapped[str] = mapped_column(String(256), comment="目录名称")
    km_id: Mapped[int | None] = mapped_column(Integer, comment="关联知识id")
    dir_type: Mapped[int] = mapped_column(
        Integer, default=0, comment="目录类型：0-目录，1-分组"
    )
    # MPTT 树形结构字段
    tree_id: Mapped[int] = mapped_column(Integer, default=0, comment="MPTT树id")
    lft: Mapped[int] = mapped_column(Integer, default=0, comment="MPTT左值")
    rgt: Mapped[int] = mapped_column(Integer, default=0, comment="MPTT右值")
    level: Mapped[int] = mapped_column(Integer, default=0, comment="MPTT层级")
    parent_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="父目录id")
