"""Pydantic schema 单元测试

覆盖 KnowledgeItemDetailOut 中 is_edit/is_download 默认值和安全类型约束。
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.knowledge_item import KnowledgeItemDetailOut


_BASE_KWARGS = {
    "id": 1,
    "appid": 0,
    "kb_id": 1,
    "cate_id": 5,
    "name": "测试知识",
    "content": "内容",
    "abstract": "摘要",
    "author": "作者",
    "creator": "admin",
    "last_modify_user": None,
    "version": 1,
    "max_version": 3,
    "status": 3,
    "is_online": 1,
    "first_release_time": None,
    "last_release_time": None,
    "view_count": 10,
    "like_count": 5,
    "favorite_count": 3,
    "share_num": 2,
    "download_num": 1,
    "is_top": 0,
    "sort_order": None,
    "name_sort_key": None,
    "knowledge_type": 0,
    "dir_type": 2,
    "tag_ids": None,
    "attachment_ids": None,
    "create_time": datetime(2026, 1, 1),
    "update_time": datetime(2026, 5, 29),
}


def _make(**overrides) -> KnowledgeItemDetailOut:
    kwargs = {**_BASE_KWARGS, **overrides}
    return KnowledgeItemDetailOut(**kwargs)


class TestKnowledgeItemDetailOutDefaults:
    """验证 is_edit / is_download 默认值为 False，不接收 None"""

    def test_is_edit_defaults_to_false(self):
        obj = _make()
        assert obj.is_edit is False

    def test_is_edit_accepts_true(self):
        obj = _make(is_edit=True)
        assert obj.is_edit is True

    def test_is_edit_accepts_false(self):
        obj = _make(is_edit=False)
        assert obj.is_edit is False

    def test_is_edit_rejects_none(self):
        with pytest.raises(ValidationError):
            _make(is_edit=None)

    def test_is_download_defaults_to_false(self):
        obj = _make()
        assert obj.is_download is False

    def test_is_download_accepts_true(self):
        obj = _make(is_download=True)
        assert obj.is_download is True

    def test_is_download_accepts_false(self):
        obj = _make(is_download=False)
        assert obj.is_download is False

    def test_is_download_rejects_none(self):
        with pytest.raises(ValidationError):
            _make(is_download=None)

    def test_optional_fields_still_accept_none(self):
        """确保 is_edit/is_download 改成 bool 后，不影响其他可空字段"""
        obj = _make(is_favorite=None, comments_count=None, related_knowledge=None)
        assert obj.is_favorite is None
        assert obj.comments_count is None
        assert obj.related_knowledge is None

    def test_minimal_construction(self):
        """确认只传必填字段 + 依赖新默认值的场景"""
        obj = _make()
        assert obj.is_edit is False
        assert obj.is_download is False
        assert obj.name == "测试知识"

    def test_pydantic_coerces_truthy_string_to_bool(self):
        """Pydantic v2 将 'true' 字符串强制转换为 True（不是 bug，是行为记录）"""
        obj = _make(is_edit="true")  # type: ignore[arg-type]
        assert obj.is_edit is True

    def test_pydantic_coerces_int_to_bool(self):
        """Pydantic v2 将非零 int 强制转换为 True"""
        obj = _make(is_download=1)  # type: ignore[arg-type]
        assert obj.is_download is True
