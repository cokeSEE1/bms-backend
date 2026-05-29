from app.core.elasticsearch import get_es

KNOWLEDGE_ITEM_INDEX = "knowledge_item"

KNOWLEDGE_ITEM_MAPPING = {
    "properties": {
        "id": {"type": "integer"},
        "appid": {"type": "integer"},
        "kb_id": {"type": "integer"},
        "cate_id": {"type": "integer"},
        "name": {
            "type": "text",
            "analyzer": "ik_max_word",
            "search_analyzer": "ik_smart",
            "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
        },
        "abstract": {
            "type": "text",
            "analyzer": "ik_max_word",
            "search_analyzer": "ik_smart",
        },
        "content": {
            "type": "text",
            "analyzer": "ik_max_word",
            "search_analyzer": "ik_smart",
        },
        "author": {"type": "keyword"},
        "creator": {"type": "keyword"},
        "status": {"type": "integer"},
        "is_online": {"type": "integer"},
        "version": {"type": "integer"},
        "dir_type": {"type": "integer"},
        "knowledge_type": {"type": "integer"},
        "view_count": {"type": "integer"},
        "like_count": {"type": "integer"},
        "favorite_count": {"type": "integer"},
        "share_num": {"type": "integer"},
        "download_num": {"type": "integer"},
        "is_top": {"type": "integer"},
        "create_time": {"type": "date"},
        "update_time": {"type": "date"},
        "last_release_time": {"type": "date"},
        "tag_ids": {"type": "keyword"},
    }
}


async def ensure_index() -> None:
    es = get_es()
    if es is None:
        return
    exists = await es.indices.exists(index=KNOWLEDGE_ITEM_INDEX)
    if not exists:
        await es.indices.create(
            index=KNOWLEDGE_ITEM_INDEX,
            body={
                "settings": {"number_of_shards": 1, "number_of_replicas": 0},
                "mappings": KNOWLEDGE_ITEM_MAPPING,
            },
        )
