from app.agents.clarifier import ClarifiedRequirement
from app.agents.structurer import PRD
from app.agents.validator import ValidatorAgent
from app.llm import FakeLLM
from app.render import render_all, render_markdown


def _prd() -> PRD:
    doc = {
        "lang": "zh",
        "title": "银发支付优化 PRD",
        "background": "高龄用户在支付页流失。",
        "goal": "让 65 岁以上用户顺利完成支付。",
        "user_stories": [
            {"id": "US-1", "story": "作为年长用户，我希望看清按钮，以便快速支付。", "acceptance_criteria": ["主按钮 >= 18pt", "步骤 <= 3"]}
        ],
        "functional_reqs": ["简化支付流程"],
        "nonfunctional_reqs": ["首屏 1.5s 内渲染"],
        "risks": ["本地支付未定"],
        "open_questions": ["是否支持 PayPay？"],
    }
    return PRD(
        product_name="银发支付优化",
        docs={"zh": doc},
        glossary=[{"term_zh": "验收标准", "term_en": "AC", "term_ja": "受入基準", "note": "可判定"}],
        target_langs=["zh"],
    )


def test_render_markdown_sections_and_glossary():
    md = render_markdown(_prd(), "zh")
    for expected in ["# 银发支付优化 PRD", "## 背景", "## 目标", "## 用户故事", "### US-1", "验收标准", "## 术语对照表", "| zh | en | ja | note |"]:
        assert expected in md


def test_render_includes_clarification_meta():
    clarified = ClarifiedRequirement(
        original="日本市场要一个对老年人友好的支付流程",
        success_metrics=["完成率 >= 90%"],
        assumptions=["不需要改后端协议"],
        feedback=["[major/testability] AC 无阈值"],
    )
    md = render_markdown(_prd(), "zh", clarified)
    assert "原始需求" in md and "完成率 >= 90%" in md and "不需要改后端协议" in md
    assert "本轮已修正的校验问题" in md


def test_render_all_covers_langs():
    prd = _prd()
    prd.docs["en"] = dict(prd.docs["zh"], lang="en", title="Senior Payment PRD")
    prd.target_langs = ["zh", "en"]
    rendered = render_all(prd)
    assert set(rendered) == {"zh", "en"}
    assert "Senior Payment PRD" in rendered["en"]


async def test_validator_blocks_structural_defect_even_if_llm_passes():
    prd = _prd()
    prd.docs["zh"]["user_stories"][0]["acceptance_criteria"] = []
    report = await ValidatorAgent(FakeLLM()).run(prd)
    assert report.passed is False
    assert report.structural_count >= 1


async def test_validator_passes_clean_prd():
    report = await ValidatorAgent(FakeLLM()).run(_prd())
    assert report.passed is True
    assert report.issues == []
