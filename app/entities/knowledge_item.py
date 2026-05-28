from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.entities.base import BaseEntity


class KnowledgeItem(BaseEntity):
    __tablename__ = "kms_knowledge_item"
    __table_args__ = {"comment": "知识详情表"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # ── 身份标识 ──
    appid: Mapped[int] = mapped_column(Integer, comment="应用id", index=True)
    kb_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="所属知识库id", index=True)
    cate_id: Mapped[int | None] = mapped_column(Integer, comment="目录id")

    # ── 内容核心 ──
    name: Mapped[str] = mapped_column(String(255), comment="知识名称")
    content: Mapped[str | None] = mapped_column(Text, comment="知识内容（富文本）")
    abstract: Mapped[str | None] = mapped_column(Text, comment="知识摘要")
    author: Mapped[str | None] = mapped_column(String(255), comment="作者")

    # ── 人员信息 ──
    creator: Mapped[str] = mapped_column(String(255), comment="创建人", index=True)
    last_modify_user: Mapped[str | None] = mapped_column(String(255), comment="最新编辑人")

    # ── 版本发布 ──
    version: Mapped[int] = mapped_column(Integer, default=0, comment="当前版本号")
    max_version: Mapped[int] = mapped_column(Integer, default=0, comment="最大版本号")
    status: Mapped[int] = mapped_column(
        Integer, default=1,
        comment="知识状态：1-拟稿 2-审核中 3-已发布 4-已下线",
    )
    is_online: Mapped[int] = mapped_column(Integer, default=0, comment="是否上线", index=True)
    first_release_time: Mapped[datetime | None] = mapped_column(DateTime, comment="首次发布时间")
    last_release_time: Mapped[datetime | None] = mapped_column(DateTime, comment="最后发布时间")

    # ── 统计计数 ──
    view_count: Mapped[int] = mapped_column(Integer, default=0, comment="浏览量")
    like_count: Mapped[int] = mapped_column(Integer, default=0, comment="点赞数")
    favorite_count: Mapped[int] = mapped_column(Integer, default=0, comment="收藏数")
    share_num: Mapped[int] = mapped_column(Integer, default=0, comment="分享数")
    download_num: Mapped[int] = mapped_column(Integer, default=0, comment="下载数")

    # ── 排序展示 ──
    is_top: Mapped[int] = mapped_column(Integer, default=0, comment="是否置顶：0-否，1-是")
    sort_order: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="自定义排序号")
    name_sort_key: Mapped[str | None] = mapped_column(String(255), comment="名称拼音首字母")

    # ── 扩展元数据 ──
    tag_ids: Mapped[str | None] = mapped_column(String(255), comment="标签ids，逗号分隔")
    attachment_ids: Mapped[str | None] = mapped_column(String(255), comment="附件ids，逗号分隔")
    knowledge_type: Mapped[int] = mapped_column(
        Integer, default=0, comment="知识类型：0-富文本 1-纯文本 2-文件",
    )
    dir_type: Mapped[int] = mapped_column(
        Integer, default=2, comment="类型：0-富文本知识 1-分组 2-文件",
    )
