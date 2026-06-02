from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_item import KnowledgeItemModel


@dataclass
class RankItemOut:
    rank: int
    name: str
    department: str
    count: int


class RankingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_ranking(self, field: str, limit: int = 10) -> list[RankItemOut]:
        items = await KnowledgeItemModel.get_top_by_field(self.db, field, limit)
        result = []
        for idx, item in enumerate(items):
            result.append(RankItemOut(
                rank=idx + 1,
                name=item.name,
                department=item.author or "未知",
                count=getattr(item, field, 0),
            ))
        return result

    async def get_reading_stars(self, limit: int = 10) -> list[RankItemOut]:
        return await self.get_ranking('view_count', limit)

    async def get_original_stars(self, limit: int = 10) -> list[RankItemOut]:
        return await self.get_ranking('favorite_count', limit)

    async def get_hot_stars(self, limit: int = 10) -> list[RankItemOut]:
        return await self.get_ranking('like_count', limit)
