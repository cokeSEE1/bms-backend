from minio import Minio

from app.config import MINIO_ACCESS_KEY, MINIO_BUCKET, MINIO_ENDPOINT, MINIO_SECRET_KEY, MINIO_SECURE

_minio: Minio | None = None


async def init_minio() -> None:
    global _minio
    try:
        _minio = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE,
        )
        _minio.list_buckets()
    except Exception:
        _minio = None  # MinIO 不可用时降级，不影响启动


async def close_minio() -> None:
    global _minio
    _minio = None


def get_minio() -> Minio | None:
    """返回 MinIO 客户端，未初始化时返回 None（降级放行）"""
    return _minio
