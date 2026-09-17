"""Structurer Agent：将澄清后的需求映射为标准 PRD 模板（多语言）。"""

PRD_TEMPLATE = {
    "background": "背景",
    "goal": "目标",
    "user_stories": [],   # [{"id": "US-1", "story": str, "acceptance_criteria": [str]}]
    "functional_reqs": [],
    "nonfunctional_reqs": [],
    "acceptance_criteria": [],
    "risks": [],
    "open_questions": [],
}

STRUCTURER_SYSTEM_PROMPT = """你是资深产品经理。将澄清后的需求整理为标准 PRD：
- 用户故事遵循 "作为<角色>，我可以<动作>，以便<价值>" 句式
- 每条用户故事至少 1 条可测试的验收标准（AC）
- 输出 target_langs 指定的语种版本，附关键术语对照表
- 若收到 Validator 反馈（feedback），逐条修正后重新输出"""


class StructurerAgent:
    async def run(self, clarified, target_langs: list[str]) -> dict:
        # TODO(v0.2): 接入 LLM 生成多语言 PRD；当前返回模板骨架
        prd = {lang: dict(PRD_TEMPLATE) for lang in target_langs}
        prd["meta"] = {
            "source": clarified.original,
            "assumptions": clarified.assumptions,
            "validator_feedback_applied": clarified._feedback,
        }
        return prd
