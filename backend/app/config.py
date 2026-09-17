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
    def max_validation_rounds(self) -> int:
        return max(1, int(_env("MAX_VALIDATION_ROUNDS", "3")))

    @property
    def max_input_chars(self) -> int:
        return int(_env("MAX_INPUT_CHARS", "4000"))

    @property
    def cors_origins(self) -> list[str]:
        raw = _env(
            "CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001",
        )
        return [o.strip() for o in raw.split(",") if o.strip()]


settings = Settings()
