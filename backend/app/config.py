"""应用配置：从环境变量读取，backend/.env 优先。

未配置 LLM_API_KEY 时自动降级为 fake 模式（确定性 Mock），保证零配置可跑通全流程。
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

SUPPORTED_LANGS = ("zh", "ja", "en")
DEFAULT_LANGS = ["zh", "ja", "en"]
LANG_LABEL = {"zh": "简体中文", "ja": "日本語", "en": "English"}


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


class Settings:
    """实时读环境变量，便于测试与运行期切换。"""

    @property
    def llm_api_key(self) -> str:
        return _env("LLM_API_KEY", "").strip()

    @property
    def llm_base_url(self) -> str:
        return _env("LLM_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")

    @property
    def llm_model(self) -> str:
        return _env("LLM_MODEL", "deepseek-chat")

    @property
    def llm_provider(self) -> str:
        """fake | openai。默认按是否有 API key 自动判定。"""
        explicit = _env("LLM_PROVIDER", "").strip().lower()
        if explicit:
            return explicit
        return "openai" if self.llm_api_key else "fake"

    @property
    def llm_temperature(self) -> float:
        return float(_env("LLM_TEMPERATURE", "0.2"))

    @property
    def llm_timeout_seconds(self) -> float:
        return float(_env("LLM_TIMEOUT_SECONDS", "120"))

    @property
    def llm_max_retries(self) -> int:
        return int(_env("LLM_MAX_RETRIES", "3"))

    @property
    def llm_max_tokens(self) -> int | None:
        """单次请求的输出上限；默认不发送，交给服务端默认值（三语 PRD 输出可能很长）。

        某些服务端默认值偏小，导致 JSON 被截断时，显式设置（如 LLM_MAX_TOKENS=8192）。
        """
        raw = _env("LLM_MAX_TOKENS", "").strip()
        return int(raw) if raw else None

    @property
    def backtranslate_chunk_chars(self) -> int:
        """回译请求的分片大小：越小越不容易触发模型输出截断/JSON 破损。"""
        return int(_env("BACKTRANSLATE_CHUNK_CHARS", "4000"))

    @property
    def max_validation_rounds(self) -> int:
        return max(1, int(_env("MAX_VALIDATION_ROUNDS", "3")))

    @property
    def max_input_chars(self) -> int:
        return int(_env("MAX_INPUT_CHARS", "4000"))

    @property
    def consistency_method(self) -> str:
        """structural（零成本确定性）| backtranslate（回译）| embeddings（语义向量）| off"""
        return _env("CONSISTENCY_METHOD", "structural").strip().lower()

    @property
    def consistency_min_score(self) -> float:
        """低于该分数记为 major（进评审清单）。"""
        return float(_env("CONSISTENCY_MIN_SCORE", "75"))

    @property
    def consistency_blocker_score(self) -> float:
        """低于该分数（或单条故事低于该分数）记为 blocker（触发下一轮修正）。"""
        return float(_env("CONSISTENCY_BLOCKER_SCORE", "50"))

    @property
    def embeddings_api_key(self) -> str:
        return _env("EMBEDDINGS_API_KEY", "").strip() or self.llm_api_key

    @property
    def embeddings_base_url(self) -> str:
        return _env("EMBEDDINGS_BASE_URL", "").strip() or self.llm_base_url

    @property
    def embeddings_model(self) -> str:
        return _env("EMBEDDINGS_MODEL", "text-embedding-3-small")

    @property
    def embeddings_provider(self) -> str:
        """fake | openai。默认按是否有 key 自动判定。"""
        explicit = _env("EMBEDDINGS_PROVIDER", "").strip().lower()
        if explicit:
            return explicit
        return "openai" if self.embeddings_api_key else "fake"

    @property
    def cors_origins(self) -> list[str]:
        raw = _env(
            "CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001",
        )
        return [o.strip() for o in raw.split(",") if o.strip()]


settings = Settings()
