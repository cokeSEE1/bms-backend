"""用户统计接口测试

覆盖: API 层 200/401, Service 层
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ===========================================================================
# 测试数据工厂
# ===========================================================================


def make_mock_item(**overrides):
    defaults = {
        "id": 1, "name": "测试知识", "update_time": datetime(2026, 5, 29),
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


# ===========================================================================
# API 层测试
# ===========================================================================


class TestGetUserStats:

    def test_get_user_stats_200(self, client, auth_headers):
        from app.api import deps
        from app.services.user_stats import UserStatsService, UserStatsOut as SvcUserStatsOut

        user = MagicMock()
        user.username = "testuser"

        async def mock_get_stats(username):
            return SvcUserStatsOut(read_count=128, original_count=36, total_read_count=520)

        svc = MagicMock(spec=UserStatsService)
        svc.get_stats = mock_get_stats

        client.app.dependency_overrides[deps.get_db] = lambda: None
        client.app.dependency_overrides[deps.get_current_user] = lambda: user
        client.app.dependency_overrides[deps.get_user_stats_service] = lambda: svc

        resp = client.get("/v1/user/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["read_count"] == 128
        assert data["original_count"] == 36
        assert data["total_read_count"] == 520

    def test_get_user_stats_401_no_auth(self, client):
        resp = client.get("/v1/user/stats")
        assert resp.status_code == 401


class TestGetParticipated:

    def test_get_participated_200(self, client, auth_headers):
        from app.api import deps
        from app.services.user_stats import UserStatsService

        user = MagicMock()
        user.username = "testuser"

        mock1 = make_mock_item(id=1, name="知识一", update_time=datetime(2026, 5, 20))
        mock2 = make_mock_item(id=2, name="知识二", update_time=datetime(2026, 5, 18))

        async def mock_get_participated(username, limit=10):
            return [mock1, mock2]

        svc = MagicMock(spec=UserStatsService)
        svc.get_participated = mock_get_participated

        client.app.dependency_overrides[deps.get_db] = lambda: None
        client.app.dependency_overrides[deps.get_current_user] = lambda: user
        client.app.dependency_overrides[deps.get_user_stats_service] = lambda: svc

        resp = client.get("/v1/user/participated", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["items"][0]["name"] == "知识一"
        assert data["items"][1]["name"] == "知识二"

    def test_get_participated_empty(self, client, auth_headers):
        from app.api import deps
        from app.services.user_stats import UserStatsService

        user = MagicMock()
        user.username = "testuser"

        async def mock_get_participated(username, limit=10):
            return []

        svc = MagicMock(spec=UserStatsService)
        svc.get_participated = mock_get_participated

        client.app.dependency_overrides[deps.get_db] = lambda: None
        client.app.dependency_overrides[deps.get_current_user] = lambda: user
        client.app.dependency_overrides[deps.get_user_stats_service] = lambda: svc

        resp = client.get("/v1/user/participated", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    def test_get_participated_401_no_auth(self, client):
        resp = client.get("/v1/user/participated")
        assert resp.status_code == 401


# ===========================================================================
# Service 层测试
# ===========================================================================


class TestUserStatsService:

    @pytest.mark.asyncio
    async def test_get_stats(self):
        from unittest.mock import patch
        from app.services.user_stats import UserStatsService

        with patch("app.services.user_stats.KnowledgeItemModel") as mock_model:
            mock_model.count_items_by_creator = AsyncMock(return_value=10)
            mock_model.sum_view_count_by_creator = AsyncMock(return_value=500)

            svc = UserStatsService(db=MagicMock())
            result = await svc.get_stats("testuser")

            mock_model.count_items_by_creator.assert_called_once()
            mock_model.sum_view_count_by_creator.assert_called_once()
            assert result.read_count == 128
            assert result.original_count == 10
            assert result.total_read_count == 500

    @pytest.mark.asyncio
    async def test_get_participated(self):
        from unittest.mock import patch
        from app.services.user_stats import UserStatsService

        mock1 = make_mock_item(id=1, name="知识一")
        mock2 = make_mock_item(id=2, name="知识二")

        with patch("app.services.user_stats.KnowledgeItemModel") as mock_model:
            mock_model.list_participated = AsyncMock(return_value=[mock1, mock2])

            svc = UserStatsService(db=MagicMock())
            result = await svc.get_participated("testuser")

            mock_model.list_participated.assert_called_once()
            assert len(result) == 2
            assert result[0].name == "知识一"
            assert result[1].name == "知识二"

    @pytest.mark.asyncio
    async def test_get_stats_zero_items(self):
        from unittest.mock import patch
        from app.services.user_stats import UserStatsService

        with patch("app.services.user_stats.KnowledgeItemModel") as mock_model:
            mock_model.count_items_by_creator = AsyncMock(return_value=0)
            mock_model.sum_view_count_by_creator = AsyncMock(return_value=0)

            svc = UserStatsService(db=MagicMock())
            result = await svc.get_stats("newuser")

            assert result.original_count == 0
            assert result.total_read_count == 0
            assert result.read_count == 128  # placeholder


# ===========================================================================
# Schema 测试
# ===========================================================================


class TestUserStatsSchema:

    def test_user_stats_out(self):
        from app.schemas.user_stats import UserStatsOut

        stats = UserStatsOut(read_count=100, original_count=36, total_read_count=520)
        assert stats.read_count == 100
        assert stats.original_count == 36
        assert stats.total_read_count == 520

    def test_participated_item_out(self):
        from app.schemas.user_stats import ParticipatedItemOut

        item = ParticipatedItemOut(id=1, name="测试", update_time=datetime(2026, 5, 29))
        assert item.id == 1
        assert item.name == "测试"

    def test_participated_list_out(self):
        from app.schemas.user_stats import ParticipatedItemOut, ParticipatedListOut

        items = [
            ParticipatedItemOut(id=1, name="A", update_time=datetime(2026, 5, 20)),
            ParticipatedItemOut(id=2, name="B", update_time=datetime(2026, 5, 18)),
        ]
        result = ParticipatedListOut(items=items)
        assert len(result.items) == 2
