"""Validator Agent：按 INVEST 原则与可测试性检查 PRD 质量。"""
from dataclasses import dataclass, field


@dataclass
class ValidationReport:
    passed: bool
    issues: list[str] = field(default_factory=list)   # 不通过的具体问题
    suggestions: list[str] = field(default_factory=list)

VALIDATOR_SYSTEM_PROMPT = """你是 PRD 质量把关人。逐条检查：
1. 用户故事是否符合 INVEST（独立、可协商、有价值、可估算、小、可测试）
2. 每条验收标准是否可测试（能明确判定通过/不通过）
3. 风险项与 Open Questions 是否覆盖了假设中的不确定性
不通过则列出具体 issues（供 Structurer 修正），全部通过则 passed=true。"""


class ValidatorAgent:
    async def run(self, prd: dict) -> ValidationReport:
        # TODO(v0.2): 接入 LLM 评审；当前骨架：有用户故事即视为通过
        has_stories = any(
            prd.get(lang, {}).get("user_stories") for lang in prd if lang != "meta"
        )
        if has_stories:
            return ValidationReport(passed=True)
        return ValidationReport(
            passed=False,
            issues=["PRD 缺少用户故事，无法进入评审"],
            suggestions=["请先由 Structurer 生成至少 1 条用户故事"],
        )
