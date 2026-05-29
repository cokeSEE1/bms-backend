# CLAUDE.md

## 项目概述

KMS (Knowledge Management System) 后端服务 — FastAPI + SQLAlchemy 2.0 (async) + aiomysql + Pydantic v2 + Redis + Elasticsearch + bcrypt + JWT。

对接前端 [bms-frontend](../bms-frontend/) (React 18 + TypeScript + Vite + Ant Design 5 + MobX)，设计参照后端 [kms-backend](../kms-backend/) (Flask + MPTT + 插件系统)。

**每次新会话开始时，必须先阅读以下相关上下文：**
- 本项目 CLAUDE.md（本文件）
- 前端项目：`../bms-frontend/CLAUDE.md`
- 参照后端：`../kms-backend/CLAUDE.md`
- Memory 目录：`.claude/projects/-Users-lanzhang-Desktop-bms-backend/memory/MEMORY.md`

## 常用命令

```bash
# 启动开发服务器（通过 uvicorn CLI，默认端口 8000）
uvicorn app.main:app --reload

# 直接运行 main.py（端口 8001，带热重载）
python app/main.py

# 安装依赖
pip install -r requirements.txt

# 代码检查
ruff check . --fix
```

启动后访问：
- API 文档（Swagger UI）：http://127.0.0.1:8000/docs
- 根路径：http://127.0.0.1:8000/

## 代码组织

```
app/
  config.py                  # 环境变量配置（DB、Redis、JWT、ES）
  main.py                    # create_app() 工厂 + lifespan
  core/
    database.py              # engine, AsyncSessionLocal, Base
    security.py              # bcrypt + JWT 工具函数
    redis.py                 # Redis 客户端（支持降级）
    elasticsearch.py         # ES 异步客户端（支持降级）
    es_index.py              # ES 索引 mapping + 自动建索引（IK 分词器）
  entities/                  # SQLAlchemy ORM 实体（数据库表映射）
    base.py                  # BaseEntity（软删除 + 时间戳）
    user.py                  # User
    knowledge_base.py        # KnowledgeBase
    knowledge_item.py        # KnowledgeItem
    knowledge_directory.py   # KnowledgeDirectory（MPTT 树形结构）
    knowledge_item_history.py  # KnowledgeItemHistory（版本历史）
  models/                    # 数据访问层（查询 + 写操作）
    base.py                  # 重导出（供 create_all 使用）
    knowledge_directory.py   # KnowledgeDirectoryModel
    knowledge_item.py        # KnowledgeItemModel
    knowledge_base.py        # KnowledgeBaseModel
    knowledge_item_history.py  # KnowledgeItemHistoryModel
  schemas/                   # Pydantic 请求/响应模型
    auth.py                  # TokenOut, LogoutOut
    user.py                  # UserRegister, UserLogin, UserOut
    directory.py             # DirectoryTreeOut, DirectoryCreateRequest, ...
    knowledge_item.py        # KnowledgeItemCreate/Update/Out/ListResponse
  services/                  # 业务逻辑层
    auth.py                  # AuthService（注册、登录、登出）
    knowledge_directory.py   # KnowledgeDirectoryService（目录树 CRUD）
    knowledge_item.py        # KnowledgeItemService（知识条目 CRUD + 列表）
    es_sync.py               # ES 同步服务（CRUD 同步到 ES，异常静默降级）
    es_search.py             # ES 搜索服务（multi_match + term 过滤，降级 MySQL LIKE）
  api/                       # API 路由
    deps.py                  # get_db, get_current_user, get_auth_service, get_directory_service, get_knowledge_item_service
    router.py                # 顶层 APIRouter
    health.py                # /, /db/ping
    auth.py                  # /auth/*
    directory.py             # /v1/directory/*
    knowledge_item.py        # /v1/knowledge/*
```

依赖方向：`api/ → services/ → models/ → entities/ → core/`（下层不依赖上层，services 不跨调其他 service）

### 分层说明

| 层 | 目录 | 职责 |
|----|------|------|
| **Entities** | `app/entities/` | SQLAlchemy ORM 映射，继承 `BaseEntity`（含软删除、时间戳） |
| **Models** | `app/models/` | 数据访问层，封装 select/insert/update/delete 查询逻辑，纯 static 方法 |
| **Schemas** | `app/schemas/` | Pydantic v2 请求/响应模型，`from_attributes=True` |
| **Services** | `app/services/` | 业务逻辑，调用 Model 层，处理异常，返回 Schema 对象 |
| **API** | `app/api/` | FastAPI 路由，只做参数提取和依赖注入，逻辑委托给 Service |

## 数据库表

| 表名 | 实体 | 说明 |
|------|------|------|
| `user` | User | 用户表 |
| `kms_knowledge_base` | KnowledgeBase | 知识库 |
| `kms_knowledge_item` | KnowledgeItem | 知识条目（含版本、状态、统计） |
| `kms_knowledge_directory` | KnowledgeDirectory | 知识目录（MPTT 树形结构） |
| `kms_knowledge_item_history` | KnowledgeItemHistory | 知识版本历史 |

所有表继承 `BaseEntity`，包含 `is_delete`（软删除标记）、`create_time`、`update_time`。查询时需过滤 `is_delete == 0`。

## MPTT 目录树

目录使用 MPTT (Modified Preorder Tree Traversal) 模型，字段：

| 字段 | 说明 |
|------|------|
| `tree_id` | 树 ID，同一棵树的所有节点共享 |
| `lft` | 左值 |
| `rgt` | 右值 |
| `level` | 层级（0 = 根节点） |
| `parent_id` | 父节点 ID |
| `dir_type` | 0 = 目录，1 = 分组 |
| `km_id` | 关联知识 ID（可选） |

### MPTT 插入算法

在父节点末尾插入新子节点：
1. 计算新节点位置：`new_lft = parent.rgt`, `new_rgt = parent.rgt + 1`
2. 腾位置：同一 `tree_id` 内，`rgt >= new_lft` 的节点 `rgt += 2`，`lft > new_lft` 的节点 `lft += 2`
3. 插入新节点

### MPTT 查询

- **子树查询**：`lft >= node.lft AND rgt <= node.rgt AND tree_id = node.tree_id`
- **直接子节点**：`parent_id = node.id`
- 所有 MPTT 查询按 `lft` 排序

## API 接口

### Health
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 根路径 |
| GET | `/db/ping` | 数据库连通性检查 |

### Auth (`/auth`)
| 方法 | 路径 | 请求体 | 响应 | 说明 |
|------|------|--------|------|------|
| POST | `/auth/register` | `UserRegister` | `UserOut` | 注册 (201) |
| POST | `/auth/login` | `UserLogin` | `TokenOut` | 登录，返回 JWT + 用户信息 |
| GET | `/auth/me` | — (Bearer token) | `UserOut` | 获取当前用户 |
| POST | `/auth/logout` | — (Bearer token) | `LogoutOut` | 登出，JWT 加入 Redis 黑名单 |

- JWT 算法 HS256，有效期 24h，含 `sub`(user_id)、`jti`(唯一ID)、`iat`、`exp`
- 登出时将 `jti` 写入 Redis 黑名单 (`bl:{jti}`)，TTL = token 剩余有效期
- Redis 不可达时降级放行（不阻断业务）

### Directory (`/v1/directory`) — 均需 Bearer token
| 方法 | 路径 | 请求体 | 响应 | 说明 |
|------|------|--------|------|------|
| GET | `/v1/directory/trees` | — | `list[DirectoryTreeOut]` | 获取所有根树 |
| POST | `/v1/directory/tree` | `{ dir_id, level }` | `DirectoryTreeOut` | 获取子树 |
| POST | `/v1/directory/node` | `{ parent_id, dir_name, dir_type, km_id? }` | `DirectoryTreeOut` | 创建节点 |
| PUT | `/v1/directory/node` | `{ dir_id, dir_name }` | `DirectoryTreeOut` | 更新节点名称 |
| DELETE | `/v1/directory/node` | `{ dir_id, delete_type }` | `DirectoryDeleteResponse` | 删除节点 |

- `level`: -1 = 完整树（递归所有子节点），1 = 仅直接子节点
- `delete_type`: 1 = 软删除，2 = 彻底删除（目前均软删除整棵子树）

### Directory Search (`/v1/directory/search`) — 需 Bearer token
| 方法 | 路径 | Query 参数 | 响应 | 说明 |
|------|------|-----------|------|------|
| GET | `/v1/directory/search` | `keyword`, `limit`, `offset` | `DirectorySearchResponse` | 按名称模糊搜索目录 |

### Knowledge (`/v1/knowledge`) — 均需 Bearer token
| 方法 | 路径 | 请求体/Query | 响应 | 说明 |
|------|------|-------------|------|------|
| POST | `/v1/knowledge/item` | `KnowledgeItemCreate` | `KnowledgeItemOut` | 创建知识条目 (201) |
| GET | `/v1/knowledge/item/{id}` | — | `KnowledgeItemOut` | 查询知识条目详情 |
| PUT | `/v1/knowledge/item/{id}` | `KnowledgeItemUpdate` | `KnowledgeItemOut` | 更新知识条目 |
| DELETE | `/v1/knowledge/item/{id}` | — | 204 | 软删除知识条目 |
| GET | `/v1/knowledge/list` | `cate_id?`, `search?`, `status?`, `author?`, `sort_by?`, `order_by?`, `start_time?`, `end_time?`, `page`, `page_size` | `KnowledgeItemListResponse` | 知识列表查询 |

- `sort_by`: 0-推荐(默认) 1-收藏 2-上线时间 3-创建时间 4-阅读数 5-拼音 6-自定义排序
- `order_by`: 0-倒序(默认) 1-顺序
- `status`: 1-拟稿 2-审核中 3-已发布 4-已下线
- 创建/更新/删除时自动同步 ES 索引，ES 不可达时静默降级

## 代码风格约定

### 导入顺序
1. **标准库** — `collections.abc`、`datetime`、`uuid` 等
2. **空一行**
3. **第三方库异常类**（如 `sqlalchemy.exc`、`redis.exceptions`）
4. **空一行**
5. **第三方库** — fastapi、pydantic、sqlalchemy、jose、bcrypt、redis（按库分组）
6. **空一行**
7. **项目内部模块** — `from app.config import ...`、`from app.core.xxx import ...`
8. 不使用相对导入，所有导入路径从 `app.` 开始
9. 只导入实际用到的类/函数，不使用 `import *`

### 命名规范
| 类别 | 风格 | 示例 |
|------|------|------|
| 模块级变量 | `UPPER_SNAKE_CASE` | `DATABASE_URL`, `SECRET_KEY` |
| 类名 | `PascalCase` | `AuthService`, `DirectoryTreeOut` |
| 函数/方法 | `snake_case` | `get_db`, `get_current_user` |
| 路由路径 | 小写、短横线分隔 | `/v1/directory`, `/db/ping` |
| 未使用的参数 | 下划线前缀 | `lifespan(_: FastAPI)` |
| Model 方法 | `get_by_*`, `create_*`, `update_*`, `delete_*` | `get_by_id`, `soft_delete_nodes` |

### 类型标注
- 所有函数必须标注参数类型和返回类型
- 使用 Python 3.10+ 原生泛型语法：`list[User]`、`dict[str, str]`，不用 `typing.List/Dict`
- SQLAlchemy 实体字段使用 `Mapped[int]` + `mapped_column()`（2.0 风格）
- 依赖注入使用 `Annotated[Type, Depends(...)]` 风格
- 可空字段使用 `int | None`，不用 `Optional[int]`

### 注释风格
- 中文注释，简洁实用
- 只注释关键配置项和启动逻辑
- 路由函数不加注释（函数名自解释）
- 实体字段使用 `comment=` 参数描述

### 代码检查
- 使用 ruff，配置见 `ruff.toml`
- 规则集：E, F, I, UP, B, ANN, RUF, TRY, FAST, COM
- 行宽 100 字符

## 架构模式

### 数据库层
- **引擎**：`create_async_engine()` 创建异步引擎，`pool_pre_ping=True` 保活连接池
- **会话工厂**：`async_sessionmaker(engine, expire_on_commit=False)`
- **基类**：`DeclarativeBase`（SQLAlchemy 2.0 风格）
- **BaseEntity**：抽象基类，包含 `is_delete`、`create_time`、`update_time`
- 开发环境启用 `echo=True` 打印 SQL

### 实体 (entities/)
- 每个实体显式写 `__tablename__`
- 主键用 `Mapped[int] = mapped_column(primary_key=True, autoincrement=True)`
- 继承 `BaseEntity` 获得软删除和时间戳字段
- 表注释用 `__table_args__ = {"comment": "..."}`

### 模型 (models/) — 数据访问层
- 纯 static 方法类，不持有状态
- 每个方法接收 `db: AsyncSession` 作为第一个参数
- 查询使用 SQLAlchemy 2.0 的 `select()` / `update()` 风格
- 写操作后调用 `await db.commit()`
- 所有查询过滤 `is_delete == 0`

### Pydantic Schema (schemas/)
- 请求模型继承 `BaseModel`，使用 `Field(...)` 添加约束和描述
- 响应模型继承 `BaseModel`，使用 `model_config = ConfigDict(from_attributes=True)` 启用 ORM 模式
- ORM → Pydantic 转换使用 `SchemaOut.model_validate(entity)`

### 依赖注入 (api/deps.py)
- 数据库会话：通过 async generator `get_db()` 提供，`yield` 返回 session，`finally` 中自动关闭
- 认证：`get_current_user()` 解析 Bearer token，验证 JWT + Redis 黑名单，返回 User 实体
- 服务层：`get_auth_service()` / `get_directory_service()` 封装 `db → Service` 的构造

### 服务层 (services/)
- 纯 Python 类，构造函数接收 `AsyncSession`
- 每个业务方法都是 `async`
- 调用 Model 层获取数据，处理异常，返回 Schema 对象
- 服务间不互相调用

### 生命周期 (main.py)
- 使用 `@asynccontextmanager` 装饰器实现 `lifespan`
- 启动阶段：连通性校验（`SELECT 1`）+ 自动建表 + Redis 初始化
- 关闭阶段：`await engine.dispose()` + 关闭 Redis 连接
- 通过环境变量 `DB_CHECK_ON_STARTUP` 控制是否执行启动检查

### Redis 集成 (core/redis.py)
- 全局模块级 `_redis` 变量，`init_redis()` 初始化，`close_redis()` 关闭
- `get_redis()` 返回客户端，未初始化时返回 `None`
- **降级策略**：Redis 不可达时不影响启动，业务代码检查 `None` 后跳过 Redis 操作
- 用途：JWT 黑名单（logout 时写入，auth 时检查）

### Elasticsearch 集成 (core/elasticsearch.py)
- 全局模块级 `_es` 变量，`init_es()` 初始化，`close_es()` 关闭
- `get_es()` 返回 `AsyncElasticsearch` 客户端，未初始化时返回 `None`
- **降级策略**：ES 不可达时不影响启动，业务代码检查 `None` 后跳过 ES 操作
- 用途：知识条目全文搜索 + 索引同步

#### ES 索引管理 (core/es_index.py)
- 索引名：`knowledge_item`
- 分词器：IK（`ik_max_word` 索引 / `ik_smart` 搜索）
- 在 lifespan 启动阶段调用 `ensure_index()` 自动创建索引
- 搜索字段：`name`（权重 3）、`abstract`（权重 2）、`content`（权重 1）

#### ES 同步 (services/es_sync.py)
- `sync_knowledge_item(item)` — 将 KnowledgeItem 全量字段写入 ES，`refresh=True` 立即可见
- `delete_from_es(item_id)` — 删除 ES 中的文档
- 在 KnowledgeItemService 的 create/update/delete 后调用，异常静默降级

#### ES 搜索 (services/es_search.py)
- `search_knowledge_items(keyword, cate_id?, status?, limit, offset)` — ES multi_match 搜索
- 返回 `(total, [id, ...])` 或 `None`（ES 不可达时）
- Service 层收到 `None` 后自动回退 MySQL `LIKE` 查询

### 错误处理
- 服务层抛出 `HTTPException`，路由层透传
- Redis 异常使用 `try/except RedisError: pass` 降级放行
- JWT 异常统一转换为 401

## 配置 (config.py)

```python
DATABASE_URL          # 默认 mysql+aiomysql://root:root123456@127.0.0.1:3306/test_db
DB_CHECK_ON_STARTUP   # 默认 "1"（启用启动检查）
SECRET_KEY            # JWT 签名密钥
ALGORITHM             # HS256
ACCESS_TOKEN_EXPIRE_MINUTES  # 1440（24h）
REDIS_URL             # 默认 redis://127.0.0.1:6379/0
ELASTICSEARCH_URL     # 默认 http://127.0.0.1:9200
```

## 项目状态

- [ ] 无测试
- [ ] 无数据库迁移（使用 `create_all` 自动建表）
- [ ] 无 CORS/中间件/异常处理
- [x] APIRouter 拆分（api/ 目录）
- [x] 数据库连接 + ORM
- [x] 依赖注入
- [x] 用户注册/登录/登出认证
- [x] JWT + Redis 黑名单
- [x] MPTT 目录树 CRUD + 移动 + 搜索
- [x] 分层架构（entities → models → services → api）
- [x] Redis 降级容错
- [x] Elasticsearch 集成（全文搜索 + 索引同步 + 降级）
- [x] 知识条目 CRUD + 列表查询（多条件过滤 + 排序 + ES 搜索）
