# CLAUDE.md

## 项目概述

这是一个最小可运行的 FastAPI 学习项目，帮助你从零开始掌握 FastAPI 的核心概念。当前只有一个模块 `app/main.py`，约 105 行代码，但已经涵盖了：数据库连接、ORM 模型、Pydantic 序列化、依赖注入、生命周期管理等核心模式。

技术栈：FastAPI + SQLAlchemy 2.0 (async) + aiomysql + Pydantic v2

## 常用命令

```bash
# 启动开发服务器（通过 uvicorn CLI，默认端口 8000）
uvicorn app.main:app --reload

# 直接运行 main.py（端口 8001，带热重载）
python app/main.py

# 安装依赖
pip install -r requirements.txt
```

启动后访问：
- API 文档（Swagger UI）：http://127.0.0.1:8000/docs
- 根路径：http://127.0.0.1:8000/

## 代码风格约定

### 导入顺序
1. **标准库** — `os`、`typing`、`contextlib` 等
2. **空一行**
3. **第三方库异常类**（如 `sqlalchemy.exc`）
4. **空一行**
5. **第三方库** — uvicorn、fastapi、pydantic、sqlalchemy（按库分组）
6. 不使用相对导入，所有导入路径从顶层模块名开始
7. 只导入实际用到的类/函数，不使用 `import *`

### 命名规范
| 类别 | 风格 | 示例 |
|------|------|------|
| 模块级变量 | `UPPER_SNAKE_CASE` | `DATABASE_URL`, `DB_CHECK_ON_STARTUP` |
| 类名 | `PascalCase` | `BookService`, `BookOut` |
| 函数/方法 | `snake_case` | `get_db`, `list_books` |
| 路由路径 | 小写、短横线分隔、集合用复数 | `/db/ping`, `/books` |
| 未使用的参数 | 下划线前缀 | `lifespan(_: FastAPI)` |

### 类型标注
- 所有函数必须标注参数类型和返回类型
- 使用 Python 3.10+ 原生泛型语法：`list[Book]`、`dict[str, str]`，不用 `typing.List/Dict`
- SQLAlchemy 模型字段使用 `Mapped[int]` + `mapped_column()`（2.0 风格）
- 依赖注入推荐使用 `Annotated[Type, Depends(...)]` 风格（项目中两种风格并存，新代码优先用 `Annotated`）

### 注释风格
- 中文注释，简洁实用
- 只注释关键配置项和启动逻辑，路由函数不加注释（函数名自解释）

### 代码组织
- 所有代码放在 `app/` 包内，`app/__init__.py` 为空文件
- 单模块结构：配置 → 数据库引擎 → ORM 模型 → Pydantic 模型 → 生命周期 → App 初始化 → 依赖注入 → 路由
- 两个顶层定义之间空两行，类内部方法之间不空行（当前风格）

## 架构模式

### 数据库层
- **引擎**：`create_async_engine()` 创建异步引擎，`pool_pre_ping=True` 保活连接池
- **会话工厂**：`async_sessionmaker(engine, expire_on_commit=False)`
- **基类**：`DeclarativeBase`（SQLAlchemy 2.0 风格）
- 开发环境启用 `echo=True` 打印 SQL

### ORM 模型
- 每个模型显式写 `__tablename__`
- 主键用 `Mapped[int] = mapped_column(primary_key=True, autoincrement=True)`
- 字符串字段用 `mapped_column(String(255), nullable=False)`

### Pydantic 模型
- 序列化模型继承 `BaseModel`，命名为 `{Entity}Out`
- 使用 `model_config = ConfigDict(from_attributes=True)` 启用 ORM 模式（Pydantic v2 风格）
- 字段与 ORM 模型一一对应

### 依赖注入
- 数据库会话：通过 async generator `get_db()` 提供，`yield` 返回 session，`finally` 中自动关闭
- 服务层：`get_book_service()` 包装了注入 db → 构造 `BookService` 的转换
- 路由中通过 FastAPI 的 `Depends()` 声明依赖

### 服务层
- 纯 Python 类，构造函数接收 `AsyncSession`
- 每个业务方法都是 `async`，方法参数自带默认值
- 查询使用 SQLAlchemy 2.0 的 `select()` 风格（不再使用 `Query` 对象）

### 生命周期
- 使用 `@asynccontextmanager` 装饰器实现 `lifespan`
- 启动阶段：连通性校验（`SELECT 1`）+ 自动建表
- 关闭阶段：`await engine.dispose()` 释放连接
- 通过环境变量 `DB_CHECK_ON_STARTUP` 控制是否执行启动检查

### 路由
- 直接使用 `@app.get()` 装饰器，不使用 `APIRouter`（学习阶段保持简单）
- 响应模型用 `response_model=list[BookOut]` 显式声明
- ORM → Pydantic 转换使用 `BookOut.model_validate(book)`（Pydantic v2 风格）

### 配置
- 通过 `os.getenv("KEY", "default")` 读取环境变量
- 布尔型配置用字符串比较：`os.getenv("FLAG", "1") == "1"`
- 尚未使用 `.env` 文件或 pydantic-settings

## 项目状态

- [ ] 无测试
- [ ] 无数据库迁移（使用 `create_all` 自动建表）
- [ ] 无 CORS/中间件/异常处理
- [ ] 无 APIRouter 拆分
- [x] 基本的 CRUD 读取
- [x] 数据库连接 + ORM
- [x] 依赖注入
