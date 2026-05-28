# 目录树接口设计

## 背景

参考 kms-backend 的 V1 目录树 API（`POST /api/v1/knowledge_base/catalogue_management`），在 bms-backend 中实现获取知识目录树的接口。

bms-backend 已有 `KnowledgeDirectory` 实体（含 MPTT 字段：lft/rgt/tree_id/level/parent_id）和基础的 `KnowledgeDirectoryModel`（get_by_id、get_children、get_tree、create），本次引入 `sqlalchemy_mptt` 第三方库来增强 MPTT 操作能力。

### kms-backend 参考端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/v1/knowledge_base/catalogue_management` | POST | 按 dir_id + level 查询目录树 |

请求参数：`current_knowledge_dir_id` + `level`（-1=完整树，1=直接子节点）

## 方案

**手动 MPTT 树构建**：不依赖 sqlalchemy_mptt 的 ORM 方法（它是同步的，与 async 环境冲突），而是利用已有的 lft/rgt 字段做范围查询，在 Python 层手动构建递归树结构。

- level=-1：调用 `Model.get_tree(root_id)` 获取整个子树（lft/rgt 范围查询），然后在 Service 层将扁平列表组装成递归树
- level=1：调用 `Model.get_children(parent_id)` 获取直接子节点，直接返回

## 接口定义

```
POST /api/v1/directory/tree
Authorization: Bearer <token>
Content-Type: application/json

Request:
{
  "dir_id": 1,
  "level": -1
}

Response 200:
{
  "id": 1,
  "dir_name": "根目录",
  "dir_type": 0,
  "level": 0,
  "parent_id": null,
  "children": [
    {
      "id": 2,
      "dir_name": "子目录",
      "dir_type": 0,
      "level": 1,
      "parent_id": 1,
      "children": [...]
    }
  ]
}
```

- 需要登录状态（`get_current_user` 依赖注入）
- `level` 取值：-1（完整子树）或 1（直接子节点）

## 数据流

```
POST /api/v1/directory/tree
Authorization: Bearer <token>
Body: { "dir_id": 1, "level": -1 }
        │
        ▼
  get_current_user()  ← JWT 认证
        │
        ▼
  KnowledgeDirectoryService.get_tree(db, dir_id, level)
        │
        ▼
  level == -1:
    Model.get_tree(root_id) → 查所有子孙节点（lft/rgt 范围）
    → Service._build_tree() → 将扁平列表组装成嵌套树
  level == 1:
    Model.get_children(parent_id) → 查直接子节点（parent_id）
        │
        ▼
  DirectoryTreeOut (Pydantic 递归序列化)
```

### 树组装算法

```
输入: 按 lft 排序的扁平节点列表
1. 将列表转为 {id: node_dict} 映射
2. 第一个节点即为根（最小 lft）
3. 遍历其余节点：根据 parent_id 挂到父节点的 children 列表
4. 返回根节点
```

## 文件变更

| 文件 | 操作 | 说明 |
|------|------|------|
| `app/models/knowledge_directory.py` | 修改 | 新增 `get_root_nodes` |
| `app/services/knowledge_directory.py` | **新建** | 树构建服务 |
| `app/schemas/directory.py` | **新建** | Pydantic 请求/响应模型 |
| `app/api/directory.py` | **新建** | 目录树路由 |
| `app/api/router.py` | 修改 | 注册新路由 |
| `app/api/deps.py` | 修改 | 注入 `KnowledgeDirectoryService` |

## Schema 设计

### 请求

```python
class DirectoryTreeRequest(BaseModel):
    dir_id: int = Field(..., description="根目录id")
    level: int = Field(..., ge=-1, le=1, description="-1=完整树, 1=直接子节点")
```

### 响应

使用 Pydantic v2 递归模型 + `from_attributes=True` 支持 ORM 对象直接转换：

```python
class DirectoryTreeOut(BaseModel):
    id: int
    dir_name: str
    dir_type: int
    level: int
    parent_id: int | None
    children: list["DirectoryTreeOut"] = []

    model_config = ConfigDict(from_attributes=True)
```

## 错误处理

| 场景 | HTTP 状态 | 响应 |
|------|-----------|------|
| 未认证 | 401 | `{"detail": "未提供认证凭据"}` |
| dir_id 不存在 | 404 | `{"detail": "目录不存在"}` |
| level 无效 | 422 | Pydantic 自动校验 |
| 正常请求 | 200 | 目录树 JSON |

## Model 层补充

`KnowledgeDirectoryModel` 已有 `get_by_id`、`get_children`、`get_tree`、`create`，本次新增：

```python
@staticmethod
async def get_root_nodes(db: AsyncSession, *, appid: int | None = None):
    """获取所有根节点（parent_id IS NULL）"""
```

其余方法已满足需求，无需修改。

## 注意事项

- 本次仅实现查询接口，利用已有的 lft/rgt 字段做范围查询，不引入 `sqlalchemy_mptt`
- 后续需要 MPTT 写操作（新增/移动/删除节点）时再引入 `sqlalchemy_mptt` 来管理 lft/rgt 的重平衡
- 实际的树组装逻辑从 MPTT 扁平查询结果在 Python 层完成
- `children` 默认空列表，叶子节点返回 `[]` 而非 `null`
- `model_config = ConfigDict(from_attributes=True)` 支持 ORM 对象 `.model_validate(obj)`
