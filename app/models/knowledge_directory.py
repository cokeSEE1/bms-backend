from sqlalchemy import func, select, update
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
        return await KnowledgeDirectoryModel.get_subtree_nodes(db, root)

    @staticmethod
    async def get_subtree_nodes(
        db: AsyncSession, node: KnowledgeDirectory
    ) -> list[KnowledgeDirectory]:
        """获取某个节点及其所有子孙节点（通过 MPTT lft/rgt 范围查询）"""
        stmt = (
            select(KnowledgeDirectory)
            .where(
                KnowledgeDirectory.tree_id == node.tree_id,
                KnowledgeDirectory.lft >= node.lft,
                KnowledgeDirectory.rgt <= node.rgt,
                KnowledgeDirectory.is_delete == 0,
            )
            .order_by(KnowledgeDirectory.lft)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def soft_delete_nodes(
        db: AsyncSession, node_ids: list[int], delete_type: int
    ) -> None:
        """批量软删除目录节点"""
        if not node_ids:
            return
        await db.execute(
            update(KnowledgeDirectory)
            .where(
                KnowledgeDirectory.id.in_(node_ids),
                KnowledgeDirectory.is_delete == 0,
            )
            .values(is_delete=delete_type)
        )
        await db.commit()

    @staticmethod
    async def update_node(
        db: AsyncSession, dir_id: int, dir_name: str
    ) -> KnowledgeDirectory | None:
        """更新目录节点名称"""
        await db.execute(
            update(KnowledgeDirectory)
            .where(
                KnowledgeDirectory.id == dir_id,
                KnowledgeDirectory.is_delete == 0,
            )
            .values(dir_name=dir_name)
        )
        await db.commit()
        return await KnowledgeDirectoryModel.get_by_id(db, dir_id)

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

    @staticmethod
    async def create_node(
        db: AsyncSession,
        parent: KnowledgeDirectory,
        dir_name: str,
        dir_type: int,
        km_id: int | None = None,
    ) -> KnowledgeDirectory:
        """在父节点末尾插入新子节点，自动 MPTT 重平衡"""
        tree_id = parent.tree_id
        new_lft = parent.rgt
        new_rgt = parent.rgt + 1
        new_level = parent.level + 1

        # 腾位置：rgt >= new_lft 的节点 rgt += 2
        await db.execute(
            update(KnowledgeDirectory)
            .where(
                KnowledgeDirectory.tree_id == tree_id,
                KnowledgeDirectory.rgt >= new_lft,
            )
            .values(rgt=KnowledgeDirectory.rgt + 2)
        )
        # 腾位置：lft > new_lft 的节点 lft += 2
        await db.execute(
            update(KnowledgeDirectory)
            .where(
                KnowledgeDirectory.tree_id == tree_id,
                KnowledgeDirectory.lft > new_lft,
            )
            .values(lft=KnowledgeDirectory.lft + 2)
        )

        directory = KnowledgeDirectory(
            appid=parent.appid,
            dir_name=dir_name,
            dir_type=dir_type,
            km_id=km_id,
            tree_id=tree_id,
            lft=new_lft,
            rgt=new_rgt,
            level=new_level,
            parent_id=parent.id,
        )
        db.add(directory)
        await db.commit()
        await db.refresh(directory)
        return directory
