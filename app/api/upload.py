from fastapi import APIRouter, Depends, HTTPException, UploadFile
from minio.error import S3Error
from starlette.responses import StreamingResponse

from app.api.deps import get_current_user
from app.config import MINIO_BUCKET
from app.core.minio import get_minio
from app.entities.user import User
from app.schemas.upload import ImageUploadResponse
from app.services.upload import UploadService

router = APIRouter()


@router.post("/v1/upload/image", response_model=ImageUploadResponse)
async def upload_image(
    file: UploadFile,
    _current_user: User = Depends(get_current_user),
) -> ImageUploadResponse:
    return await UploadService.save_image(file)


@router.get("/v1/file/{path:path}")
async def download_file(path: str) -> StreamingResponse:
    """公开端点，无需认证（图片 URL 嵌入富文本内容，无法带 token）"""
    try:
        client = get_minio()
        if client is None:
            raise HTTPException(status_code=503, detail="存储服务不可用")
        response = client.get_object(MINIO_BUCKET, path)
        return StreamingResponse(
            response.stream(amt=64 * 1024),
            media_type=response.headers.get("Content-Type", "application/octet-stream"),
            headers={"Cache-Control": "public, max-age=31536000, immutable"},
        )
    except S3Error:
        raise HTTPException(status_code=404, detail="文件不存在")
