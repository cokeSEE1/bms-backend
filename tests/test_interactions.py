"""点赞/收藏/分享 接口测试

覆盖: API 层 200/404/422, Service 层 业务逻辑, Model 层 计数器增减
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ===========================================================================
# 测试数据工厂
# ===========================================================================


def make_mock_item(**overrides):
    defaults = {
        "id": 1, "appid": 0, "kb_id": 1, "cate_id": 5,
        "name": "测试知识", "content": "内容", "abstract": "摘要",
        "author": "张三", "creator": "admin", "last_modify_user": "admin",
        "version": 1, "max_version": 3, "status": 3, "is_online": 1,
        "first_release_time": datetime(2026, 1, 1),
        "last_release_time": None,
        "view_count": 10, "like_count": 5, "favorite_count": 3,
        "share_num": 2, "download_num": 1, "is_top": 0,
        "sort_order": None, "name_sort_key": None,
        "knowledge_type": 0, "dir_type": 2,
        "tag_ids": None, "attachment_ids": None,
        "create_time": datetime(2026, 1, 1),
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


class TestLikeAPI:

    @pytest.mark.parametrize("action,expected", [("like", 6), ("unlike", 4)])
    def test_toggle_like_200(self, client, auth_headers, action, expected):
        from app.api import deps
        from app.services.knowledge_item import KnowledgeItemService
        from app.schemas.knowledge_item import KnowledgeItemOut

        async def mock_toggle(item_id, _action):
            mock = make_mock_item(like_count=expected)
            return KnowledgeItemOut.model_validate(mock)

        svc = MagicMock(spec=KnowledgeItemService)
        svc.toggle_like = mock_toggle

        client.app.dependency_overrides[deps.get_db] = lambda: None
        client.app.dependency_overrides[deps.get_current_user] = lambda: MagicMock()
        client.app.dependency_overrides[deps.get_knowledge_item_service] = lambda: svc

        resp = client.post("/v1/knowledge/item/1/like", json={"action": action}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["like_count"] == expected

    def test_toggle_like_404(self, client, auth_headers):
        from app.api import deps
        from app.services.knowledge_item import KnowledgeItemService
        from fastapi import HTTPException, status

        async def mock_toggle(item_id, _action):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识条目不存在")

        svc = MagicMock(spec=KnowledgeItemService)
        svc.toggle_like = mock_toggle

        client.app.dependency_overrides[deps.get_db] = lambda: None
        client.app.dependency_overrides[deps.get_current_user] = lambda: MagicMock()
        client.app.dependency_overrides[deps.get_knowledge_item_service] = lambda: svc

        resp = client.post("/v1/knowledge/item/999/like", json={"action": "like"}, headers=auth_headers)
        assert resp.status_code == 404

    def test_toggle_like_422_invalid_action(self, client, auth_headers):
        from app.api import deps

        client.app.dependency_overrides[deps.get_db] = lambda: None
        client.app.dependency_overrides[deps.get_current_user] = lambda: MagicMock()

        resp = client.post("/v1/knowledge/item/1/like", json={"action": "invalid"}, headers=auth_headers)
        assert resp.status_code == 422

    def test_toggle_like_401_no_auth(self, client):
        resp = client.post("/v1/knowledge/item/1/like", json={"action": "like"})
        assert resp.status_code == 401


class TestFavoriteAPI:

    def test_toggle_favorite_200(self, client, auth_headers):
        from app.api import deps
        from app.services.knowledge_item import KnowledgeItemService
        from app.schemas.knowledge_item import KnowledgeItemOut

        async def mock_toggle(item_id, _action):
            mock = make_mock_item(favorite_count=4)
            return KnowledgeItemOut.model_validate(mock)

        svc = MagicMock(spec=KnowledgeItemService)
        svc.toggle_favorite = mock_toggle

        client.app.dependency_overrides[deps.get_db] = lambda: None
        client.app.dependency_overrides[deps.get_current_user] = lambda: MagicMock()
        client.app.dependency_overrides[deps.get_knowledge_item_service] = lambda: svc

        resp = client.post("/v1/knowledge/item/1/favorite", json={"action": "favorite"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["favorite_count"] == 4

    def test_toggle_favorite_422_invalid_action(self, client, auth_headers):
        from app.api import deps

        client.app.dependency_overrides[deps.get_db] = lambda: None
        client.app.dependency_overrides[deps.get_current_user] = lambda: MagicMock()

        resp = client.post("/v1/knowledge/item/1/favorite", json={"action": "invalid"}, headers=auth_headers)
        assert resp.status_code == 422


class TestShareAPI:

    def test_share_item_200(self, client, auth_headers):
        from app.api import deps
        from app.services.knowledge_item import KnowledgeItemService
        from app.schemas.knowledge_item import KnowledgeItemOut

        async def mock_share(item_id):
            mock = make_mock_item(share_num=3)
            return KnowledgeItemOut.model_validate(mock)

        svc = MagicMock(spec=KnowledgeItemService)
        svc.share_item = mock_share

        client.app.dependency_overrides[deps.get_db] = lambda: None
        client.app.dependency_overrides[deps.get_current_user] = lambda: MagicMock()
        client.app.dependency_overrides[deps.get_knowledge_item_service] = lambda: svc

        resp = client.post("/v1/knowledge/item/1/share", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["share_num"] == 3

    def test_share_item_401_no_auth(self, client):
        resp = client.post("/v1/knowledge/item/1/share")
        assert resp.status_code == 401


# ===========================================================================
# Service 层测试
# ===========================================================================


class TestToggleLikeService:

    @pytest.mark.asyncio
    async def test_like_increments_count(self):
        from unittest.mock import patch

        mock_item = make_mock_item(like_count=5)

        with patch("app.services.knowledge_item.KnowledgeItemModel") as mock_model:
            mock_model.get_by_id = AsyncMock(return_value=mock_item)
            mock_model.increment_like_count = AsyncMock()
            mock_model.decrement_like_count = AsyncMock()

            from app.services.knowledge_item import KnowledgeItemService

            svc = KnowledgeItemService(db=MagicMock())
            result = await svc.toggle_like(1, "like")

            mock_model.increment_like_count.assert_called_once()
            mock_model.decrement_like_count.assert_not_called()

    @pytest.mark.asyncio
    async def test_unlike_decrements_count(self):
        from unittest.mock import patch

        mock_item = make_mock_item(like_count=5)

        with patch("app.services.knowledge_item.KnowledgeItemModel") as mock_model:
            mock_model.get_by_id = AsyncMock(return_value=mock_item)
            mock_model.increment_like_count = AsyncMock()
            mock_model.decrement_like_count = AsyncMock()

            from app.services.knowledge_item import KnowledgeItemService

            svc = KnowledgeItemService(db=MagicMock())
            await svc.toggle_like(1, "unlike")

            mock_model.decrement_like_count.assert_called_once()
            mock_model.increment_like_count.assert_not_called()

    @pytest.mark.asyncio
    async def test_like_404_when_item_missing(self):
        from unittest.mock import patch
        from fastapi import HTTPException

        with patch("app.services.knowledge_item.KnowledgeItemModel") as mock_model:
            mock_model.get_by_id = AsyncMock(return_value=None)

            from app.services.knowledge_item import KnowledgeItemService

            svc = KnowledgeItemService(db=MagicMock())
            with pytest.raises(HTTPException) as exc:
                await svc.toggle_like(999, "like")
            assert exc.value.status_code == 404


class TestToggleFavoriteService:

    @pytest.mark.asyncio
    async def test_favorite_increments_count(self):
        from unittest.mock import patch

        mock_item = make_mock_item(favorite_count=3)

        with patch("app.services.knowledge_item.KnowledgeItemModel") as mock_model:
            mock_model.get_by_id = AsyncMock(return_value=mock_item)
            mock_model.increment_favorite_count = AsyncMock()
            mock_model.decrement_favorite_count = AsyncMock()

            from app.services.knowledge_item import KnowledgeItemService

            svc = KnowledgeItemService(db=MagicMock())
            await svc.toggle_favorite(1, "favorite")

            mock_model.increment_favorite_count.assert_called_once()

    @pytest.mark.asyncio
    async def test_unfavorite_decrements_count(self):
        from unittest.mock import patch

        mock_item = make_mock_item(favorite_count=3)

        with patch("app.services.knowledge_item.KnowledgeItemModel") as mock_model:
            mock_model.get_by_id = AsyncMock(return_value=mock_item)
            mock_model.increment_favorite_count = AsyncMock()
            mock_model.decrement_favorite_count = AsyncMock()

            from app.services.knowledge_item import KnowledgeItemService

            svc = KnowledgeItemService(db=MagicMock())
            await svc.toggle_favorite(1, "unfavorite")

            mock_model.decrement_favorite_count.assert_called_once()


class TestShareService:

    @pytest.mark.asyncio
    async def test_share_increments_num(self):
        from unittest.mock import patch

        mock_item = make_mock_item(share_num=2)

        with patch("app.services.knowledge_item.KnowledgeItemModel") as mock_model:
            mock_model.get_by_id = AsyncMock(return_value=mock_item)
            mock_model.increment_share_num = AsyncMock()

            from app.services.knowledge_item import KnowledgeItemService

            svc = KnowledgeItemService(db=MagicMock())
            await svc.share_item(1)

            mock_model.increment_share_num.assert_called_once()

    @pytest.mark.asyncio
    async def test_share_404_when_item_missing(self):
        from unittest.mock import patch
        from fastapi import HTTPException

        with patch("app.services.knowledge_item.KnowledgeItemModel") as mock_model:
            mock_model.get_by_id = AsyncMock(return_value=None)

            from app.services.knowledge_item import KnowledgeItemService

            svc = KnowledgeItemService(db=MagicMock())
            with pytest.raises(HTTPException) as exc:
                await svc.share_item(999)
            assert exc.value.status_code == 404


# ===========================================================================
# Schema 测试
# ===========================================================================


class TestToggleActionRequest:

    def test_valid_like(self):
        from app.schemas.knowledge_item import ToggleActionRequest

        req = ToggleActionRequest(action="like")
        assert req.action == "like"

    def test_valid_unlike(self):
        from app.schemas.knowledge_item import ToggleActionRequest

        req = ToggleActionRequest(action="unlike")
        assert req.action == "unlike"

    def test_invalid_action(self):
        from app.schemas.knowledge_item import ToggleActionRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ToggleActionRequest(action="invalid")


class TestFavoriteActionRequest:

    def test_valid_favorite(self):
        from app.schemas.knowledge_item import FavoriteActionRequest

        req = FavoriteActionRequest(action="favorite")
        assert req.action == "favorite"

    def test_valid_unfavorite(self):
        from app.schemas.knowledge_item import FavoriteActionRequest

        req = FavoriteActionRequest(action="unfavorite")
        assert req.action == "unfavorite"

    def test_invalid_action(self):
        from app.schemas.knowledge_item import FavoriteActionRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            FavoriteActionRequest(action="invalid")
