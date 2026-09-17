"""Spec Agent API 入口：接收模糊需求，返回多语种结构化 PRD。"""
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from sse_starlette.sse import EventSourceResponse

from app.config import SUPPORTED_LANGS, settings
from app.llm import LLMError
from app.pipeline import iter_pipeline, run_pipeline
from app.samples import SAMPLES

app = FastAPI(title="Spec Agent", version="0.3.0", description="模糊需求 → 中日英三语标准 PRD + 三语一致性评分")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    raw_text: str = Field(..., min_length=10, description="任意语言的模糊需求描述")
    target_langs: list[str] = Field(default=["zh", "ja", "en"], description="输出语种，支持 zh / ja / en")

    @field_validator("raw_text")
    @classmethod
    def _limit_length(cls, value: str) -> str:
        value = value.strip()
        if len(value) > settings.max_input_chars:
            raise ValueError(f"需求描述过长（上限 {settings.max_input_chars} 字符）")
        return value

    @field_validator("target_langs")
    @classmethod
    def _check_langs(cls, value: list[str]) -> list[str]:
        langs: list[str] = []
        for lang in value:
            normalized = lang.strip().lower()
            if normalized not in SUPPORTED_LANGS:
                raise ValueError(f"不支持的语种：{lang}（可选：{'/'.join(SUPPORTED_LANGS)}）")
            if normalized not in langs:
                langs.append(normalized)
        if not langs:
            raise ValueError("至少选择一个输出语种")
        return langs


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": app.version, "provider": settings.llm_provider}


@app.get("/api/meta")
async def meta():
    return {
        "provider": settings.llm_provider,
        "model": settings.llm_model if settings.llm_provider != "fake" else "fake-deterministic",
        "supported_langs": list(SUPPORTED_LANGS),
        "max_validation_rounds": settings.max_validation_rounds,
        "max_input_chars": settings.max_input_chars,
        "samples": SAMPLES,
    }


@app.post("/api/generate")
async def generate(req: GenerateRequest):
    """跑完整流水线，返回多语种 PRD、术语表、Markdown 与校验报告。"""
    try:
        result = await run_pipeline(req.raw_text, req.target_langs)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=f"LLM 调用失败：{exc}") from exc
    return result.to_api_dict()


@app.post("/api/generate/stream")
async def generate_stream(req: GenerateRequest):
    """SSE 流式输出：逐阶段推送进度事件，最后推送完整结果。"""

    async def event_source():
        try:
            async for kind, payload in iter_pipeline(req.raw_text, req.target_langs):
                if kind == "stage":
                    yield {"event": "stage", "data": json.dumps(payload, ensure_ascii=False)}
                else:
                    yield {"event": "result", "data": json.dumps(payload.to_api_dict(), ensure_ascii=False)}
        except LLMError as exc:
            yield {"event": "error", "data": json.dumps({"message": f"LLM 调用失败：{exc}"}, ensure_ascii=False)}
        except Exception as exc:  # 兜底：不让流悬挂
            yield {"event": "error", "data": json.dumps({"message": f"生成失败：{exc}"}, ensure_ascii=False)}

    return EventSourceResponse(event_source())
