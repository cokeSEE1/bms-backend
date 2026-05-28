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
