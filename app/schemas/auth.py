from pydantic import BaseModel

from app.schemas.user import UserOut


class TokenOut(BaseModel):
    access_token: str
    user: UserOut


class LogoutOut(BaseModel):
    message: str
