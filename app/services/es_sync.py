from app.core.elasticsearch import get_es
from app.core.es_index import KNOWLEDGE_ITEM_INDEX
from app.entities.knowledge_item import KnowledgeItem


async def sync_knowledge_item(item: KnowledgeItem) -> None:
    es = get_es()
    if es is None:
        return
    try:
        await es.index(
            index=KNOWLEDGE_ITEM_INDEX,
            id=str(item.id),
            document={
                "id": item.id,
                "appid": item.appid,
                "kb_id": item.kb_id,
                "cate_id": item.cate_id,
                "name": item.name,
                "abstract": item.abstract,
                "content": item.content,
                "author": item.author,
                "creator": item.creator,
                "status": item.status,
                "is_online": item.is_online,
                "version": item.version,
                "dir_type": item.dir_type,
                "knowledge_type": item.knowledge_type,
                "view_count": item.view_count,
                "like_count": item.like_count,
                "favorite_count": item.favorite_count,
                "share_num": item.share_num,
                "download_num": item.download_num,
                "is_top": item.is_top,
                "create_time": (
                    item.create_time.isoformat() if item.create_time else None
                ),
                "update_time": (
                    item.update_time.isoformat() if item.update_time else None
                ),
                "last_release_time": (
                    item.last_release_time.isoformat()
                    if item.last_release_time
                    else None
                ),
                "tag_ids": item.tag_ids,
            },
            refresh=True,
        )
    except Exception:
        pass


async def delete_from_es(item_id: int) -> None:
    es = get_es()
    if es is None:
        return
    try:
        await es.delete(index=KNOWLEDGE_ITEM_INDEX, id=str(item_id))
    except Exception:
        pass
