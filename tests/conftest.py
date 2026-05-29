import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    """创建不带 lifespan 的 TestClient（避免启动时连 DB/Redis/ES）"""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """模拟已认证的请求头（bypass JWT 验证）"""
    return {"Authorization": "Bearer test-token"}
