from pydantic import BaseModel

from app.schemas.user import UserOut


class TokenOut(BaseModel):
    access_token: str
    user: UserOut
