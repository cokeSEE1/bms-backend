import uuid
from datetime import datetime
from io import BytesIO

from fastapi import HTTPException, UploadFile, status

from app.config import MAX_UPLOAD_SIZE, MINIO_BUCKET
from app.core.minio import get_minio
from app.schemas.upload import ImageUploadResponse

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}

EXT_MAP = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


class UploadService:
    @staticmethod
    async def save_image(file: UploadFile) -> ImageUploadResponse:
        if file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的图片类型: {file.content_type}，仅支持 JPEG/PNG/GIF/WebP",
            )

        content = await file.read()
        if len(content) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"图片大小超过限制 ({MAX_UPLOAD_SIZE // 1024 // 1024}MB)",
            )

        client = get_minio()
        if client is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="存储服务不可用",
            )

        now = datetime.now()
        subdir = f"{now.year:04d}{now.month:02d}"
        ext = EXT_MAP.get(file.content_type, ".jpg")
        filename = f"{uuid.uuid4().hex}{ext}"

        object_name = f"knowledge-images/{subdir}/{filename}"
        data = BytesIO(content)
        length = len(content)

        client.put_object(
            MINIO_BUCKET,
            object_name,
            data,
            length,
            content_type=file.content_type,
        )

        url = f"/v1/file/{object_name}"
        original_name = file.filename or "unknown"
        return ImageUploadResponse(url=url, filename=original_name, size=length)
