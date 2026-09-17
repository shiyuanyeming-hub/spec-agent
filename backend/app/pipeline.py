"""流水线编排：Clarifier → Structurer → Validator（不通过则回注 Structurer，最多 N 轮）。

`iter_pipeline` 是唯一编排入口：同步接口与 SSE 流式接口消费同一份事件流。
"""
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from app.agents.clarifier import ClarifiedRequirement, ClarifierAgent
from app.agents.structurer import PRD, StructurerAgent
from app.agents.validator import ValidationReport, ValidatorAgent
from app.config import settings
from app.llm import FakeLLM, get_llm
from app.render import render_all

STAGE_LABEL = {"clarifier": "需求澄清", "structurer": "PRD 结构化", "validator": "质量校验", "done": "完成"}


@dataclass
class PipelineResult:
    prd: PRD
    clarifications: ClarifiedRequirement
    validation: ValidationReport
    markdown: dict[str, str] = field(default_factory=dict)
    rounds_used: int = 0
    stalled: bool = False
    provider: str = "fake"
    trace: list[dict] = field(default_factory=list)

    @property
    def status(self) -> str:
        return self.validation.status

    def to_api_dict(self) -> dict:
        return {
            "prd": self.prd.to_api_dict(),
            "glossary": self.prd.glossary,
            "markdown": self.markdown,
            "clarifications": {
                "original": self.clarifications.original,
                "goal": self.clarifications.goal,
                "target_users": self.clarifications.target_users,
                "success_metrics": self.clarifications.success_metrics,
                "scope": self.clarifications.scope,
                "assumptions": self.clarifications.assumptions,
                "open_questions": self.clarifications.open_questions,
            },
            "consistency": self.validation.consistency.to_dict() if self.validation.consistency else None,
            "validation": {
                "passed": self.validation.passed,
                "status": self.validation.status,
                "consistency_score": self.validation.consistency_score,
                "summary": self.validation.summary,
                "issues": self.validation.issues,
                "suggestions": self.validation.suggestions,
                "counts": {
                    "blocker": len(self.validation.blockers),
                    "major": len(self.validation.majors),
                    "minor": len(self.validation.minors),
                },
                "structural_issues": self.validation.structural_count,
            },
            "rounds_used": self.rounds_used,
            "status": self.validation.status,
            "stalled": self.stalled,
            "provider": self.provider,
            "trace": self.trace,
        }


def _provider_name(llm) -> str:
    if isinstance(llm, FakeLLM):
        return "fake"
    return settings.llm_provider


def _story_count(prd: PRD) -> int:
    first = prd.docs.get(prd.target_langs[0]) if prd.target_langs else None
    return len((first or {}).get("user_stories") or [])


async def iter_pipeline(
    raw_text: str,
    target_langs: list[str],
    llm=None,
    max_rounds: int | None = None,
) -> AsyncIterator[tuple[str, object]]:
    """产出 ("stage", {...}) 事件，最后产出 ("result", PipelineResult)。"""
    llm = llm or get_llm()
    rounds = max_rounds or settings.max_validation_rounds
    clarifier, structurer, validator = ClarifierAgent(llm), StructurerAgent(llm), ValidatorAgent(llm)
    trace: list[dict] = []

    def event(stage: str, status: str, round_no: int, detail: str = "", duration_ms: int = 0) -> dict:
        item = {
            "stage": stage,
            "label": STAGE_LABEL.get(stage, stage),
            "status": status,
            "round": round_no,
            "detail": detail,
            "duration_ms": duration_ms,
        }
        trace.append(item)
        return item

    started = time.perf_counter()
    clarified: ClarifiedRequirement = await clarifier.run(raw_text)
    yield ("stage", event(
        "clarifier", "ok", 0,
        f"目标：{clarified.goal}；待确认 {len(clarified.open_questions)} 项",
        int((time.perf_counter() - started) * 1000),
    ))

    prd: PRD | None = None
    report: ValidationReport | None = None
    stalled = False
    previous_score: int | None = None
    # 交付排序：先看有没有 blocker（blocked 的 PRD 不能直接交付），再看问题加权分
    best: tuple[tuple[int, int], PRD, ValidationReport] | None = None

    def rank(report: ValidationReport, score: int) -> tuple[int, int]:
        return (1 if report.blockers else 0, score)

    for round_no in range(1, rounds + 1):
        round_started = time.perf_counter()
        yield ("stage", event("structurer", "start", round_no))
        prd = await structurer.run(clarified, target_langs, feedback=clarified.feedback)
        yield ("stage", event(
            "structurer", "ok", round_no,
            f"{len(prd.target_langs)} 个语种 · {_story_count(prd)} 条用户故事",
            int((time.perf_counter() - round_started) * 1000),
        ))

        yield ("stage", event("validator", "start", round_no))
        report = await validator.run(prd, round_no=round_no)
        score = 3 * len(report.blockers) + len(report.majors)
        detail = report.summary or f"{len(report.issues)} 条问题"
        if report.consistency_score is not None:
            detail = f"{detail} · 三语一致性 {report.consistency_score:.0f} 分（{report.consistency.method}）"
        yield ("stage", event(
            "validator", report.status, round_no,
            detail,
            int((time.perf_counter() - round_started) * 1000),
        ))
        if best is None or rank(report, score) < best[0]:
            best = (rank(report, score), prd, report)
        if score == 0:  # 无 blocker 也无 major：收敛，直接交付
            break
        if not report.blockers and round_no >= 2:
            # 已迭代过一次且没有 blocker：剩下的 major 进评审清单即可，
            # 再迭代多半只是措辞抖动（还会引入新的抖动），不值得烧 token。
            break
        if previous_score is not None and score >= previous_score:
            # 问题数没有下降：继续迭代只是在烧 token，停下来把剩余问题交给人工
            stalled = True
            break
        previous_score = score
        clarified.attach_feedback(report.blockers + report.majors[:5])

    assert prd is not None and report is not None
    if best is not None and best[0] < rank(report, 3 * len(report.blockers) + len(report.majors)):
        # 后续轮次可能变差（模型抖动）：交付排序最优的那一轮
        _, prd, report = best
    result = PipelineResult(
        prd=prd,
        clarifications=clarified,
        validation=report,
        markdown=render_all(prd, clarified),
        rounds_used=len([e for e in trace if e["stage"] == "validator" and e["status"] in ("passed", "needs_review", "blocked")]),
        stalled=stalled,
        provider=_provider_name(llm),
        trace=trace,
    )
    yield ("stage", event("done", report.status, result.rounds_used, result.validation.summary))
    yield ("result", result)


async def run_pipeline(
    raw_text: str,
    target_langs: list[str] | None = None,
    llm=None,
    max_rounds: int | None = None,
) -> PipelineResult:
    langs = target_langs or ["zh", "ja", "en"]
    result: PipelineResult | None = None
    async for kind, payload in iter_pipeline(raw_text, langs, llm=llm, max_rounds=max_rounds):
        if kind == "result":
            result = payload  # type: ignore[assignment]
    assert result is not None
    return result


if __name__ == "__main__":  # 本地冒烟：python -m app.pipeline
    import asyncio

    demo = "日本市场想要一个能让老年用户更容易用的支付流程，大概下个季度要。"
    outcome = asyncio.run(run_pipeline(demo))
    print(outcome.markdown["zh"])
    print(f"\n通过：{outcome.validation.passed} · 轮次：{outcome.rounds_used} · 模式：{outcome.provider}")
