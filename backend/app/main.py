"""Spec Agent API 入口：接收模糊需求，返回结构化 PRD。"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.pipeline import run_pipeline

app = FastAPI(title="Spec Agent", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RequirementIn(BaseModel):
    raw_text: str = Field(..., min_length=10, description="任意语言的模糊需求描述")
    target_langs: list[str] = Field(default=["zh", "ja", "en"])


@app.post("/api/generate")
async def generate(req: RequirementIn):
    """运行 Clarifier → Structurer → Validator 流水线，返回结构化 PRD 与校验报告。"""
    result = await run_pipeline(req.raw_text, req.target_langs)
    return result


@app.get("/api/health")
async def health():
    return {"status": "ok"}
