"""LLM 结构化输出的 Pydantic Schema（同时用于校验与 JSON Schema 提示词）。"""
from typing import Literal

from pydantic import BaseModel, Field

Lang = Literal["zh", "ja", "en"]


class ClarificationRaw(BaseModel):
    """Clarifier 输出：把模糊需求拆成结构化要素。"""

    goal: str = Field(description="一句话说清要达成的业务目标")
    target_users: str = Field(description="目标用户是谁（人群/场景）")
    success_metrics: list[str] = Field(default_factory=list, description="可量化的成功指标")
    scope: str = Field(default="", description="范围边界：做什么、不做什么")
    assumptions: list[str] = Field(default_factory=list, description="为补全信息而显式标注的假设")
    open_questions: list[str] = Field(default_factory=list, description="必须由需求方确认的问题")


class StoryDraft(BaseModel):
    id: str = Field(description="用户故事编号，如 US-1，同一故事在各语种必须同号")
    story: str = Field(description="作为<角色>，我可以<动作>，以便<价值>")
    acceptance_criteria: list[str] = Field(
        default_factory=list, description="可测试的验收标准，逐条可判定通过/不通过"
    )


class LangDoc(BaseModel):
    """单个语种的 PRD 正文。"""

    lang: Lang
    title: str
    background: str
    goal: str
    user_stories: list[StoryDraft] = Field(default_factory=list)
    functional_reqs: list[str] = Field(default_factory=list)
    nonfunctional_reqs: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class GlossaryEntry(BaseModel):
    """术语对照表条目：保证多语种团队说的是同一件事。"""

    term_zh: str
    term_en: str
    term_ja: str
    note: str = Field(default="", description="术语在本项目中的确切含义")


class PRDRaw(BaseModel):
    product_name: str
    glossary: list[GlossaryEntry] = Field(default_factory=list)
    docs: list[LangDoc] = Field(default_factory=list, description="target_langs 每语种一份")


class ValidationIssue(BaseModel):
    severity: Literal["blocker", "major", "minor"]
    category: Literal["invest", "testability", "consistency", "completeness", "other"]
    message: str
    suggestion: str = Field(default="", description="给 Structurer 的具体修改指令")


class ValidationRaw(BaseModel):
    passed: bool = Field(description="无 blocker/major 问题时为 true")
    summary: str = Field(default="", description="一句话结论")
    issues: list[ValidationIssue] = Field(default_factory=list)


class BackTranslatedStory(BaseModel):
    id: str = Field(description="必须与源语种完全一致的故事编号")
    story: str
    acceptance_criteria: list[str] = Field(default_factory=list)


class BackTranslatedDoc(BaseModel):
    """某语种 PRD 回译到基准语言后的结果（用于一致性比对）。"""

    lang: Lang = Field(description="被回译的源语种")
    title: str = ""
    background: str = ""
    goal: str = ""
    user_stories: list[BackTranslatedStory] = Field(default_factory=list)


class BackTranslationRaw(BaseModel):
    docs: list[BackTranslatedDoc] = Field(default_factory=list, description="每个待回译语种一条")
