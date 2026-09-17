"""Clarifier Agent：识别缺失信息，产出澄清问题与显式标注的假设。"""
from dataclasses import dataclass, field


@dataclass
class ClarifiedRequirement:
    original: str
    goal: str = ""
    target_users: str = ""
    success_metrics: list[str] = field(default_factory=list)
    scope: str = ""
    assumptions: list[str] = field(default_factory=list)   # 显式标注的假设
    open_questions: list[str] = field(default_factory=list)  # 需人工确认的问题
    _feedback: list[str] = field(default_factory=list)

    def attach_feedback(self, issues: list[str]) -> None:
        """接收 Validator 回注的问题，下一轮结构化时修正。"""
        self._feedback = issues


CLARIFIER_SYSTEM_PROMPT = """你是需求澄清专家。输入是一段可能模糊、不完整的产品需求描述（任意语言）。
你的任务：
1. 提取：目标（goal）、目标用户（target_users）、成功指标（success_metrics）、范围（scope）
2. 信息缺失时：能基于行业常识合理补全的 → 补全并写入 assumptions（显式标注"假设"）；
   必须由需求方确认的 → 写入 open_questions
输出 JSON，字段与 ClarifiedRequirement 对应。"""


class ClarifierAgent:
    async def run(self, raw_text: str) -> ClarifiedRequirement:
        # TODO(v0.2): 接入 LLM（OpenAI 兼容接口），解析 JSON 输出
        # 当前为骨架实现：直接构造结构，便于跑通流水线与前端联调
        return ClarifiedRequirement(
            original=raw_text,
            goal="(待 LLM 填充)",
            open_questions=["目标用户具体是哪个人群？", "成功指标是什么？"],
        )
