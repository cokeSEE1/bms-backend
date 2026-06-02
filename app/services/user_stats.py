from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_item import KnowledgeItemModel


@dataclass
class UserStatsOut:
    read_count: int       # 阅读量（自己的知识被阅读）
    original_count: int   # 原创量
    total_read_count: int # 被阅读量


class UserStatsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_stats(self, username: str) -> UserStatsOut:
        original_count = await KnowledgeItemModel.count_items_by_creator(self.db, username)
        total_read_count = await KnowledgeItemModel.sum_view_count_by_creator(self.db, username)
        return UserStatsOut(
            read_count=128,  # TODO: reading history tracking — placeholder for now
            original_count=original_count,
            total_read_count=total_read_count,
        )

    async def get_participated(self, username: str, limit: int = 10):
        items = await KnowledgeItemModel.list_participated(self.db, username, limit)
        return items
