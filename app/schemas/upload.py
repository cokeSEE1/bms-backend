from pydantic import BaseModel


class ImageUploadResponse(BaseModel):
    url: str
    filename: str
    size: int
