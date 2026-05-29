from app.core.elasticsearch import get_es
from app.core.es_index import KNOWLEDGE_ITEM_INDEX


async def search_knowledge_items(
    keyword: str,
    cate_id: int | None = None,
    status: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[int, list[int]] | None:
    es = get_es()
    if es is None:
        return None

    must: list[dict] = []
    if cate_id is not None:
        must.append({"term": {"cate_id": cate_id}})
    if status is not None:
        must.append({"term": {"status": status}})

    try:
        result = await es.search(
            index=KNOWLEDGE_ITEM_INDEX,
            body={
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": keyword,
                                    "fields": ["name^3", "abstract^2", "content"],
                                }
                            }
                        ]
                        + must,
                    }
                },
                "from": offset,
                "size": limit,
                "sort": [{"_score": {"order": "desc"}}, {"update_time": {"order": "desc"}}],
                "_source": ["id"],
            },
        )
        total = result["hits"]["total"]["value"]
        ids = [int(hit["_source"]["id"]) for hit in result["hits"]["hits"]]
        return total, ids
    except Exception:
        return None
