"""Structurer Agent：把澄清后的需求映射为标准 PRD 模板（多语言 + 术语对照）。"""
from dataclasses import dataclass, field

from app.config import LANG_LABEL
from app.llm import LLMResult
from app.schemas import PRDRaw

STRUCTURER_SYSTEM_PROMPT = """你是跨国产品团队的资深产品经理。把澄清后的需求整理成标准 PRD，并按指定语种各输出一份。
硬性要求：
1. 每个语种的 user_stories 数量与编号必须完全一致（US-1、US-2…），编号在全部语种中代表同一条故事
2. 每条用户故事使用「作为<角色>，我可以<动作>，以便<价值>」句式，并用该语种表达
3. 每条用户故事至少 1 条可测试的验收标准（含可判定的阈值或条件）
4. 多语种不是逐字翻译，而是本地化表达；同一术语在各语种中必须一致，并写入 glossary 对照表
5. 必须输出 target_langs 里列出的每一个语种，lang 字段只能取 zh / ja / en
6. 用户确认问题写进各语种的 open_questions；未确认的假设在 risks 或 open_questions 中体现
7. 严禁占位符：不写 "X%"、"TBD"、"待定"、"具体数值待定"；无法给出数值的指标写进 open_questions 并说明测量口径
8. 用户故事控制在 3~6 条，聚焦首期可交付范围；其余想法写进 open_questions 或 risks（避免输出过长导致 JSON 被截断）
8. 若给出「上一轮校验未通过」，请逐条修正后重新输出完整 PRD（不要只输出差异）

只输出 JSON，不要输出任何解释文字。字段名必须与给定 JSON Schema 完全一致：
{schema}"""


@dataclass
class PRD:
    product_name: str
    docs: dict[str, dict] = field(default_factory=dict)
    glossary: list[dict] = field(default_factory=list)
    target_langs: list[str] = field(default_factory=list)
    feedback_applied: list[str] = field(default_factory=list)

    def to_api_dict(self) -> dict:
        return {
            "product_name": self.product_name,
            "target_langs": self.target_langs,
            "glossary": self.glossary,
            "docs": self.docs,
        }


class StructurerAgent:
    def __init__(self, llm=None):
        from app.llm import get_llm

        self.llm = llm or get_llm()

    async def run(self, clarified, target_langs: list[str], feedback: list[str] | None = None) -> PRD:
        feedback = feedback if feedback is not None else getattr(clarified, "feedback", [])
        user = "\n".join(
            [
                clarified.to_prompt_payload(),
                f"需要输出的语种：{', '.join(LANG_LABEL.get(code, code) for code in target_langs)}"
                f"（lang 字段分别用 {', '.join(target_langs)}）",
            ]
        )
        result: LLMResult = await self.llm.chat_json(
            system=STRUCTURER_SYSTEM_PROMPT.format(schema=PRDRaw.model_json_schema()),
            user=user,
            schema=PRDRaw,
            extras={"raw_text": clarified.original, "target_langs": target_langs, "feedback": feedback},
        )
        raw = PRDRaw.model_validate(result.data)

        docs: dict[str, dict] = {}
        for doc in raw.docs:
            if doc.lang in target_langs and doc.lang not in docs:
                docs[doc.lang] = doc.model_dump()
        missing = [lang for lang in target_langs if lang not in docs]
        if missing:
            # 兜底：模型漏语种时保留结构存在（由 Validator 以 blocker 报出）
            for lang in missing:
                docs[lang] = {
                    "lang": lang,
                    "title": raw.product_name,
                    "background": "",
                    "goal": "",
                    "user_stories": [],
                    "functional_reqs": [],
                    "nonfunctional_reqs": [],
                    "risks": [],
                    "open_questions": [],
                }

        return PRD(
            product_name=raw.product_name,
            docs={lang: docs[lang] for lang in target_langs},
            glossary=[g.model_dump() for g in raw.glossary],
            target_langs=list(target_langs),
            feedback_applied=list(feedback),
        )
