"""知识搜索测试

覆盖: API 层 200/422/401, Service 层 ES/降级
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ===========================================================================
# 测试数据工厂
# ===========================================================================


def make_mock_item(**overrides):
    defaults = {
        "id": 1,
        "appid": 0,
        "kb_id": 1,
        "cate_id": None,
        "name": "测试知识",
        "content": "测试内容",
        "abstract": "测试摘要",
        "author": "测试作者",
        "creator": "admin",
        "last_modify_user": None,
        "version": 1,
        "max_version": 1,
        "status": 3,
        "is_online": 1,
        "first_release_time": None,
        "last_release_time": None,
        "view_count": 0,
        "like_count": 0,
        "favorite_count": 0,
        "share_num": 0,
        "download_num": 0,
        "is_top": 0,
        "sort_order": None,
        "name_sort_key": None,
        "knowledge_type": 0,
        "dir_type": 0,
        "tag_ids": None,
        "attachment_ids": None,
        "create_time": datetime(2026, 5, 29),
        "update_time": datetime(2026, 5, 29),
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


# ===========================================================================
# API 层测试
# ===========================================================================


class TestSearchKnowledgeAPI:

    def test_search_200(self, client, auth_headers):
        from app.api import deps
        from app.services.knowledge_item import KnowledgeItemService
        from app.schemas.knowledge_item import KnowledgeItemOut

        mock_item = make_mock_item(id=1, name="React Guide")
        item_out = KnowledgeItemOut.model_validate(mock_item)

        async def mock_search_items(keyword, cate_id=None, status=None, limit=20, offset=0):
            return 1, [item_out]

        svc = MagicMock(spec=KnowledgeItemService)
        svc.search_items = mock_search_items

        client.app.dependency_overrides[deps.get_db] = lambda: None
        client.app.dependency_overrides[deps.get_current_user] = lambda: MagicMock()
        client.app.dependency_overrides[deps.get_knowledge_item_service] = lambda: svc

        resp = client.get("/v1/knowledge/search?keyword=React", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "React Guide"

    def test_search_empty_result(self, client, auth_headers):
        from app.api import deps
        from app.services.knowledge_item import KnowledgeItemService

        async def mock_search_items(keyword, cate_id=None, status=None, limit=20, offset=0):
            return 0, []

        svc = MagicMock(spec=KnowledgeItemService)
        svc.search_items = mock_search_items

        client.app.dependency_overrides[deps.get_db] = lambda: None
        client.app.dependency_overrides[deps.get_current_user] = lambda: MagicMock()
        client.app.dependency_overrides[deps.get_knowledge_item_service] = lambda: svc

        resp = client.get("/v1/knowledge/search?keyword=nonexistent", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_search_401_no_auth(self, client):
        resp = client.get("/v1/knowledge/search?keyword=test")
        assert resp.status_code == 401

    def test_search_422_missing_keyword(self, client, auth_headers):
        from app.api import deps

        client.app.dependency_overrides[deps.get_db] = lambda: None
        client.app.dependency_overrides[deps.get_current_user] = lambda: MagicMock()

        resp = client.get("/v1/knowledge/search", headers=auth_headers)
        assert resp.status_code == 422

    def test_search_422_empty_keyword(self, client, auth_headers):
        from app.api import deps

        client.app.dependency_overrides[deps.get_db] = lambda: None
        client.app.dependency_overrides[deps.get_current_user] = lambda: MagicMock()

        resp = client.get("/v1/knowledge/search?keyword=", headers=auth_headers)
        assert resp.status_code == 422


# ===========================================================================
# Service 层测试
# ===========================================================================


class TestSearchItemsService:

    @pytest.mark.asyncio
    async def test_search_items_es(self):
        from app.services.knowledge_item import KnowledgeItemService
        from app.schemas.knowledge_item import KnowledgeItemOut

        mock_item1 = make_mock_item(id=1, name="React Guide")
        mock_item2 = make_mock_item(id=2, name="Vue Guide")
        item_out1 = KnowledgeItemOut.model_validate(mock_item1)
        item_out2 = KnowledgeItemOut.model_validate(mock_item2)

        svc = KnowledgeItemService(db=MagicMock())

        # Mock ES search returns (total, [id, ...])
        async def mock_get_item(item_id):
            if item_id == 1:
                return item_out1
            if item_id == 2:
                return item_out2
            raise Exception("not found")

        svc.get_item = mock_get_item

        with patch("app.services.es_search.search_knowledge_items") as mock_es_search:
            mock_es_search.return_value = (2, [1, 2])

            total, items = await svc.search_items(keyword="Guide")

            assert total == 2
            assert len(items) == 2
            assert items[0].name == "React Guide"
            assert items[1].name == "Vue Guide"
            mock_es_search.assert_called_once_with(
                keyword="Guide",
                cate_id=None,
                status=None,
                limit=20,
                offset=0,
            )

    @pytest.mark.asyncio
    async def test_search_items_es_empty(self):
        from app.services.knowledge_item import KnowledgeItemService

        svc = KnowledgeItemService(db=MagicMock())

        with patch("app.services.es_search.search_knowledge_items") as mock_es_search:
            mock_es_search.return_value = (0, [])

            total, items = await svc.search_items(keyword="nonexistent")

            assert total == 0
            assert items == []

    @pytest.mark.asyncio
    async def test_search_items_fallback(self):
        from app.services.knowledge_item import KnowledgeItemService
        from app.schemas.knowledge_item import KnowledgeItemOut, KnowledgeItemListResponse

        mock_item = make_mock_item(id=1, name="MySQL Result")
        item_out = KnowledgeItemOut.model_validate(mock_item)

        svc = KnowledgeItemService(db=MagicMock())

        async def mock_list_items(search=None, cate_id=None, status=None, limit=20, offset=0, **kwargs):
            return KnowledgeItemListResponse(total=1, items=[item_out])

        svc.list_items = mock_list_items

        with patch("app.services.es_search.search_knowledge_items") as mock_es_search:
            mock_es_search.return_value = None  # ES 不可达

            total, items = await svc.search_items(keyword="MySQL")

            assert total == 1
            assert len(items) == 1
            assert items[0].name == "MySQL Result"

    @pytest.mark.asyncio
    async def test_search_items_es_skip_deleted(self):
        from app.services.knowledge_item import KnowledgeItemService
        from app.schemas.knowledge_item import KnowledgeItemOut

        mock_item1 = make_mock_item(id=1, name="Available")
        item_out1 = KnowledgeItemOut.model_validate(mock_item1)

        svc = KnowledgeItemService(db=MagicMock())

        async def mock_get_item(item_id):
            if item_id == 1:
                return item_out1
            if item_id == 2:
                from fastapi import HTTPException, status
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识条目不存在")
            raise Exception("unknown")

        svc.get_item = mock_get_item

        with patch("app.services.es_search.search_knowledge_items") as mock_es_search:
            # ES returns id 1 (exists) and id 2 (deleted)
            mock_es_search.return_value = (2, [1, 2])

            total, items = await svc.search_items(keyword="test")

            # total from ES is 2, but only 1 item resolved
            assert total == 2
            assert len(items) == 1
            assert items[0].id == 1
