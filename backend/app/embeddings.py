"""Embeddings 客户端：OpenAI 兼容 /embeddings + 离线确定性伪嵌入。

仅在 CONSISTENCY_METHOD=embeddings 时使用：跨语言直接比较语义向量，无需回译。
"""
import httpx

from app.config import settings
from app.similarity import hashed_embedding


class EmbeddingsError(RuntimeError):
    """Embeddings 调用失败。"""


class FakeEmbeddings:
    """离线确定性伪嵌入：字符 n-gram 哈希，跨进程稳定，供 Mock 模式与单测使用。"""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [hashed_embedding(text) for text in texts]


class OpenAICompatEmbeddings:
    """任何暴露 /embeddings 的 OpenAI 兼容服务。"""

    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None):
        self.api_key = api_key if api_key is not None else settings.embeddings_api_key
        self.base_url = (base_url or settings.embeddings_base_url).rstrip("/")
        self.model = model or settings.embeddings_model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key:
            raise EmbeddingsError("缺少 EMBEDDINGS_API_KEY（或 LLM_API_KEY），无法调用 embeddings 接口")
        payload = {"model": self.model, "input": texts}
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            resp = await client.post(f"{self.base_url}/embeddings", json=payload, headers=headers)
        if resp.status_code >= 400:
            raise EmbeddingsError(f"embeddings 接口返回 {resp.status_code}: {resp.text[:200]}")
        body = resp.json()
        try:
            rows = sorted(body["data"], key=lambda item: item.get("index", 0))
            return [row["embedding"] for row in rows]
        except (KeyError, TypeError) as exc:
            raise EmbeddingsError(f"embeddings 返回结构异常：{exc}") from exc


def get_embeddings():
    provider = settings.embeddings_provider
    if provider == "fake" or not settings.embeddings_api_key:
        return FakeEmbeddings()
    return OpenAICompatEmbeddings()
