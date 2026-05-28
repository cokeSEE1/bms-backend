# 退出登录接口 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 POST /auth/logout 退出登录接口，使用 Redis 黑名单使已签发 JWT 主动失效。

**Architecture:** 签发 JWT 时写入 jti（UUID v4）唯一标识；退出时将 jti 存入 Redis 黑名单（TTL=token 剩余有效期）；认证时在 get_current_user 中检查 Redis 黑名单，命中则拒绝。Redis 不可用时降级放行。

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + python-jose + redis-py (async) + uuid

---

### Task 1: 添加 Redis 依赖和配置

**Files:**
- Modify: `requirements.txt`
- Modify: `app/config.py`
- Create: `app/core/redis.py`

- [ ] **Step 1: 添加 redis 依赖**

```bash
pip install "redis[hiredis]>=5.0"
```

- [ ] **Step 2: 更新 requirements.txt**

在 `requirements.txt` 末尾追加一行：

```
redis[hiredis]>=5.0
```

- [ ] **Step 3: 在 config.py 添加 REDIS_URL**

在 `app/config.py` 末尾追加：

```python
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
```

- [ ] **Step 4: 创建 app/core/redis.py**

```python
import redis.asyncio as aioredis

from app.config import REDIS_URL

_redis: aioredis.Redis | None = None


async def init_redis() -> None:
    global _redis
    _redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    await _redis.ping()


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None


def get_redis() -> aioredis.Redis | None:
    """返回 Redis 客户端，未初始化时返回 None（降级放行）"""
    return _redis
```

- [ ] **Step 5: 在 lifespan 中集成 Redis 初始化与关闭**

修改 `app/main.py`：

```python
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import api_router
from app.config import DATABASE_URL, DB_CHECK_ON_STARTUP
from app.core.database import Base, engine
from app.core.redis import close_redis, init_redis
from app.models import base as _models_base  # noqa: F401 — 确保所有 entity 被导入后再 create_all


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    if DB_CHECK_ON_STARTUP:
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
                await conn.run_sync(Base.metadata.create_all)
        except SQLAlchemyError as exc:
            raise RuntimeError(
                f"Database connection failed. DATABASE_URL={DATABASE_URL}",
            ) from exc
    try:
        await init_redis()
    except Exception:
        pass  # Redis 不可用时降级，不影响启动
    yield
    await engine.dispose()
    await close_redis()
```

- [ ] **Step 6: 启动 Redis 验证**

```bash
redis-cli ping  # 确认本地 Redis 可连接
```

Expected: `PONG`

- [ ] **Step 7: Commit**

```bash
git add requirements.txt app/config.py app/core/redis.py app/main.py
git commit -m "feat: add Redis dependency and connection management"
```

---

### Task 2: JWT 加入 jti 标识

**Files:**
- Modify: `app/core/security.py`

- [ ] **Step 1: 修改 create_access_token**

修改 `app/core/security.py`，加入 `uuid` 导入，在 token payload 中添加 `jti` 和 `iat`：

```python
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import jwt

from app.config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def create_access_token(user_id: int) -> str:
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {
            "sub": str(user_id),
            "jti": uuid.uuid4().hex,
            "iat": now,
            "exp": expire,
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
```

- [ ] **Step 2: 验证 JWT payload 包含新字段**

```bash
python -c "
from app.core.security import create_access_token
from jose import jwt
from app.config import SECRET_KEY, ALGORITHM

token = create_access_token(1)
payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
print('jti:', payload.get('jti'))
print('iat:', payload.get('iat'))
print('exp:', payload.get('exp'))
print('sub:', payload.get('sub'))
"
```

Expected: 四个字段都有值，`jti` 是 32 位 hex 字符串。

- [ ] **Step 3: Commit**

```bash
git add app/core/security.py
git commit -m "feat: add jti and iat claims to JWT payload"
```

---

### Task 3: get_current_user 增加 Redis 黑名单检查

**Files:**
- Modify: `app/api/deps.py`

- [ ] **Step 1: 修改 get_current_user**

修改 `app/api/deps.py`，解码 JWT 后提取 `jti` 并检查 Redis 黑名单：

```python
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import ALGORITHM, SECRET_KEY
from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis
from app.entities.user import User
from app.services.auth import AuthService


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭据",
        )
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证格式无效",
        )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="凭据无效",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="凭据无效或已过期",
        ) from None

    # 检查 Redis 黑名单
    redis_client = get_redis()
    if redis_client is not None:
        jti: str | None = payload.get("jti")
        if jti is not None and await redis_client.exists(f"bl:{jti}"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="凭据已失效",
            )

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )
    return user


def get_auth_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthService:
    return AuthService(db)
```

- [ ] **Step 2: 验证现有认证仍然正常**

启动服务后调用 `POST /auth/login` 和 `GET /auth/me`，确认正常返回。

- [ ] **Step 3: Commit**

```bash
git add app/api/deps.py
git commit -m "feat: add Redis blacklist check to get_current_user"
```

---

### Task 4: AuthService 新增 logout 方法

**Files:**
- Modify: `app/services/auth.py`

- [ ] **Step 1: 新增 logout 方法**

在 `AuthService` 类末尾追加 `logout` 方法：

```python
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.core.security import create_access_token, hash_password, verify_password
from app.entities.user import User
from app.schemas.auth import LogoutOut, TokenOut
from app.schemas.user import UserLogin, UserOut, UserRegister


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ... register, login 方法不变 ...

    async def logout(self, jti: str, exp: int) -> LogoutOut:
        redis_client = get_redis()
        if redis_client is not None:
            remaining = exp - int(datetime.now(UTC).timestamp())
            if remaining > 0:
                await redis_client.set(f"bl:{jti}", "1", ex=remaining)
        return LogoutOut(message="已退出登录")
```

注意：`login` 方法的 `create_access_token(user.id)` 保持不变（TokenOut 不变）。

- [ ] **Step 2: Commit**

```bash
git add app/services/auth.py
git commit -m "feat: add logout method to AuthService"
```

---

### Task 5: 新增 LogoutOut schema

**Files:**
- Modify: `app/schemas/auth.py`

- [ ] **Step 1: 添加 LogoutOut**

在现有 schema 后面追加：

```python
from pydantic import BaseModel

from app.schemas.user import UserOut


class TokenOut(BaseModel):
    access_token: str
    user: UserOut


class LogoutOut(BaseModel):
    message: str
```

- [ ] **Step 2: Commit**

```bash
git add app/schemas/auth.py
git commit -m "feat: add LogoutOut response schema"
```

---

### Task 6: 新增 POST /auth/logout 端点

**Files:**
- Modify: `app/api/auth.py`

- [ ] **Step 1: 添加 logout 路由**

在 `app/api/auth.py` 追加：

```python
from typing import Annotated

from fastapi import APIRouter, Depends, Header, status

from app.api.deps import get_auth_service, get_current_user
from app.entities.user import User
from app.schemas.auth import LogoutOut, TokenOut
from app.schemas.user import UserLogin, UserOut, UserRegister
from app.services.auth import AuthService
from app.config import ALGORITHM, SECRET_KEY
from jose import jwt

router = APIRouter(prefix="/auth")


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    body: UserRegister,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserOut:
    return await service.register(body)


@router.post("/login", response_model=TokenOut)
async def login(
    body: UserLogin,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenOut:
    return await service.login(body)


@router.get("/me", response_model=UserOut)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserOut:
    return UserOut.model_validate(current_user)


@router.post("/logout", response_model=LogoutOut)
async def logout(
    current_user: Annotated[User, Depends(get_current_user)],
    authorization: Annotated[str, Header()],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> LogoutOut:
    _, _, token = authorization.partition(" ")
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return await service.logout(payload["jti"], payload["exp"])
```

- [ ] **Step 2: Commit**

```bash
git add app/api/auth.py
git commit -m "feat: add POST /auth/logout endpoint"
```

---

### Task 7: 手动验证完整流程

- [ ] **Step 1: 启动服务**

```bash
uvicorn app.main:app --reload
```

- [ ] **Step 2: 注册并登录**

```bash
# 注册
curl -s -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test001","password":"123456"}'

# 登录
curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test001","password":"123456"}'
```

记录返回的 `access_token`，设为 `TOKEN`。

- [ ] **Step 3: 验证 /auth/me 正常**

```bash
curl -s http://127.0.0.1:8000/auth/me -H "Authorization: Bearer $TOKEN"
```

Expected: 返回用户信息。

- [ ] **Step 4: 退出登录**

```bash
curl -s -X POST http://127.0.0.1:8000/auth/logout -H "Authorization: Bearer $TOKEN"
```

Expected: `{"message":"已退出登录"}`

- [ ] **Step 5: 验证 token 已失效**

```bash
curl -s http://127.0.0.1:8000/auth/me -H "Authorization: Bearer $TOKEN"
```

Expected: `{"detail":"凭据已失效"}`

- [ ] **Step 6: 验证重复退出幂等**

```bash
curl -s -X POST http://127.0.0.1:8000/auth/logout -H "Authorization: Bearer $TOKEN"
```

Expected: 仍返回 `{"message":"已退出登录"}`（因为 get_current_user 仍能从 header 解析 token 并查用户，但黑名单检查是在 get_current_user 中，此时 jti 已在黑名单... 实际上第二次调用会在 get_current_user 阶段被拒绝，返回 401）。

修正预期：第二次调用返回 `{"detail":"凭据已失效"}`。这符合安全预期，且不影响幂等性（同一 token 退出两次，结果都是 token 失效）。

- [ ] **Step 7: 验证未登录调用**

```bash
curl -s -X POST http://127.0.0.1:8000/auth/logout
```

Expected: `{"detail":"未提供认证凭据"}`

- [ ] **Step 8: Commit（如有调整）**

```bash
git status
```
