from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_directory import KnowledgeDirectoryModel
from app.schemas.directory import DirectoryCreateRequest, DirectoryTreeOut


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
