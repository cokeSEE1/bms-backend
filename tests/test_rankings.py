"""排行榜接口测试

覆盖: API 层 200/401, Service 层, Model 层
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ===========================================================================
# 测试数据工厂
# ===========================================================================


def make_mock_knowledge_item(**overrides):
    defaults = {
        "id": 1, "name": "测试知识", "author": "技术部",
        "view_count": 100, "like_count": 50, "favorite_count": 30,
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


# ===========================================================================
# API 层测试
# ===========================================================================


class TestReadingStars:

    def test_reading_stars_200(self, client, auth_headers):
        from app.api import deps
        from app.services.ranking import RankItemOut, RankingService

        async def mock_get_reading_stars(limit):
            return [RankItemOut(rank=1, name="张伟", department="技术部", count=328)]

        svc = MagicMock(spec=RankingService)
        svc.get_reading_stars = mock_get_reading_stars

        client.app.dependency_overrides[deps.get_db] = lambda: None
        client.app.dependency_overrides[deps.get_current_user] = lambda: MagicMock()

        with patch("app.api.ranking.RankingService", return_value=svc):
            resp = client.get("/v1/rankings/reading-stars", headers=auth_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert "items" in data
            assert len(data["items"]) == 1
            assert data["items"][0]["name"] == "张伟"
            assert data["items"][0]["rank"] == 1

    def test_reading_stars_401_no_auth(self, client):
        resp = client.get("/v1/rankings/reading-stars")
        assert resp.status_code == 401


class TestOriginalStars:

    def test_original_stars_200(self, client, auth_headers):
        from app.api import deps
        from app.services.ranking import RankItemOut, RankingService

        async def mock_get_original_stars(limit):
            return [RankItemOut(rank=1, name="陈明", department="技术部", count=45)]

        svc = MagicMock(spec=RankingService)
        svc.get_original_stars = mock_get_original_stars

        client.app.dependency_overrides[deps.get_db] = lambda: None
        client.app.dependency_overrides[deps.get_current_user] = lambda: MagicMock()

        with patch("app.api.ranking.RankingService", return_value=svc):
            resp = client.get("/v1/rankings/original-stars", headers=auth_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["items"]) == 1


class TestHotStars:

    def test_hot_stars_200(self, client, auth_headers):
        from app.api import deps
        from app.services.ranking import RankItemOut, RankingService

        async def mock_get_hot_stars(limit):
            return [RankItemOut(rank=1, name="李四", department="技术部", count=892)]

        svc = MagicMock(spec=RankingService)
        svc.get_hot_stars = mock_get_hot_stars

        client.app.dependency_overrides[deps.get_db] = lambda: None
        client.app.dependency_overrides[deps.get_current_user] = lambda: MagicMock()

        with patch("app.api.ranking.RankingService", return_value=svc):
            resp = client.get("/v1/rankings/hot-stars", headers=auth_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["items"]) == 1


class TestLimitParam:

    def test_limit_param_respected(self, client, auth_headers):
        from app.api import deps
        from app.services.ranking import RankItemOut, RankingService

        received_limit = None

        async def mock_get_reading_stars(limit):
            nonlocal received_limit
            received_limit = limit
            return [RankItemOut(rank=1, name="test", department="test", count=1)]

        svc = MagicMock(spec=RankingService)
        svc.get_reading_stars = mock_get_reading_stars

        client.app.dependency_overrides[deps.get_db] = lambda: None
        client.app.dependency_overrides[deps.get_current_user] = lambda: MagicMock()

        with patch("app.api.ranking.RankingService", return_value=svc):
            resp = client.get("/v1/rankings/reading-stars?limit=5", headers=auth_headers)
            assert resp.status_code == 200
            assert received_limit == 5


# ===========================================================================
# Service 层测试
# ===========================================================================


class TestRankingService:

    @pytest.mark.asyncio
    async def test_get_reading_stars(self):
        mock_item = make_mock_knowledge_item(name="测试知识A", author="技术部", view_count=200)

        with patch("app.services.ranking.KnowledgeItemModel") as mock_model:
            mock_model.get_top_by_field = AsyncMock(return_value=[mock_item])

            from app.services.ranking import RankingService

            svc = RankingService(db=MagicMock())
            result = await svc.get_reading_stars(limit=10)

            mock_model.get_top_by_field.assert_called_once()
            call_args = mock_model.get_top_by_field.call_args
            assert call_args.args[1] == 'view_count'
            assert call_args.args[2] == 10

            assert len(result) == 1
            assert result[0].rank == 1
            assert result[0].name == "测试知识A"
            assert result[0].department == "技术部"
            assert result[0].count == 200

    @pytest.mark.asyncio
    async def test_get_original_stars(self):
        mock_item = make_mock_knowledge_item(name="测试知识B", author="产品部", favorite_count=45)

        with patch("app.services.ranking.KnowledgeItemModel") as mock_model:
            mock_model.get_top_by_field = AsyncMock(return_value=[mock_item])

            from app.services.ranking import RankingService

            svc = RankingService(db=MagicMock())
            result = await svc.get_original_stars(limit=10)

            mock_model.get_top_by_field.assert_called_once()
            call_args = mock_model.get_top_by_field.call_args
            assert call_args.args[1] == 'favorite_count'
            assert result[0].name == "测试知识B"
            assert result[0].count == 45

    @pytest.mark.asyncio
    async def test_get_hot_stars(self):
        mock_item = make_mock_knowledge_item(name="测试知识C", author="运营部", like_count=88)

        with patch("app.services.ranking.KnowledgeItemModel") as mock_model:
            mock_model.get_top_by_field = AsyncMock(return_value=[mock_item])

            from app.services.ranking import RankingService

            svc = RankingService(db=MagicMock())
            result = await svc.get_hot_stars(limit=10)

            mock_model.get_top_by_field.assert_called_once()
            call_args = mock_model.get_top_by_field.call_args
            assert call_args.args[1] == 'like_count'
            assert result[0].name == "测试知识C"
            assert result[0].count == 88

    @pytest.mark.asyncio
    async def test_get_original_stars_with_unknown_author(self):
        mock_item = make_mock_knowledge_item(name="匿名知识", author=None, favorite_count=10)

        with patch("app.services.ranking.KnowledgeItemModel") as mock_model:
            mock_model.get_top_by_field = AsyncMock(return_value=[mock_item])

            from app.services.ranking import RankingService

            svc = RankingService(db=MagicMock())
            result = await svc.get_original_stars(limit=10)

            assert result[0].department == "未知"


# ===========================================================================
# Model 层测试
# ===========================================================================


class TestKnowledgeItemModelRanking:

    @pytest.mark.asyncio
    async def test_get_top_by_field_valid(self):
        mock_item = make_mock_knowledge_item()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_item]

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        from app.models.knowledge_item import KnowledgeItemModel

        result = await KnowledgeItemModel.get_top_by_field(mock_db, 'view_count', limit=5)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_top_by_field_invalid_field(self):
        from app.models.knowledge_item import KnowledgeItemModel

        with pytest.raises(ValueError, match="Invalid ranking field"):
            await KnowledgeItemModel.get_top_by_field(AsyncMock(), 'invalid_field')
