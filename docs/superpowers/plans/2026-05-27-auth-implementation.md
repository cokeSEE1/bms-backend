# Auth Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add username+password auth (register/login/me) to the BMS backend

**Architecture:** All auth code lives in `app/main.py` following the existing single-module pattern. Uses bcrypt (passlib) for password hashing and JWT (python-jose) for stateless token auth with a `get_current_user` FastAPI dependency.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, passlib[bcrypt], python-jose[cryptography], Pydantic v2

---

### Task 1: Install auth dependencies

**Files:**
- Modify: `requirements.txt`
- Bash: `pip install`

- [ ] **Step 1: Add passlib and python-jose to requirements.txt**

Append two lines to `requirements.txt`:

```
passlib[bcrypt]>=1.7
python-jose[cryptography]>=3.3
```

- [ ] **Step 2: Install the new packages**

```bash
source .venv/bin/activate && pip install -q -r requirements.txt
```

- [ ] **Step 3: Verify imports work**

```bash
source .venv/bin/activate && python -c "from passlib.context import CryptContext; from jose import jwt; print('ok')"
```

Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore: add passlib and python-jose for auth"
```

---

### Task 2: Add User model and update imports

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Add datetime and sqlalchemy imports**

Add `from datetime import datetime` to the stdlib import bloc, and `DateTime` + `func` to sqlalchemy:

```python
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated
```

And:

```python
from sqlalchemy import DateTime, String, func, select, text
```

- [ ] **Step 2: Add User model after Book class**

After `class Book(Base):` block (before `class BookOut`), insert:

```python
class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(60), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
```

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: add User model"
```

---

### Task 3: Add auth Pydantic schemas

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Add HTTPException import**

Replace:
```python
from fastapi import Depends, FastAPI
```

With:
```python
from fastapi import Depends, FastAPI, Header, HTTPException, status
```

- [ ] **Step 2: Add auth schemas after BookOut**

After the `BookOut` class block, insert:

```python
class UserRegister(BaseModel):
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    user: UserOut
```

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: add auth Pydantic schemas"
```

---

### Task 4: Add security utilities (password + JWT)

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Add security imports at the top**

Replace the `from datetime import datetime` line (already added in Task 2) with:

```python
from datetime import datetime, timedelta, timezone
```

And add auth library imports right after:

```python
from jose import JWTError, jwt
from passlib.context import CryptContext
```

- [ ] **Step 2: Add security config and helpers after imports, before DATABASE_URL**

Insert after the last import line and before `# 按需修改，或通过环境变量 DATABASE_URL 覆盖`:

```python
SECRET_KEY = os.getenv("SECRET_KEY", "bms-dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire}, SECRET_KEY, algorithm=ALGORITHM
    )
```

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: add password hashing and JWT utilities"
```

---

### Task 5: Add get_current_user dependency

**Files:**
- Modify: `app/main.py` (after `get_db()`, before `BookService`)

- [ ] **Step 1: Insert get_current_user after get_db()**

After the `get_db()` function block, insert:

```python
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
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )
    return user
```

- [ ] **Step 2: Commit**

```bash
git add app/main.py
git commit -m "feat: add get_current_user dependency"
```

---

### Task 6: Add /auth/register endpoint

**Files:**
- Modify: `app/main.py` (after existing routes, before `if __name__`)

- [ ] **Step 1: Add register endpoint**

Insert before `if __name__ == "__main__":`:

```python
@app.post("/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    body: UserRegister,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserOut:
    result = await db.execute(select(User).where(User.username == body.username))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名已存在",
        )
    user = User(username=body.username, password=hash_password(body.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)
```

- [ ] **Step 2: Commit**

```bash
git add app/main.py
git commit -m "feat: add /auth/register endpoint"
```

---

### Task 7: Add /auth/login endpoint

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Add login endpoint after register**

Insert after the register endpoint:

```python
@app.post("/auth/login", response_model=TokenOut)
async def login(
    body: UserLogin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenOut:
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    token = create_access_token(user.id)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))
```

- [ ] **Step 2: Commit**

```bash
git add app/main.py
git commit -m "feat: add /auth/login endpoint"
```

---

### Task 8: Add /auth/me endpoint

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Add /auth/me endpoint after login**

Insert after the login endpoint:

```python
@app.get("/auth/me", response_model=UserOut)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserOut:
    return UserOut.model_validate(current_user)
```

- [ ] **Step 2: Commit**

```bash
git add app/main.py
git commit -m "feat: add /auth/me endpoint"
```

---

### Task 9: Manual verification

**Files:**
- Bash only

- [ ] **Step 1: Start the server**

```bash
./local_run.sh
```

- [ ] **Step 2: Test register**

```bash
curl -s -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"123456"}' | python -m json.tool
```

Expected: 201 with `{"id":1, "username":"testuser", "created_at":"..."}`

- [ ] **Step 3: Test login**

```bash
curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"123456"}' | python -m json.tool
```

Expected: 200 with `{"access_token":"...", "user":{...}}`

- [ ] **Step 4: Test /auth/me with token**

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"123456"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s http://127.0.0.1:8000/auth/me -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

Expected: 200 with user info

- [ ] **Step 5: Test unauthorized access**

```bash
curl -s -w "\nHTTP %{http_code}\n" http://127.0.0.1:8000/auth/me
```

Expected: 401

- [ ] **Step 6: Test duplicate register**

```bash
curl -s -w "\nHTTP %{http_code}\n" -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"123456"}'
```

Expected: 409, "用户名已存在"

- [ ] **Step 7: Test wrong password**

```bash
curl -s -w "\nHTTP %{http_code}\n" -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"wrong"}'
```

Expected: 401, "用户名或密码错误"
