"""Validator Agent：INVEST / 可测试性 / 三语一致性三重把关。

判定语义（避免"永远打回"的评审抖动）：
- blocker：会让 PRD 无法进入开发的缺陷（缺语种、缺用户故事、缺验收标准、语种之间内容冲突）→ 触发下一轮修正
- major / minor：不影响放行，但会作为评审清单交给需求方，在开发前确认
因此 `passed` 只由 blocker 决定，major 以「待办清单」形式随 PRD 一起交付。
"""
import json
from dataclasses import dataclass, field

from app.checks import structural_issues
from app.config import settings
from app.consistency import ConsistencyReport, consistency_issues, evaluate_consistency
from app.llm import LLMResult
from app.schemas import ValidationRaw

VALIDATOR_SYSTEM_PROMPT = """你是跨国产品团队的 PRD 质量把关人。逐条检查（按给定 JSON Schema 输出）：
1. invest：用户故事是否符合 INVEST（独立、可协商、有价值、可估算、足够小、可测试）
2. testability：验收标准是否能明确判定通过/不通过（有无阈值、有无歧义）
3. consistency：各语种版本是否语义等价——同一编号的故事、同样的验收标准数量与含义、术语与范围一致、没有某个语种凭空多出或漏掉需求
4. completeness：风险项与待确认问题是否覆盖了输入中的假设与不确定性

严重程度定义（务必克制，避免评审抖动）：
- blocker：不修就不能开发的缺陷。仅限：缺少某个语种的整份 PRD、没有用户故事、用户故事没有验收标准、各语种故事数量/编号矛盾、某语种凭空多出或漏掉需求
- major：影响开发理解或验收判定，但 PRD 仍可进入评审。例如：验收标准缺少可判定阈值、故事过大、指标是占位符（X%/待定）、关键假设未标注
- minor：表述、覆盖度、可读性方面的改进建议
- 拿不准的一律归为 major，不要报 blocker

要求：
- 每条问题给出 severity、category、message、suggestion（给 Structurer 的具体修改指令）
- passed=true 的条件是「不存在 blocker」；存在 major 也允许 passed=true（major 会作为评审清单交付）
- 同一问题在多个语种重复出现时只报一次，并在 message 中列明语种
- 不要臆造 PRD 里没有的内容；只针对实际给出的文本评审
只输出 JSON，不要输出任何解释文字。字段名必须与给定 JSON Schema 完全一致：
{schema}"""

SEVERITY_ORDER = {"blocker": 0, "major": 1, "minor": 2}


@dataclass
class ValidationReport:
    passed: bool
    issues: list[dict] = field(default_factory=list)
    summary: str = ""
    structural_count: int = 0
    suggestions: list[str] = field(default_factory=list)
    consistency: ConsistencyReport | None = None

    @property
    def consistency_score(self) -> float | None:
        return round(self.consistency.overall, 1) if self.consistency else None

    def _by(self, severity: str) -> list[dict]:
        return [i for i in self.issues if i.get("severity") == severity]

    @property
    def blockers(self) -> list[dict]:
        return self._by("blocker")

    @property
    def majors(self) -> list[dict]:
        return self._by("major")

    @property
    def minors(self) -> list[dict]:
        return self._by("minor")

    @property
    def status(self) -> str:
        if self.blockers:
            return "blocked"
        if self.majors or self.minors:
            return "needs_review"
        return "passed"

    def sorted_issues(self) -> list[dict]:
        return sorted(self.issues, key=lambda i: SEVERITY_ORDER.get(i.get("severity", "minor"), 3))

    def finalize(self) -> "ValidationReport":
        self.issues = self.sorted_issues()
        self.suggestions = [i["suggestion"] for i in self.issues if i.get("suggestion")]
        return self


class ValidatorAgent:
    def __init__(self, llm=None):
        from app.llm import get_llm

        self.llm = llm or get_llm()

    async def run(self, prd, round_no: int = 1) -> ValidationReport:
        structural = structural_issues(prd, getattr(prd, "target_langs", None))

        llm_issues: list[dict] = []
        summary = ""
        try:
            payload = json.dumps(prd.to_api_dict(), ensure_ascii=False)
            result: LLMResult = await self.llm.chat_json(
                system=VALIDATOR_SYSTEM_PROMPT.format(schema=ValidationRaw.model_json_schema()),
                user=payload,
                schema=ValidationRaw,
                extras={"prd": prd.to_api_dict(), "round": round_no, "target_langs": prd.target_langs},
            )
            data = ValidationRaw.model_validate(result.data)
            llm_issues = [i.model_dump() for i in data.issues]
            summary = data.summary
        except Exception as exc:  # LLM 评审失败不阻塞确定性结构校验结果
            summary = f"LLM 评审失败（{exc}），本轮仅采信确定性结构校验。"

        issues = structural + llm_issues

        # 三语一致性量化评分（structural / backtranslate / embeddings，可用 off 关闭）
        consistency: ConsistencyReport | None = None
        if settings.consistency_method != "off" and len(getattr(prd, "target_langs", []) or []) > 1:
            consistency = await evaluate_consistency(prd, llm=self.llm)
            issues = issues + consistency_issues(consistency)
            if not summary:
                summary = f"三语一致性 {consistency.overall:.0f} 分。"

        blockers = [i for i in issues if i.get("severity") == "blocker"]
        if not summary:
            summary = "确定性结构校验通过。" if not structural else "确定性结构校验发现问题，详见 issues。"
        return ValidationReport(
            passed=not blockers,
            issues=issues,
            summary=summary,
            structural_count=len(structural),
            consistency=consistency,
        ).finalize()
