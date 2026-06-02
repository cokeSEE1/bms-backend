"""评论接口测试

覆盖: API 层 201/200/404/422, Service 层, Model 层
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ===========================================================================
# 测试数据工厂
# ===========================================================================


def make_mock_comment(**overrides):
    defaults = {
        "id": 1, "knowledge_id": 1, "user_id": 1,
        "content": "测试评论",
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


class TestCreateComment:

    def test_create_comment_201(self, client, auth_headers):
        from app.api import deps
        from app.services.comment import CommentService
        from app.schemas.comment import CommentOut

        async def mock_create(req, user_id):
            mock = make_mock_comment(content=req.content)
            return CommentOut.model_validate(mock)

        svc = MagicMock(spec=CommentService)
        svc.create_comment = mock_create

        client.app.dependency_overrides[deps.get_db] = lambda: None
        client.app.dependency_overrides[deps.get_current_user] = lambda: MagicMock()
        client.app.dependency_overrides[deps.get_comment_service] = lambda: svc

        resp = client.post("/v1/comments", json={
            "knowledge_id": 1, "content": "好文章",
        }, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["content"] == "好文章"

    def test_create_comment_401_no_auth(self, client):
        resp = client.post("/v1/comments", json={
            "knowledge_id": 1, "content": "test",
        })
        assert resp.status_code == 401

    def test_create_comment_422_empty_content(self, client, auth_headers):
        from app.api import deps

        client.app.dependency_overrides[deps.get_db] = lambda: None
        client.app.dependency_overrides[deps.get_current_user] = lambda: MagicMock()

        resp = client.post("/v1/comments", json={
            "knowledge_id": 1, "content": "",
        }, headers=auth_headers)
        assert resp.status_code == 422


class TestListComments:

    def test_list_comments_200(self, client, auth_headers):
        from app.api import deps
        from app.services.comment import CommentService
        from app.schemas.comment import CommentListResponse, CommentOut

        async def mock_list(knowledge_id, page, page_size):
            mock1 = make_mock_comment(id=1, content="第一条")
            mock2 = make_mock_comment(id=2, content="第二条")
            return CommentListResponse(
                total=2,
                items=[CommentOut.model_validate(mock1), CommentOut.model_validate(mock2)],
            )

        svc = MagicMock(spec=CommentService)
        svc.list_comments = mock_list

        client.app.dependency_overrides[deps.get_db] = lambda: None
        client.app.dependency_overrides[deps.get_current_user] = lambda: MagicMock()
        client.app.dependency_overrides[deps.get_comment_service] = lambda: svc

        resp = client.get("/v1/comments?knowledge_id=1", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_list_comments_empty(self, client, auth_headers):
        from app.api import deps
        from app.services.comment import CommentService
        from app.schemas.comment import CommentListResponse

        async def mock_list(knowledge_id, page, page_size):
            return CommentListResponse(total=0, items=[])

        svc = MagicMock(spec=CommentService)
        svc.list_comments = mock_list

        client.app.dependency_overrides[deps.get_db] = lambda: None
        client.app.dependency_overrides[deps.get_current_user] = lambda: MagicMock()
        client.app.dependency_overrides[deps.get_comment_service] = lambda: svc

        resp = client.get("/v1/comments?knowledge_id=999", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


class TestDeleteComment:

    def test_delete_comment_204(self, client, auth_headers):
        from app.api import deps
        from app.services.comment import CommentService

        async def mock_delete(comment_id):
            pass

        svc = MagicMock(spec=CommentService)
        svc.delete_comment = mock_delete

        client.app.dependency_overrides[deps.get_db] = lambda: None
        client.app.dependency_overrides[deps.get_current_user] = lambda: MagicMock()
        client.app.dependency_overrides[deps.get_comment_service] = lambda: svc

        resp = client.delete("/v1/comments/1", headers=auth_headers)
        assert resp.status_code == 204

    def test_delete_comment_404(self, client, auth_headers):
        from app.api import deps
        from app.services.comment import CommentService
        from fastapi import HTTPException, status

        async def mock_delete(comment_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评论不存在")

        svc = MagicMock(spec=CommentService)
        svc.delete_comment = mock_delete

        client.app.dependency_overrides[deps.get_db] = lambda: None
        client.app.dependency_overrides[deps.get_current_user] = lambda: MagicMock()
        client.app.dependency_overrides[deps.get_comment_service] = lambda: svc

        resp = client.delete("/v1/comments/999", headers=auth_headers)
        assert resp.status_code == 404


# ===========================================================================
# Service 层测试
# ===========================================================================


class TestCommentService:

    @pytest.mark.asyncio
    async def test_create_comment(self):
        from unittest.mock import patch

        mock_comment = make_mock_comment()
        with patch("app.services.comment.CommentModel") as mock_model:
            mock_model.create = AsyncMock(return_value=mock_comment)

            from app.services.comment import CommentService
            from app.schemas.comment import CommentCreate

            svc = CommentService(db=MagicMock())
            result = await svc.create_comment(CommentCreate(knowledge_id=1, content="测试"), user_id=1)

            mock_model.create.assert_called_once()
            call_kwargs = mock_model.create.call_args.kwargs
            assert call_kwargs["knowledge_id"] == 1
            assert call_kwargs["user_id"] == 1
            assert call_kwargs["content"] == "测试"
            assert result.content == "测试评论"

    @pytest.mark.asyncio
    async def test_list_comments(self):
        from unittest.mock import patch

        mock1 = make_mock_comment(id=1)
        mock2 = make_mock_comment(id=2)
        with patch("app.services.comment.CommentModel") as mock_model:
            mock_model.list_by_knowledge = AsyncMock(return_value=(2, [mock1, mock2]))

            from app.services.comment import CommentService

            svc = CommentService(db=MagicMock())
            result = await svc.list_comments(knowledge_id=1, page=1, page_size=20)

            assert result.total == 2
            assert len(result.items) == 2

    @pytest.mark.asyncio
    async def test_delete_comment(self):
        from unittest.mock import patch

        mock_comment = make_mock_comment()
        with patch("app.services.comment.CommentModel") as mock_model:
            mock_model.get_by_id = AsyncMock(return_value=mock_comment)
            mock_model.soft_delete = AsyncMock()

            from app.services.comment import CommentService

            svc = CommentService(db=MagicMock())
            await svc.delete_comment(1)

            mock_model.soft_delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_comment_404(self):
        from unittest.mock import patch
        from fastapi import HTTPException

        with patch("app.services.comment.CommentModel") as mock_model:
            mock_model.get_by_id = AsyncMock(return_value=None)

            from app.services.comment import CommentService

            svc = CommentService(db=MagicMock())
            with pytest.raises(HTTPException) as exc:
                await svc.delete_comment(999)
            assert exc.value.status_code == 404


# ===========================================================================
# Schema 测试
# ===========================================================================


class TestCommentSchema:

    def test_comment_create_valid(self):
        from app.schemas.comment import CommentCreate

        req = CommentCreate(knowledge_id=1, content="好文章")
        assert req.knowledge_id == 1
        assert req.content == "好文章"

    def test_comment_create_empty_content(self):
        from app.schemas.comment import CommentCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CommentCreate(knowledge_id=1, content="")

    def test_comment_create_content_too_long(self):
        from app.schemas.comment import CommentCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CommentCreate(knowledge_id=1, content="x" * 2001)
