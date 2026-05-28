from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.entities.knowledge_directory import KnowledgeDirectory


class KnowledgeDirectoryModel:
    _entity = KnowledgeDirectory

    @staticmethod
    async def get_by_id(db: AsyncSession, dir_id: int) -> KnowledgeDirectory | None:
        result = await db.execute(
            select(KnowledgeDirectory).where(
                KnowledgeDirectory.id == dir_id,
                KnowledgeDirectory.is_delete == 0,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_children(
        db: AsyncSession, parent_id: int | None, *, appid: int | None = None
    ) -> list[KnowledgeDirectory]:
        """获取指定节点的直接子节点"""
        conditions = [KnowledgeDirectory.is_delete == 0]
        if parent_id is None:
            conditions.append(KnowledgeDirectory.parent_id.is_(None))
        else:
            conditions.append(KnowledgeDirectory.parent_id == parent_id)
        if appid is not None:
            conditions.append(KnowledgeDirectory.appid == appid)

        stmt = (
            select(KnowledgeDirectory)
            .where(*conditions)
            .order_by(KnowledgeDirectory.lft)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_tree(
        db: AsyncSession, root_id: int
    ) -> list[KnowledgeDirectory]:
        """获取某个节点及其所有子孙节点（通过 lft/rgt 范围查询）"""
        root = await KnowledgeDirectoryModel.get_by_id(db, root_id)
        if root is None:
            return []

        stmt = (
            select(KnowledgeDirectory)
            .where(
                KnowledgeDirectory.tree_id == root.tree_id,
                KnowledgeDirectory.lft >= root.lft,
                KnowledgeDirectory.rgt <= root.rgt,
                KnowledgeDirectory.is_delete == 0,
            )
            .order_by(KnowledgeDirectory.lft)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_root_nodes(
        db: AsyncSession, *, appid: int | None = None
    ) -> list[KnowledgeDirectory]:
        """获取所有根节点（parent_id IS NULL）"""
        conditions = [
            KnowledgeDirectory.is_delete == 0,
            KnowledgeDirectory.parent_id.is_(None),
        ]
        if appid is not None:
            conditions.append(KnowledgeDirectory.appid == appid)

        stmt = (
            select(KnowledgeDirectory)
            .where(*conditions)
            .order_by(KnowledgeDirectory.lft)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def create(db: AsyncSession, **kwargs) -> KnowledgeDirectory:
        directory = KnowledgeDirectory(**kwargs)
        db.add(directory)
        await db.commit()
        await db.refresh(directory)
        return directory
