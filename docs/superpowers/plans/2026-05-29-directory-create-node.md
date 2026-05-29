# 添加目录节点 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 `POST /api/v1/directory/node` 接口，在父目录末尾插入新子节点，包含 MPTT 重平衡。

**Architecture:** 自底向上四层变更 — Schema（请求模型）→ Model（MPTT 移位 + 写入）→ Service（编排 + 校验）→ API（路由端点）。MPTT 移位和节点写入合并在 Model 层一个方法中保证事务原子性。`appid` 从父节点继承。

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + Pydantic v2

**Files to modify (4 files):**
- `app/schemas/directory.py` — 新增 `DirectoryCreateRequest`
- `app/models/knowledge_directory.py` — 新增 `create_node`（含 MPTT 移位）
- `app/services/knowledge_directory.py` — 新增 `add_node()`
- `app/api/directory.py` — 新增 `POST /v1/directory/node`

---

### Task 1: Schema — 新增 DirectoryCreateRequest

**File:** Modify `app/schemas/directory.py`

- [ ] **Step 1: 添加 Field 导入并新增 DirectoryCreateRequest**

找到文件末尾，在 `DirectoryTreeOut` 类之后追加：

```python
from pydantic import BaseModel, ConfigDict, Field


class DirectoryTreeRequest(BaseModel):
    dir_id: int = Field(..., description="根目录id")
    level: int = Field(..., ge=-1, le=1, description="-1=完整树, 1=直接子节点")


class DirectoryCreateRequest(BaseModel):
    parent_id: int = Field(..., description="父目录id")
    dir_name: str = Field(..., min_length=1, max_length=256, description="目录名称")
    dir_type: int = Field(..., ge=0, le=1, description="0=目录, 1=分组")
    km_id: int | None = Field(None, description="关联知识id")


class DirectoryTreeOut(BaseModel):
    id: int
    dir_name: str
    dir_type: int
    level: int
    parent_id: int | None
    children: list["DirectoryTreeOut"] = []

    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 2: 验证 schema 语法正确**

```bash
python -c "from app.schemas.directory import DirectoryCreateRequest; print(DirectoryCreateRequest(parent_id=1, dir_name='test', dir_type=0))"
```

期望：输出 `parent_id=1 dir_name='test' dir_type=0 km_id=None`

- [ ] **Step 3: 验证校验规则生效**

```bash
python -c "from app.schemas.directory import DirectoryCreateRequest; print(DirectoryCreateRequest(parent_id=1, dir_name='', dir_type=0))"
```

期望：Pydantic ValidationError（`dir_name` 空字符串不符合 min_length=1）

- [ ] **Step 4: Commit**

```bash
git add app/schemas/directory.py
git commit -m "feat: add DirectoryCreateRequest schema for directory node creation"
```

---

### Task 2: Model — 新增 create_node（含 MPTT 移位）

**File:** Modify `app/models/knowledge_directory.py`

- [ ] **Step 1: 添加 update 导入**

将第 1 行：
```python
from sqlalchemy import func, select
```
改为：
```python
from sqlalchemy import func, select, update
```

- [ ] **Step 2: 在类末尾（`create` 方法之后）新增 `create_node` 静态方法**

```python
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
```

- [ ] **Step 3: 验证 Model 语法正确**

```bash
python -c "from app.models.knowledge_directory import KnowledgeDirectoryModel; print('OK')"
```

期望：输出 `OK`

- [ ] **Step 4: Commit**

```bash
git add app/models/knowledge_directory.py
git commit -m "feat: add create_node with MPTT rebalancing to KnowledgeDirectoryModel"
```

---

### Task 3: Service — 新增 add_node()

**File:** Modify `app/services/knowledge_directory.py`

- [ ] **Step 1: 导入 DirectoryCreateRequest**

将第 5 行：
```python
from app.schemas.directory import DirectoryTreeOut
```
改为：
```python
from app.schemas.directory import DirectoryCreateRequest, DirectoryTreeOut
```

- [ ] **Step 2: 在类末尾新增 `add_node` 方法**

在 `_build_tree` 方法之后追加：

```python
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
```

- [ ] **Step 3: 验证 Service 语法正确**

```bash
python -c "from app.services.knowledge_directory import KnowledgeDirectoryService; print('OK')"
```

期望：输出 `OK`

- [ ] **Step 4: Commit**

```bash
git add app/services/knowledge_directory.py
git commit -m "feat: add add_node method to KnowledgeDirectoryService"
```

---

### Task 4: API — 新增 POST /v1/directory/node

**File:** Modify `app/api/directory.py`

- [ ] **Step 1: 导入 DirectoryCreateRequest 并新增端点**

将第 7 行导入改为：
```python
from app.schemas.directory import DirectoryCreateRequest, DirectoryTreeOut, DirectoryTreeRequest
```

在文件末尾（`get_all_trees` 函数之后）追加：

```python
@router.post("/node", response_model=DirectoryTreeOut, status_code=200)
async def create_directory_node(
    body: DirectoryCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[KnowledgeDirectoryService, Depends(get_directory_service)],
) -> DirectoryTreeOut:
    return await service.add_node(body)
```

- [ ] **Step 2: 验证路由语法正确**

```bash
python -c "from app.api.directory import router; print([r.path for r in router.routes])"
```

期望：输出包含 `'/v1/directory/node'` 的路由列表

- [ ] **Step 3: Commit**

```bash
git add app/api/directory.py
git commit -m "feat: add POST /v1/directory/node endpoint for directory node creation"
```

---

### Task 5: 端到端验证

- [ ] **Step 1: 确认服务已启动**

如果服务未运行：
```bash
source .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- [ ] **Step 2: 获取 JWT token**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

提取返回的 `access_token`，后续命令中用 `<TOKEN>` 替代。

- [ ] **Step 3: 确认父目录存在**

```bash
curl -s http://127.0.0.1:8000/api/v1/directory/trees \
  -H "Authorization: Bearer <TOKEN>" | python -m json.tool
```

确认有至少一个根目录，记录其 `id`（如 `1`）。

- [ ] **Step 4: 创建子目录节点**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/directory/node \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"parent_id": 1, "dir_name": "测试子目录", "dir_type": 0}' | python -m json.tool
```

期望：返回 200，包含新节点的 `id`、`dir_name`、`level`、`parent_id` 等字段。

- [ ] **Step 5: 查询父目录树验证节点已挂载**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/directory/tree \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"dir_id": 1, "level": -1}' | python -m json.tool
```

期望：`children` 数组末尾包含刚创建的节点。

- [ ] **Step 6: 验证 404 错误处理**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/directory/node \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"parent_id": 99999, "dir_name": "不存在的父节点", "dir_type": 0}'
```

期望：返回 404，`{"detail": "父目录不存在"}`

- [ ] **Step 7: 验证 401 未认证**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/directory/node \
  -H "Content-Type: application/json" \
  -d '{"parent_id": 1, "dir_name": "未认证测试", "dir_type": 0}'
```

期望：返回 401，`{"detail": "未提供认证凭据"}`
