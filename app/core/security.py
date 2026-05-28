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
