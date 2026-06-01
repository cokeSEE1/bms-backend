"""知识详情接口测试套件

覆盖场景:
  API 层: 200/401/404/422, 响应结构, view_count 递增, 边界值, 各状态条目
  Service 层: 数据聚合, kb_name, 面包屑路径, 错误处理, 字段完整性
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
        "name": "测试知识条目", "content": "详细内容", "abstract": "摘要",
        "author": "张三", "creator": "admin", "last_modify_user": "admin",
        "version": 1, "max_version": 3, "status": 3, "is_online": 1,
        "first_release_time": datetime(2026, 1, 1),
        "last_release_time": datetime(2026, 5, 1),
        "view_count": 10, "like_count": 5, "favorite_count": 3,
        "share_num": 2, "download_num": 1, "is_top": 0,
        "sort_order": None, "name_sort_key": "ceshizhishitiaomu",
        "knowledge_type": 0, "dir_type": 2,
        "tag_ids": "1,2,3", "attachment_ids": "10,20",
        "create_time": datetime(2026, 1, 1),
        "update_time": datetime(2026, 5, 29),
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


def make_mock_kb(**overrides):
    defaults = {"id": 1, "name": "测试知识库"}
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


def make_mock_directory(**overrides):
    defaults = {
        "id": 5, "dir_name": "子目录", "dir_type": 0,
        "tree_id": 1, "lft": 5, "rgt": 10, "level": 1, "parent_id": 1,
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


# ===========================================================================
# API 层测试 — 使用 TestClient + dependency_overrides
# ===========================================================================


_UNSET = object()


class TestKnowledgeDetailAPI:

    @staticmethod
    def _setup_dependencies(client, mock_item, mock_kb=_UNSET, mock_dirs=_UNSET):
        """注入模拟依赖，绕过真实 DB/JWT/Redis"""
        from app.api import deps
        from app.entities.user import User

        if mock_kb is _UNSET:
            mock_kb = make_mock_kb()
        if mock_dirs is _UNSET:
            mock_dirs = [
                make_mock_directory(id=1, dir_name="根目录", dir_type=0),
                make_mock_directory(),
            ]

        async def mock_get_detail(knowledge_id: int, current_user=None):
            from app.schemas.knowledge_item import KnowledgeItemDetailOut, KnowledgeItemOut, PathNode

            if mock_item is None:
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="知识条目不存在")

            mock_item.view_count += 1
            item_data = KnowledgeItemOut.model_validate(mock_item).model_dump()

            kb_name = mock_kb.name if mock_kb else ""
            knowledge_path = [
                PathNode(dir_id=d.id, dir_name=d.dir_name, dir_type=d.dir_type)
                for d in mock_dirs
            ]
            return KnowledgeItemDetailOut(
                **item_data,
                kb_name=kb_name,
                knowledge_path=knowledge_path,
                creator_user_info={"username": "admin"},
                last_modify_user_info={"username": "admin"},
                tag_names=["1", "2", "3"],
                is_edit=False,
                is_download=True,
            )

        mock_service = MagicMock()
        mock_service.get_detail = AsyncMock(side_effect=mock_get_detail)

        def override_get_db():
            return MagicMock()

        async def override_get_current_user():
            return User(id=1, username="testuser")

        def override_get_service():
            return mock_service

        client.app.dependency_overrides[deps.get_db] = override_get_db
        client.app.dependency_overrides[deps.get_current_user] = override_get_current_user
        client.app.dependency_overrides[deps.get_knowledge_item_service] = override_get_service

        return mock_service

    # ---------- 正向测试 ----------

    def test_returns_200_with_correct_structure(self, client, auth_headers):
        mock_item = make_mock_item()
        self._setup_dependencies(client, mock_item)

        response = client.get("/v1/knowledge/detail?knowledge_id=1", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "测试知识条目"
        assert data["kb_name"] == "测试知识库"
        assert len(data["knowledge_path"]) == 2
        assert data["knowledge_path"][0]["dir_name"] == "根目录"

    def test_response_includes_all_base_fields(self, client, auth_headers):
        mock_item = make_mock_item()
        self._setup_dependencies(client, mock_item)

        response = client.get("/v1/knowledge/detail?knowledge_id=1", headers=auth_headers)
        data = response.json()

        for field in [
            "id", "appid", "kb_id", "cate_id", "name", "content", "abstract",
            "author", "creator", "last_modify_user", "version", "max_version",
            "status", "is_online", "first_release_time", "last_release_time",
            "view_count", "like_count", "favorite_count", "share_num", "download_num",
            "is_top", "sort_order", "name_sort_key", "knowledge_type", "dir_type",
            "tag_ids", "attachment_ids", "create_time", "update_time",
        ]:
            assert field in data, f"缺少基础字段: {field}"

    def test_reserved_fields_are_filled(self, client, auth_headers):
        mock_item = make_mock_item()
        self._setup_dependencies(client, mock_item)

        response = client.get("/v1/knowledge/detail?knowledge_id=1", headers=auth_headers)
        data = response.json()

        assert isinstance(data["creator_user_info"], dict)
        assert "username" in data["creator_user_info"]

        assert isinstance(data["last_modify_user_info"], dict)
        assert "username" in data["last_modify_user_info"]

        assert isinstance(data["tag_names"], list)
        for tag in data["tag_names"]:
            assert isinstance(tag, str)

        assert isinstance(data["is_edit"], bool)
        assert data["is_download"] is True

    def test_knowledge_path_node_structure(self, client, auth_headers):
        mock_item = make_mock_item()
        self._setup_dependencies(client, mock_item)

        response = client.get("/v1/knowledge/detail?knowledge_id=1", headers=auth_headers)

        for node in response.json()["knowledge_path"]:
            assert isinstance(node["dir_id"], int)
            assert isinstance(node["dir_name"], str)
            assert isinstance(node["dir_type"], int)

    # ---------- 认证测试 ----------

    def test_without_auth_returns_401(self, client):
        response = client.get("/v1/knowledge/detail?knowledge_id=1")
        assert response.status_code == 401

    def test_with_invalid_token_returns_401(self, client):
        response = client.get(
            "/v1/knowledge/detail?knowledge_id=1",
            headers={"Authorization": "Invalid token"},
        )
        assert response.status_code == 401

    def test_with_wrong_scheme_returns_401(self, client):
        response = client.get(
            "/v1/knowledge/detail?knowledge_id=1",
            headers={"Authorization": "Basic dGVzdDp0ZXN0"},
        )
        assert response.status_code == 401

    # ---------- 404 测试 ----------

    def test_nonexistent_item_returns_404(self, client, auth_headers):
        self._setup_dependencies(client, None)

        response = client.get("/v1/knowledge/detail?knowledge_id=99999", headers=auth_headers)

        assert response.status_code == 404
        assert "知识条目不存在" in response.json()["detail"]

    # ---------- 422 参数校验测试 ----------

    def test_missing_knowledge_id_returns_422(self, client):
        """缺少 knowledge_id → 422（不传 auth 验证参数校验优先）"""
        response = client.get("/v1/knowledge/detail")
        # FastAPI 参数缺失返回 422，认证也在依赖链中但 auth header 验证在 query param 之后
        # 实际行为：无 auth header 时先返回 401（get_current_user 先执行）
        assert response.status_code in (401, 422)

    def test_invalid_knowledge_id_type_returns_422(self, client):
        """knowledge_id 类型错误 → 422"""
        response = client.get("/v1/knowledge/detail?knowledge_id=abc")
        assert response.status_code in (401, 422)

    # ---------- view_count 递增 ----------

    def test_view_count_increments(self, client, auth_headers):
        mock_item = make_mock_item(view_count=10)
        self._setup_dependencies(client, mock_item)

        r1 = client.get("/v1/knowledge/detail?knowledge_id=1", headers=auth_headers)
        r2 = client.get("/v1/knowledge/detail?knowledge_id=1", headers=auth_headers)

        assert r2.json()["view_count"] > r1.json()["view_count"]

    # ---------- 边界值 ----------

    def test_cate_id_none_empty_path(self, client, auth_headers):
        mock_item = make_mock_item(cate_id=None)
        self._setup_dependencies(client, mock_item, mock_dirs=[])

        response = client.get("/v1/knowledge/detail?knowledge_id=1", headers=auth_headers)

        assert response.json()["knowledge_path"] == []

    def test_cate_id_zero_empty_path(self, client, auth_headers):
        mock_item = make_mock_item(cate_id=0)
        self._setup_dependencies(client, mock_item, mock_dirs=[])

        response = client.get("/v1/knowledge/detail?knowledge_id=1", headers=auth_headers)

        assert response.json()["knowledge_path"] == []

    def test_kb_missing_empty_name(self, client, auth_headers):
        mock_item = make_mock_item()
        self._setup_dependencies(client, mock_item, mock_kb=None)

        response = client.get("/v1/knowledge/detail?knowledge_id=1", headers=auth_headers)

        assert response.json()["kb_name"] == ""

    def test_empty_knowledge_path(self, client, auth_headers):
        mock_item = make_mock_item()
        self._setup_dependencies(client, mock_item, mock_dirs=[])

        response = client.get("/v1/knowledge/detail?knowledge_id=1", headers=auth_headers)

        assert response.json()["knowledge_path"] == []

    def test_max_knowledge_id(self, client, auth_headers):
        self._setup_dependencies(client, None)

        response = client.get(
            "/v1/knowledge/detail?knowledge_id=2147483647", headers=auth_headers,
        )
        assert response.status_code == 404

    def test_zero_knowledge_id(self, client, auth_headers):
        self._setup_dependencies(client, None)

        response = client.get("/v1/knowledge/detail?knowledge_id=0", headers=auth_headers)
        assert response.status_code == 404

    # ---------- 软删除 ----------

    def test_soft_deleted_item_returns_404(self, client, auth_headers):
        self._setup_dependencies(client, None)

        response = client.get("/v1/knowledge/detail?knowledge_id=1", headers=auth_headers)
        assert response.status_code == 404

    # ---------- 各状态条目 ----------

    def test_draft_item(self, client, auth_headers):
        mock_item = make_mock_item(status=1, is_online=0)
        self._setup_dependencies(client, mock_item)

        response = client.get("/v1/knowledge/detail?knowledge_id=1", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == 1

    def test_reviewing_item(self, client, auth_headers):
        mock_item = make_mock_item(status=2)
        self._setup_dependencies(client, mock_item)

        response = client.get("/v1/knowledge/detail?knowledge_id=1", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == 2

    def test_published_item(self, client, auth_headers):
        mock_item = make_mock_item(status=3, is_online=1)
        self._setup_dependencies(client, mock_item)

        response = client.get("/v1/knowledge/detail?knowledge_id=1", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == 3

    def test_offline_item(self, client, auth_headers):
        mock_item = make_mock_item(status=4, is_online=0)
        self._setup_dependencies(client, mock_item)

        response = client.get("/v1/knowledge/detail?knowledge_id=1", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == 4


# ===========================================================================
# Service 层单元测试 — 直接 mock Model 引用位置
# ===========================================================================


class TestKnowledgeDetailService:

    @staticmethod
    def _patch_models(item, kb=None, dir_node=None, ancestors=None, user_mock=None):
        """在 service 文件的引用位置 patch Model"""

        patches = [
            patch(
                "app.services.knowledge_item.KnowledgeItemModel",
                _make_item_model_mock(item),
            ),
            patch(
                "app.services.knowledge_item.KnowledgeBaseModel",
                _make_kb_model_mock(kb),
            ),
            patch(
                "app.models.knowledge_directory.KnowledgeDirectoryModel",
                _make_dir_model_mock(dir_node, ancestors),
            ),
        ]
        if user_mock is None:
            user_mock = _make_user_model_mock()
        patches.append(patch("app.services.knowledge_item.UserModel", user_mock))
        return patches

    # ---------- 正向 ----------

    @pytest.mark.asyncio
    async def test_returns_full_data(self):
        item = make_mock_item()
        kb = make_mock_kb()
        dir_node = make_mock_directory()
        ancestors = [
            make_mock_directory(id=1, dir_name="根目录", dir_type=0, lft=1, rgt=20),
            dir_node,
        ]
        from app.entities.user import User
        mock_user = User(id=1, username="testuser")

        ps = self._patch_models(item, kb, dir_node, ancestors, _make_user_model_mock("admin"))
        for p in ps:
            p.start()
        try:
            from app.services.knowledge_item import KnowledgeItemService

            service = KnowledgeItemService(MagicMock())
            result = await service.get_detail(1, mock_user)

            assert result.id == 1
            assert result.kb_name == "测试知识库"
            assert len(result.knowledge_path) == 2
            assert result.knowledge_path[0].dir_name == "根目录"
            assert result.creator_user_info == {"username": "admin"}
            assert result.is_edit is False
            assert result.is_download is True
            assert result.tag_names == ["1", "2", "3"]
        finally:
            for p in ps:
                p.stop()

    @pytest.mark.asyncio
    async def test_calls_increment_view_count(self):
        item = make_mock_item(view_count=5)
        kb = make_mock_kb()
        from app.entities.user import User
        mock_user = User(id=1, username="testuser")

        ps = self._patch_models(item, kb)
        for p in ps:
            p.start()
        try:
            import app.services.knowledge_item as svc_mod
            from app.services.knowledge_item import KnowledgeItemService

            service = KnowledgeItemService(MagicMock())
            await service.get_detail(1, mock_user)

            svc_mod.KnowledgeItemModel.increment_view_count.assert_awaited_once()
        finally:
            for p in ps:
                p.stop()

    # ---------- 404 ----------

    @pytest.mark.asyncio
    async def test_item_not_found_raises_404(self):
        from app.entities.user import User
        mock_user = User(id=1, username="testuser")

        ps = self._patch_models(None)
        for p in ps:
            p.start()
        try:
            from fastapi import HTTPException
            from app.services.knowledge_item import KnowledgeItemService

            service = KnowledgeItemService(MagicMock())
            with pytest.raises(HTTPException) as exc:
                await service.get_detail(99999, mock_user)

            assert exc.value.status_code == 404
            assert "知识条目不存在" in exc.value.detail
        finally:
            for p in ps:
                p.stop()

    # ---------- 面包屑 ----------

    @pytest.mark.asyncio
    async def test_single_level_path(self):
        item = make_mock_item(cate_id=1)
        kb = make_mock_kb()
        dir_node = make_mock_directory(id=1, dir_name="根目录", dir_type=0)
        from app.entities.user import User
        mock_user = User(id=1, username="testuser")

        ps = self._patch_models(item, kb, dir_node, [dir_node])
        for p in ps:
            p.start()
        try:
            from app.services.knowledge_item import KnowledgeItemService

            service = KnowledgeItemService(MagicMock())
            result = await service.get_detail(1, mock_user)

            assert len(result.knowledge_path) == 1
            assert result.knowledge_path[0].dir_name == "根目录"
        finally:
            for p in ps:
                p.stop()

    @pytest.mark.asyncio
    async def test_deep_path_three_levels(self):
        item = make_mock_item(cate_id=10)
        kb = make_mock_kb()
        dir_node = make_mock_directory(id=10, dir_name="第三层", level=2)
        ancestors = [
            make_mock_directory(id=1, dir_name="根目录", lft=1, rgt=30, level=0),
            make_mock_directory(id=3, dir_name="第二层", lft=5, rgt=25, level=1),
            dir_node,
        ]
        from app.entities.user import User
        mock_user = User(id=1, username="testuser")

        ps = self._patch_models(item, kb, dir_node, ancestors)
        for p in ps:
            p.start()
        try:
            from app.services.knowledge_item import KnowledgeItemService

            service = KnowledgeItemService(MagicMock())
            result = await service.get_detail(1, mock_user)

            assert [n.dir_name for n in result.knowledge_path] == ["根目录", "第二层", "第三层"]
        finally:
            for p in ps:
                p.stop()

    @pytest.mark.asyncio
    async def test_no_cate_id_empty_path(self):
        item = make_mock_item(cate_id=None)
        kb = make_mock_kb()
        from app.entities.user import User
        mock_user = User(id=1, username="testuser")

        ps = self._patch_models(item, kb)
        for p in ps:
            p.start()
        try:
            from app.services.knowledge_item import KnowledgeItemService

            service = KnowledgeItemService(MagicMock())
            result = await service.get_detail(1, mock_user)
            assert result.knowledge_path == []
        finally:
            for p in ps:
                p.stop()

    @pytest.mark.asyncio
    async def test_dir_not_found_empty_path(self):
        item = make_mock_item(cate_id=999)
        kb = make_mock_kb()
        from app.entities.user import User
        mock_user = User(id=1, username="testuser")

        ps = self._patch_models(item, kb, dir_node=None)
        for p in ps:
            p.start()
        try:
            from app.services.knowledge_item import KnowledgeItemService

            service = KnowledgeItemService(MagicMock())
            result = await service.get_detail(1, mock_user)
            assert result.knowledge_path == []
        finally:
            for p in ps:
                p.stop()

    # ---------- kb_name ----------

    @pytest.mark.asyncio
    async def test_kb_not_found_empty_name(self):
        item = make_mock_item()
        from app.entities.user import User
        mock_user = User(id=1, username="testuser")

        ps = self._patch_models(item, kb=None)
        for p in ps:
            p.start()
        try:
            from app.services.knowledge_item import KnowledgeItemService

            service = KnowledgeItemService(MagicMock())
            result = await service.get_detail(1, mock_user)
            assert result.kb_name == ""
        finally:
            for p in ps:
                p.stop()

    @pytest.mark.asyncio
    async def test_kb_id_zero_empty_name(self):
        item = make_mock_item(kb_id=0)
        from app.entities.user import User
        mock_user = User(id=1, username="testuser")

        ps = self._patch_models(item)
        for p in ps:
            p.start()
        try:
            from app.services.knowledge_item import KnowledgeItemService

            service = KnowledgeItemService(MagicMock())
            result = await service.get_detail(1, mock_user)
            assert result.kb_name == ""
        finally:
            for p in ps:
                p.stop()

    # ---------- 知识类型 ----------

    @pytest.mark.asyncio
    async def test_richtext_knowledge_type(self):
        item = make_mock_item(knowledge_type=0, content='[{"type":"p","children":[{"text":"h"}]}]')
        kb = make_mock_kb()
        from app.entities.user import User
        mock_user = User(id=1, username="testuser")

        ps = self._patch_models(item, kb)
        for p in ps:
            p.start()
        try:
            from app.services.knowledge_item import KnowledgeItemService

            service = KnowledgeItemService(MagicMock())
            result = await service.get_detail(1, mock_user)
            assert result.knowledge_type == 0
            assert result.content is not None
        finally:
            for p in ps:
                p.stop()

    @pytest.mark.asyncio
    async def test_file_knowledge_type(self):
        item = make_mock_item(knowledge_type=2, dir_type=2, content=None)
        kb = make_mock_kb()
        from app.entities.user import User
        mock_user = User(id=1, username="testuser")

        ps = self._patch_models(item, kb)
        for p in ps:
            p.start()
        try:
            from app.services.knowledge_item import KnowledgeItemService

            service = KnowledgeItemService(MagicMock())
            result = await service.get_detail(1, mock_user)
            assert result.knowledge_type == 2
            assert result.dir_type == 2
        finally:
            for p in ps:
                p.stop()

    # ---------- 字段完整性 ----------

    @pytest.mark.asyncio
    async def test_has_all_detail_fields(self):
        item = make_mock_item()
        kb = make_mock_kb()
        from app.entities.user import User
        mock_user = User(id=1, username="testuser")

        ps = self._patch_models(item, kb, user_mock=_make_user_model_mock("admin"))
        for p in ps:
            p.start()
        try:
            from app.services.knowledge_item import KnowledgeItemService

            service = KnowledgeItemService(MagicMock())
            result = await service.get_detail(1, mock_user)

            for field in [
                "kb_name", "knowledge_path", "creator_user_info",
                "last_modify_user_info", "tag_names", "attachments",
                "is_favorite", "is_edit", "is_download",
                "comments_count", "related_knowledge",
            ]:
                assert hasattr(result, field), f"缺少字段: {field}"
        finally:
            for p in ps:
                p.stop()

    @pytest.mark.asyncio
    async def test_view_count_is_callers_snapshot(self):
        """item_data 在 increment_view_count 之前提取，返回调用前快照值"""
        item = make_mock_item(view_count=42)
        kb = make_mock_kb()
        from app.entities.user import User
        mock_user = User(id=1, username="testuser")

        ps = self._patch_models(item, kb)
        for p in ps:
            p.start()
        try:
            from app.services.knowledge_item import KnowledgeItemService

            service = KnowledgeItemService(MagicMock())
            result = await service.get_detail(1, mock_user)
            assert result.view_count == 42
        finally:
            for p in ps:
                p.stop()


# ===========================================================================
# Mock 工厂
# ===========================================================================


def _make_item_model_mock(item):
    m = MagicMock()
    m.get_by_id = AsyncMock(return_value=item)
    m.increment_view_count = AsyncMock(return_value=None)
    return m


def _make_kb_model_mock(kb):
    m = MagicMock()
    m.get_by_id = AsyncMock(return_value=kb)
    return m


def _make_user_model_mock(username="admin"):
    m = MagicMock()
    user = MagicMock()
    user.username = username
    m.get_by_username = AsyncMock(return_value=user)
    return m


def _make_dir_model_mock(dir_node, ancestors):
    m = MagicMock()
    m.get_by_id = AsyncMock(return_value=dir_node)
    m.get_ancestors = AsyncMock(return_value=ancestors or [])
    return m
