from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_directory import KnowledgeDirectoryModel
from app.schemas.directory import (
    DirectoryCreateRequest,
    DirectoryDeleteRequest,
    DirectoryDeleteResponse,
    DirectoryMoveRequest,
    DirectorySearchItem,
    DirectorySearchResponse,
    DirectoryTreeOut,
    DirectoryUpdateRequest,
)


class KnowledgeDirectoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_tree(self, dir_id: int, level: int) -> DirectoryTreeOut:
        root = await KnowledgeDirectoryModel.get_by_id(self.db, dir_id)
        if root is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="目录不存在",
            )

        if level == -1:
            nodes = await KnowledgeDirectoryModel.get_tree(self.db, dir_id)
            if not nodes:
                return DirectoryTreeOut.model_validate(root)
            return self._build_tree(nodes)
        else:
            children = await KnowledgeDirectoryModel.get_children(self.db, dir_id)
            result = DirectoryTreeOut.model_validate(root)
            result.children = [
                DirectoryTreeOut.model_validate(c) for c in children
            ]
            return result

    async def get_all_trees(self) -> list[DirectoryTreeOut]:
        roots = await KnowledgeDirectoryModel.get_root_nodes(self.db)
        result: list[DirectoryTreeOut] = []
        for root in roots:
            nodes = await KnowledgeDirectoryModel.get_tree(self.db, root.id)
            if nodes:
                result.append(self._build_tree(nodes))
            else:
                result.append(DirectoryTreeOut.model_validate(root))
        return result

    @staticmethod
    def _build_tree(nodes: list) -> DirectoryTreeOut:
        """将按 lft 排序的扁平节点列表组装成递归树"""
        node_map: dict[int, DirectoryTreeOut] = {}
        for node in nodes:
            node_map[node.id] = DirectoryTreeOut.model_validate(node)

        root = node_map[nodes[0].id]

        for node in nodes[1:]:
            parent = node_map.get(node.parent_id)
            if parent is not None:
                parent.children.append(node_map[node.id])

        return root

    async def add_node(self, req: DirectoryCreateRequest) -> DirectoryTreeOut:
        parent = await KnowledgeDirectoryModel.get_by_id(self.db, req.parent_id)
        if parent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="父目录不存在",
            )

        node = await KnowledgeDirectoryModel.create_node(
            self.db,
            parent=parent,
            dir_name=req.dir_name,
            dir_type=req.dir_type,
            km_id=req.km_id,
        )
        return DirectoryTreeOut.model_validate(node)

    async def delete_node(self, req: DirectoryDeleteRequest) -> DirectoryDeleteResponse:
        node = await KnowledgeDirectoryModel.get_by_id(self.db, req.dir_id)
        if node is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="目录不存在",
            )

        subtree = await KnowledgeDirectoryModel.get_subtree_nodes(self.db, node)
        ids = [n.id for n in subtree]
        await KnowledgeDirectoryModel.soft_delete_nodes(self.db, ids, req.delete_type)

        return DirectoryDeleteResponse(
            deleted_count=len(ids),
            deleted_ids=ids,
            dir_name=node.dir_name,
        )

    async def update_node(self, req: DirectoryUpdateRequest) -> DirectoryTreeOut:
        node = await KnowledgeDirectoryModel.update_node(
            self.db, req.dir_id, req.dir_name
        )
        if node is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="目录不存在",
            )
        return DirectoryTreeOut.model_validate(node)

    async def search_nodes(
        self, keyword: str, limit: int = 20, offset: int = 0
    ) -> DirectorySearchResponse:
        total, items = await KnowledgeDirectoryModel.search_by_name(
            self.db, keyword, limit, offset
        )
        return DirectorySearchResponse(
            total=total,
            items=[DirectorySearchItem.model_validate(item) for item in items],
        )

    async def move_node(self, req: DirectoryMoveRequest) -> DirectoryTreeOut:
        source = await KnowledgeDirectoryModel.get_by_id(self.db, req.source_id)
        if source is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="要移动的目录不存在",
            )

        target = await KnowledgeDirectoryModel.get_by_id(self.db, req.target_id)
        if target is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="目标目录不存在",
            )

        if source.id == target.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="源目录和目标目录不能相同",
            )

        if source.parent_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能移动顶级目录",
            )

        if target.dir_type != 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="目标目录类型必须是目录",
            )

        if source.tree_id != target.tree_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="源目录和目标目录必须属于同一棵树",
            )

        position = req.position.value
        if position in ("left", "right") and target.parent_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="目标目录不能是顶级目录",
            )

        # 检查不能移动到自己的子树中
        is_ancestor = (
            target.lft > source.lft
            and target.rgt < source.rgt
            and target.tree_id == source.tree_id
        )
        if is_ancestor and position in ("first-child", "last-child"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无法将目录移动到自己的子节点中",
            )

        # 检查是否已经是目标位置
        try:
            await KnowledgeDirectoryModel.verify_noop_move(
                self.db, position, source, target
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from None

        # 计算方向和目标位置
        direction = KnowledgeDirectoryModel._relative_direction(position, source, target)
        source_width = source.rgt - source.lft
        new_left, new_right, new_level, new_parent_id = (
            await KnowledgeDirectoryModel._calc_new_position(
                self.db, direction, position, source_width, target
            )
        )

        # 校验新父节点不是 source 的子孙（二次保障）
        if new_parent_id is not None:
            new_parent = await KnowledgeDirectoryModel.get_by_id(self.db, new_parent_id)
            if new_parent is not None:
                is_new_parent_descendant = (
                    new_parent.lft > source.lft
                    and new_parent.rgt < source.rgt
                    and new_parent.tree_id == source.tree_id
                )
                if is_new_parent_descendant:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="无法将目录移动到自己的子节点中",
                    )

        # 执行 MPTT 移动
        await KnowledgeDirectoryModel._relative_direction_strategy(
            self.db,
            direction=direction,
            source=source,
            new_left=new_left,
            new_right=new_right,
            new_level=new_level,
            new_parent_id=new_parent_id,
        )

        # 返回更新后的节点
        moved = await KnowledgeDirectoryModel.get_by_id(self.db, source.id)
        return DirectoryTreeOut.model_validate(moved)
