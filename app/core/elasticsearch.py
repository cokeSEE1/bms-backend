from elasticsearch import AsyncElasticsearch

from app.config import ELASTICSEARCH_URL

_es: AsyncElasticsearch | None = None


async def init_es() -> None:
    global _es
    try:
        _es = AsyncElasticsearch(ELASTICSEARCH_URL)
        await _es.ping()
    except Exception:
        _es = None


async def close_es() -> None:
    global _es
    if _es is not None:
        await _es.close()
        _es = None


def get_es() -> AsyncElasticsearch | None:
    return _es
