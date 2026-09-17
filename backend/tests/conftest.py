import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture(autouse=True)
def _fake_llm_env(monkeypatch):
    """所有测试默认走确定性 fake 模式，不发真实网络请求。"""
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.delenv("LLM_API_KEY", raising=False)


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


DEMO = "日本市场想要一个能让老年用户更容易用的支付流程，大概下个季度要上线。"


@pytest.fixture
def demo_text() -> str:
    return DEMO
