# 添加目录节点接口设计

## 背景

bms-backend 已有目录树只读查询（`POST /v1/directory/tree` 和 `GET /v1/directory/trees`），MPTT 字段（lft/rgt/tree_id/level/parent_id）已存在。需要补齐创建目录节点的写操作，核心是实现 MPTT 重平衡逻辑。

## 插入策略

新节点作为父节点的**最后一个子节点**插入（末尾追加）。

## MPTT 插入算法

假设把新节点 N 插入到父节点 P 的末尾：

```
插入前：                    插入后：
P                           P
├── A (lft=3, rgt=4)        ├── A (lft=3, rgt=4)
└── B (lft=5, rgt=6)        ├── B (lft=5, rgt=6)
                             └── N (lft=7, rgt=8)
```

1. 查询父节点 P，确定新节点的 lft = P.rgt（原值），rgt = P.rgt + 1
2. 把 tree 中所有 `rgt >= P.rgt` 的节点 rgt += 2，所有 `lft > P.rgt` 的节点 lft += 2（P 自身的 rgt 也 +2）
3. 写入新节点：lft/rgt 使用步骤 1 的值，level = P.level + 1，tree_id = P.tree_id
4. 步骤 2 和 3 在同一个事务中完成

## 接口定义

```
POST /api/v1/directory/node
Authorization: Bearer <token>
Content-Type: application/json

Request:
{
  "parent_id": 1,
  "dir_name": "新目录",
  "dir_type": 0,
  "km_id": null        // 可选
}

Response 200:
{
  "id": 3,
  "dir_name": "新目录",
  "dir_type": 0,
  "level": 1,
  "parent_id": 1,
  "children": []
}
```

## 各层变更

| 层 | 文件 | 操作 | 说明 |
|------|------|------|------|
| Schema | `app/schemas/directory.py` | 修改 | 新增 `DirectoryCreateRequest` |
| Model | `app/models/knowledge_directory.py` | 修改 | 新增 `shift_mptt_values`、`create_node` |
| Service | `app/services/knowledge_directory.py` | 修改 | 新增 `add_node()` |
| API | `app/api/directory.py` | 修改 | 新增 `POST /v1/directory/node` |

## Schema 设计

```python
class DirectoryCreateRequest(BaseModel):
    parent_id: int
    dir_name: str = Field(..., min_length=1, max_length=256)
    dir_type: int = Field(..., ge=0, le=1, description="0=目录, 1=分组")
    km_id: int | None = None
```

## Model 层新增

```python
@staticmethod
async def shift_mptt_values(db: AsyncSession, tree_id: int, after_lft: int) -> None:
    """将 tree 中 lft > after_lft 的节点 lft += 2，rgt >= after_lft 的节点 rgt += 2"""
    # UPDATE ... SET rgt = rgt + 2 WHERE tree_id = :tree_id AND rgt >= :after_lft
    # UPDATE ... SET lft = lft + 2 WHERE tree_id = :tree_id AND lft > :after_lft

@staticmethod
async def create_node(db: AsyncSession, parent: KnowledgeDirectory, **kwargs) -> KnowledgeDirectory:
    """在父节点末尾插入新节点，自动处理 MPTT 重平衡"""
```

## 错误处理

| 场景 | HTTP 状态 | 响应 |
|------|-----------|------|
| 未认证 | 401 | `{"detail": "未提供认证凭据"}` |
| parent_id 不存在 | 404 | `{"detail": "父目录不存在"}` |
| 正常请求 | 200 | 新节点 JSON |

## 数据流

```
POST /api/v1/directory/node
Authorization: Bearer <token>
Body: { "parent_id": 1, "dir_name": "...", "dir_type": 0 }
        │
        ▼
  get_current_user()  ← JWT 认证
        │
        ▼
  KnowledgeDirectoryService.add_node(parent_id, dir_name, dir_type)
        │
        ▼
  Model.get_by_id(parent_id) → 验证父节点存在
  Model.shift_mptt_values(tree_id, parent.rgt) → 腾位置
  Model.create_node(parent, dir_name, dir_type, level, tree_id) → 写入
        │
        ▼
  DirectoryTreeOut (Pydantic 序列化返回)
```
