# 目录树查询接口 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 POST /api/v1/directory/tree 目录树查询接口，支持完整子树查询和直接子节点查询。

**Architecture:** 利用已有的 MPTT 字段（lft/rgt）做范围查询获取扁平节点列表，然后在 Python 层手动将扁平列表组装成递归树结构。遵循 Entity → Model → Service → API 四层架构。

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + Pydantic v2

---

### Task 1: Model 层新增 get_root_nodes

**Files:**
- Modify: `app/models/knowledge_directory.py`

- [ ] **Step 1: 添加 get_root_nodes 方法**

在 `KnowledgeDirectoryModel` 类末尾追加：

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add app/models/knowledge_directory.py
git commit -m "feat: add get_root_nodes to KnowledgeDirectoryModel"
```

---

### Task 2: 新建 Schema 文件

**Files:**
- Create: `app/schemas/directory.py`

- [ ] **Step 1: 创建目录 schema**

```python
from pydantic import BaseModel, ConfigDict, Field


class DirectoryTreeRequest(BaseModel):
    dir_id: int = Field(..., description="根目录id")
    level: int = Field(..., ge=-1, le=1, description="-1=完整树, 1=直接子节点")


class DirectoryTreeOut(BaseModel):
    id: int
    dir_name: str
    dir_type: int
    level: int
    parent_id: int | None
    children: list["DirectoryTreeOut"] = []

    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 2: 验证 Pydantic 模型**

```bash
python -c "
from app.schemas.directory import DirectoryTreeRequest, DirectoryTreeOut

# 验证请求校验
req = DirectoryTreeRequest(dir_id=1, level=-1)
print('Request OK:', req)

# 验证 level 范围
try:
    DirectoryTreeRequest(dir_id=1, level=2)
    print('ERROR: should have raised')
except Exception as e:
    print('Level validation OK:', type(e).__name__)

# 验证递归模型
out = DirectoryTreeOut(id=1, dir_name='test', dir_type=0, level=0, parent_id=None)
print('Response OK:', out)
"
```

Expected: 三次 OK 输出。

- [ ] **Step 3: Commit**

```bash
git add app/schemas/directory.py
git commit -m "feat: add DirectoryTreeRequest and DirectoryTreeOut schemas"
```

---

### Task 3: 新建 Service 层

**Files:**
- Create: `app/services/knowledge_directory.py`

- [ ] **Step 1: 创建 KnowledgeDirectoryService**

```python
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_directory import KnowledgeDirectoryModel
from app.schemas.directory import DirectoryTreeOut


class KnowledgeDirectoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_tree(self, dir_id: int, level: int) -> DirectoryTreeOut:
        """获取目录树"""
        root = await KnowledgeDirectoryModel.get_by_id(self.db, dir_id)
        if root is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="目录不存在",
            )

        if level == -1:
            # 完整子树：通过 lft/rgt 范围查询所有子孙，再组装成树
            nodes = await KnowledgeDirectoryModel.get_tree(self.db, dir_id)
            if not nodes:
                return DirectoryTreeOut.model_validate(root)
            return self._build_tree(nodes)
        else:
            # 直接子节点
            children = await KnowledgeDirectoryModel.get_children(self.db, dir_id)
            result = DirectoryTreeOut.model_validate(root)
            result.children = [
                DirectoryTreeOut.model_validate(c) for c in children
            ]
            return result

    @staticmethod
    def _build_tree(nodes: list) -> DirectoryTreeOut:
        """将按 lft 排序的扁平节点列表组装成递归树"""
        # 构建 {id: DirectoryTreeOut} 映射
        node_map: dict[int, DirectoryTreeOut] = {}
        for node in nodes:
            node_map[node.id] = DirectoryTreeOut.model_validate(node)

        # 第一个节点即为根（最小 lft）
        root = node_map[nodes[0].id]

        # 将其余节点挂到父节点的 children 列表
        for node in nodes[1:]:
            parent = node_map.get(node.parent_id)
            if parent is not None:
                parent.children.append(node_map[node.id])

        return root
```

- [ ] **Step 2: 验证导入**

```bash
python -c "from app.services.knowledge_directory import KnowledgeDirectoryService; print('Import OK')"
```

- [ ] **Step 3: Commit**

```bash
git add app/services/knowledge_directory.py
git commit -m "feat: add KnowledgeDirectoryService with tree building"
```

---

### Task 4: deps.py 新增依赖注入

**Files:**
- Modify: `app/api/deps.py`

- [ ] **Step 1: 添加 get_directory_service 依赖**

在 `app/api/deps.py` 末尾追加：

```python
from app.services.knowledge_directory import KnowledgeDirectoryService


def get_directory_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KnowledgeDirectoryService:
    return KnowledgeDirectoryService(db)
```

文件顶部已有 `AsyncSession` 和 `Depends` 的导入，无需新增。

- [ ] **Step 2: Commit**

```bash
git add app/api/deps.py
git commit -m "feat: add get_directory_service dependency"
```

---

### Task 5: 新建 API 端点

**Files:**
- Create: `app/api/directory.py`

- [ ] **Step 1: 创建 directory 路由**

```python
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_directory_service
from app.entities.user import User
from app.schemas.directory import DirectoryTreeOut, DirectoryTreeRequest
from app.services.knowledge_directory import KnowledgeDirectoryService

router = APIRouter(prefix="/api/v1/directory")


@router.post("/tree", response_model=DirectoryTreeOut)
async def get_directory_tree(
    body: DirectoryTreeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[KnowledgeDirectoryService, Depends(get_directory_service)],
) -> DirectoryTreeOut:
    return await service.get_tree(body.dir_id, body.level)
```

- [ ] **Step 2: Commit**

```bash
git add app/api/directory.py
git commit -m "feat: add POST /api/v1/directory/tree endpoint"
```

---

### Task 6: 注册路由

**Files:**
- Modify: `app/api/router.py`

- [ ] **Step 1: 添加 directory 路由**

当前 `app/api/router.py`：

```python
from fastapi import APIRouter

from app.api import auth, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, tags=["auth"])
```

修改为：

```python
from fastapi import APIRouter

from app.api import auth, directory, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(directory.router, tags=["directory"])
```

- [ ] **Step 2: Commit**

```bash
git add app/api/router.py
git commit -m "feat: register directory tree route"
```

---

### Task 7: 手动验证完整流程

- [ ] **Step 1: 启动服务（如果已启动则跳过）**

```bash
curl -s http://127.0.0.1:8000/
```

Expected: `{"message":"Hello, KMS"}`

- [ ] **Step 2: 登录获取 token**

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test001","password":"123456"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo "Token: ${TOKEN:0:20}..."
```

- [ ] **Step 3: 查询完整目录树（level=-1）**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/directory/tree \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dir_id": 1, "level": -1}'
```

Expected: 返回目录树 JSON，包含 `dir_name`、`children` 等递归字段。

- [ ] **Step 4: 查询直接子节点（level=1）**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/directory/tree \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dir_id": 1, "level": 1}'
```

Expected: 返回该目录及其直接子节点。

- [ ] **Step 5: 验证不存在的目录**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/directory/tree \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dir_id": 99999, "level": -1}'
```

Expected: `{"detail":"目录不存在"}`

- [ ] **Step 6: 验证未认证请求**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/directory/tree \
  -H "Content-Type: application/json" \
  -d '{"dir_id": 1, "level": -1}'
```

Expected: `{"detail":"未提供认证凭据"}`

- [ ] **Step 7: Commit（如有调整）**

```bash
git status
```
