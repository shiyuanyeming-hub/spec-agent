"""Clarifier Agent：识别缺失信息，产出澄清问题与显式标注的假设。"""
from dataclasses import dataclass, field

from app.llm import LLMResult
from app.schemas import ClarificationRaw

CLARIFIER_SYSTEM_PROMPT = """你是资深需求分析师，服务跨国产品团队。输入是一段可能模糊、不完整的产品需求描述（任意语言）。
你的任务是把这段描述拆解成结构化要素：
1. goal：一句话说清要达成的业务目标
2. target_users：目标用户人群与使用场景
3. success_metrics：可量化的成功指标，必须给出具体指标名 + 阈值 + 测量口径（如"支付页放弃率从 38% 降到 25%，来源：埋点漏斗"）
   —— 严禁输出 "X%"、"待定"、"TBD" 这类占位符；确实无法给出数值时，把该指标改写进 open_questions
4. scope：范围边界，明确写出"不做什么"
5. assumptions：信息缺失时你基于行业常识补全的部分，逐条显式标注
6. open_questions：必须由需求方确认、不允许拍脑袋的问题（含上面无法量化的指标）

只输出 JSON，不要输出任何解释文字。字段名必须与给定 JSON Schema 完全一致：
{schema}"""


@dataclass
class ClarifiedRequirement:
    original: str
    goal: str = ""
    target_users: str = ""
    success_metrics: list[str] = field(default_factory=list)
    scope: str = ""
    assumptions: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    feedback: list[str] = field(default_factory=list)

    def attach_feedback(self, issues: list[dict]) -> None:
        """接收 Validator 回注的问题，下一轮结构化时逐条修正。"""
        self.feedback = [
            f"[{i.get('severity', 'minor')}/{i.get('category', 'other')}] {i.get('message', '')}"
            + (f" → 修改建议：{i['suggestion']}" if i.get("suggestion") else "")
            for i in issues
        ]

    def to_prompt_payload(self) -> str:
        lines = [
            f"原始需求：{self.original}",
            f"目标：{self.goal}",
            f"目标用户：{self.target_users}",
            f"成功指标：{'；'.join(self.success_metrics) or '（待补充）'}",
            f"范围：{self.scope}",
            f"已标注假设：{'；'.join(self.assumptions) or '（无）'}",
            f"待确认问题：{'；'.join(self.open_questions) or '（无）'}",
        ]
        if self.feedback:
            lines.append("上一轮校验未通过，请逐条修正：" + "；".join(self.feedback))
        return "\n".join(lines)


class ClarifierAgent:
    def __init__(self, llm=None):
        from app.llm import get_llm

        self.llm = llm or get_llm()

    async def run(self, raw_text: str) -> ClarifiedRequirement:
        prompt = CLARIFIER_SYSTEM_PROMPT.format(schema=ClarificationRaw.model_json_schema())
        result: LLMResult = await self.llm.chat_json(
            system=prompt, user=raw_text, schema=ClarificationRaw, extras={"raw_text": raw_text}
        )
        data = ClarificationRaw.model_validate(result.data)
        return ClarifiedRequirement(
            original=raw_text,
            goal=data.goal,
            target_users=data.target_users,
            success_metrics=data.success_metrics,
            scope=data.scope,
            assumptions=data.assumptions,
            open_questions=data.open_questions,
        )
