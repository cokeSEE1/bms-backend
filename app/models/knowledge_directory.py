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

    # ==================== MPTT Move Helpers ====================

    @staticmethod
    async def _get_first_child(
        db: AsyncSession, parent_id: int
    ) -> KnowledgeDirectory | None:
        """获取父节点下第一个子节点（按 lft 排序）"""
        stmt = (
            select(KnowledgeDirectory)
            .where(
                KnowledgeDirectory.parent_id == parent_id,
                KnowledgeDirectory.is_delete == 0,
            )
            .order_by(KnowledgeDirectory.lft.asc())
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def _get_last_child(
        db: AsyncSession, parent_id: int
    ) -> KnowledgeDirectory | None:
        """获取父节点下最后一个子节点（按 lft 排序）"""
        stmt = (
            select(KnowledgeDirectory)
            .where(
                KnowledgeDirectory.parent_id == parent_id,
                KnowledgeDirectory.is_delete == 0,
            )
            .order_by(KnowledgeDirectory.lft.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def _get_left_sibling(
        db: AsyncSession, node: KnowledgeDirectory
    ) -> KnowledgeDirectory | None:
        """获取节点的左兄弟"""
        stmt = (
            select(KnowledgeDirectory)
            .where(
                KnowledgeDirectory.tree_id == node.tree_id,
                KnowledgeDirectory.parent_id == node.parent_id,
                KnowledgeDirectory.level == node.level,
                KnowledgeDirectory.lft < node.lft,
                KnowledgeDirectory.is_delete == 0,
            )
            .order_by(KnowledgeDirectory.lft.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def _get_children_count(
        db: AsyncSession, parent_id: int
    ) -> int:
        """获取父节点的直接子节点数量"""
        stmt = select(func.count()).where(
            KnowledgeDirectory.parent_id == parent_id,
            KnowledgeDirectory.is_delete == 0,
        )
        result = await db.execute(stmt)
        return result.scalar() or 0

    @staticmethod
    def _relative_direction(
        position: str,
        source: KnowledgeDirectory,
        target: KnowledgeDirectory,
    ) -> bool:
        """判断移动相对方向，True=向右移动，False=向左移动"""
        # 检查 source 是否是 target 的子孙
        is_descendant = (
            source.tree_id == target.tree_id
            and source.lft > target.lft
            and source.rgt < target.rgt
        )
        if is_descendant:
            # 当 source 在 target 内部时，left/first-child 表示向左
            return position not in ("left", "first-child")
        else:
            return source.rgt < target.rgt

    @staticmethod
    async def _calc_new_position(
        db: AsyncSession,
        direction: bool,
        position: str,
        source_width: int,
        target: KnowledgeDirectory,
    ) -> tuple[int, int, int, int | None]:
        """计算移动后新位置，返回 (new_left, new_right, new_level, new_parent_id)"""
        PADDING = 1

        if direction:  # 向右移动，从右侧边界计算
            if position in ("left", "right"):
                new_level = target.level
                new_parent_id = target.parent_id
                if position == "right":
                    new_right = target.rgt
                else:  # left
                    new_right = target.lft - PADDING
            else:  # first-child / last-child
                new_level = target.level + 1
                new_parent_id = target.id
                if position == "first-child":
                    first_child = await KnowledgeDirectoryModel._get_first_child(db, target.id)
                    if first_child is None:
                        new_right = target.rgt - PADDING
                    else:
                        new_right = first_child.lft - PADDING
                else:  # last-child
                    new_right = target.rgt - PADDING
            new_left = new_right - source_width
        else:  # 向左移动，从左侧边界计算
            if position in ("left", "right"):
                new_level = target.level
                new_parent_id = target.parent_id
                if position == "right":
                    new_left = target.rgt + PADDING
                else:  # left
                    new_left = target.lft
            else:  # first-child / last-child
                new_level = target.level + 1
                new_parent_id = target.id
                if position == "first-child":
                    new_left = target.lft + 1
                else:  # last-child
                    last_child = await KnowledgeDirectoryModel._get_last_child(db, target.id)
                    if last_child is None:
                        new_left = target.lft + 1
                    else:
                        new_left = last_child.rgt + PADDING
            new_right = new_left + source_width

        return new_left, new_right, new_level, new_parent_id

    @staticmethod
    async def _relative_direction_strategy(
        db: AsyncSession,
        direction: bool,
        source: KnowledgeDirectory,
        new_left: int,
        new_right: int,
        new_level: int,
        new_parent_id: int | None,
    ) -> None:
        """MPTT 移动核心：隐藏源节点 → 移动中间节点 → 恢复源节点"""
        PADDING = 1
        source_width = source.rgt - source.lft
        diff_level = new_level - source.level
        tree_id = source.tree_id
        source_left = source.lft
        source_right = source.rgt

        # 阶段1：隐藏源节点子树（lft/rgt 减去 source_right 变成负数）
        await db.execute(
            update(KnowledgeDirectory)
            .where(
                KnowledgeDirectory.tree_id == tree_id,
                KnowledgeDirectory.lft >= source_left,
                KnowledgeDirectory.rgt <= source_right,
            )
            .values(
                lft=KnowledgeDirectory.lft - source_right,
                rgt=KnowledgeDirectory.rgt - source_right,
            )
        )

        # 阶段2：移动受影响的中间节点
        if direction:  # 向右移动，中间节点左移
            await db.execute(
                update(KnowledgeDirectory)
                .where(
                    KnowledgeDirectory.tree_id == tree_id,
                    KnowledgeDirectory.lft.between(source_left, new_right),
                )
                .values(lft=KnowledgeDirectory.lft - source_width - PADDING)
            )
            await db.execute(
                update(KnowledgeDirectory)
                .where(
                    KnowledgeDirectory.tree_id == tree_id,
                    KnowledgeDirectory.rgt.between(source_left, new_right),
                )
                .values(rgt=KnowledgeDirectory.rgt - source_width - PADDING)
            )
        else:  # 向左移动，中间节点右移
            await db.execute(
                update(KnowledgeDirectory)
                .where(
                    KnowledgeDirectory.tree_id == tree_id,
                    KnowledgeDirectory.lft.between(new_left, source_right),
                )
                .values(lft=KnowledgeDirectory.lft + source_width + PADDING)
            )
            await db.execute(
                update(KnowledgeDirectory)
                .where(
                    KnowledgeDirectory.tree_id == tree_id,
                    KnowledgeDirectory.rgt.between(new_left, source_right),
                )
                .values(rgt=KnowledgeDirectory.rgt + source_width + PADDING)
            )

        # 阶段3：恢复源节点到新位置
        if direction:
            diff_value = new_right - source_right
        else:
            diff_value = new_left - source_left

        await db.execute(
            update(KnowledgeDirectory)
            .where(
                KnowledgeDirectory.tree_id == tree_id,
                KnowledgeDirectory.lft <= 0,
            )
            .values(
                lft=KnowledgeDirectory.lft + source_right + diff_value,
                rgt=KnowledgeDirectory.rgt + source_right + diff_value,
                level=KnowledgeDirectory.level + diff_level,
            )
        )

        # 更新源节点的 parent_id
        await db.execute(
            update(KnowledgeDirectory)
            .where(KnowledgeDirectory.id == source.id)
            .values(parent_id=new_parent_id)
        )

        await db.commit()

    @staticmethod
    async def verify_noop_move(
        db: AsyncSession,
        position: str,
        source: KnowledgeDirectory,
        target: KnowledgeDirectory,
    ) -> None:
        """检查移动是否为无操作（已在目标位置），若是则抛出异常"""
        if position in ("left", "right"):
            if position == "left":
                left_sibling = await KnowledgeDirectoryModel._get_left_sibling(db, target)
                if left_sibling and left_sibling.id == source.id:
                    raise ValueError("目录已在目标位置")
            else:  # right
                left_sibling = await KnowledgeDirectoryModel._get_left_sibling(db, source)
                if left_sibling and left_sibling.id == target.id:
                    raise ValueError("目录已在目标位置")
        else:  # first-child / last-child
            children_count = await KnowledgeDirectoryModel._get_children_count(db, target.id)
            if children_count > 0:
                if position == "first-child":
                    first_child = await KnowledgeDirectoryModel._get_first_child(db, target.id)
                    if first_child and first_child.id == source.id:
                        raise ValueError("目录已在目标位置")
                else:  # last-child
                    last_child = await KnowledgeDirectoryModel._get_last_child(db, target.id)
                    if last_child and last_child.id == source.id:
                        raise ValueError("目录已在目标位置")
