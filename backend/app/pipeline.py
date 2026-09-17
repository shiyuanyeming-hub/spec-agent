"""三阶段流水线编排：Clarifier → Structurer → Validator。"""
import asyncio
from dataclasses import dataclass, field

from app.agents.clarifier import ClarifierAgent
from app.agents.structurer import StructurerAgent
from app.agents.validator import ValidatorAgent

MAX_ROUNDS = 3


@dataclass
class PipelineResult:
    prd: dict = field(default_factory=dict)
    clarifications: list[str] = field(default_factory=list)
    validation_report: dict = field(default_factory=dict)
    rounds_used: int = 0


async def run_pipeline(raw_text: str, target_langs: list[str]) -> PipelineResult:
    """跑完整流水线；Validator 不通过则回注 Structurer，最多 MAX_ROUNDS 轮。"""
    clarifier = ClarifierAgent()
    structurer = StructurerAgent()
    validator = ValidatorAgent()

    clarified = await clarifier.run(raw_text)
    result = PipelineResult(clarifications=clarified.open_questions)

    for round_no in range(1, MAX_ROUNDS + 1):
        result.rounds_used = round_no
        result.prd = await structurer.run(clarified, target_langs)
        report = await validator.run(result.prd)
        result.validation_report = report
        if report.passed:
            break
        clarified.attach_feedback(report.issues)  # 校验问题回注，下一轮修正
    return result


if __name__ == "__main__":  # 本地冒烟测试
    demo = "日本市场想要一个能让老年用户更容易用的支付流程，大概下个季度要。"
    print(asyncio.run(run_pipeline(demo, ["zh", "ja", "en"])))
