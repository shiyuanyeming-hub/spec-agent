
from app.agents.structurer import PRD
from app.checks import has_blocking_issues, structural_issues


def _doc(lang: str, stories: int = 2, with_ac: bool = True) -> dict:
    return {
        "lang": lang,
        "title": f"PRD {lang}",
        "background": "背景说明",
        "goal": "目标说明",
        "user_stories": [
            {"id": f"US-{i}", "story": "作为用户我可以完成主流程，以便更快达成目标", "acceptance_criteria": ["步骤 <= 3 步"] if with_ac else []}
            for i in range(1, stories + 1)
        ],
        "functional_reqs": ["功能需求"],
        "nonfunctional_reqs": ["性能需求"],
        "risks": ["风险"],
        "open_questions": ["问题"],
    }


def _prd(docs: dict, glossary=None) -> PRD:
    return PRD(
        product_name="Demo",
        docs=docs,
        glossary=glossary if glossary is not None else [
            {"term_zh": "验收标准", "term_en": "AC", "term_ja": "受入基準", "note": ""}
        ],
        target_langs=list(docs.keys()),
    )


def test_clean_prd_has_no_blocking_issues():
    prd = _prd({"zh": _doc("zh"), "en": _doc("en")})
    issues = structural_issues(prd, ["zh", "en"])
    assert issues == []
    assert not has_blocking_issues(issues)


def test_missing_lang_is_blocker():
    prd = _prd({"zh": _doc("zh")})
    prd.target_langs = ["zh", "ja"]
    issues = structural_issues(prd, ["zh", "ja"])
    assert any(i["severity"] == "blocker" and "缺失" in i["message"] for i in issues)
    assert has_blocking_issues(issues)


def test_story_count_mismatch_is_blocker():
    prd = _prd({"zh": _doc("zh", stories=3), "ja": _doc("ja", stories=2)})
    issues = structural_issues(prd, ["zh", "ja"])
    assert any(i["category"] == "consistency" and i["severity"] == "blocker" for i in issues)


def test_story_id_mismatch_reported():
    zh = _doc("zh")
    ja = _doc("ja")
    ja["user_stories"][1]["id"] = "US-9"
    issues = structural_issues(_prd({"zh": zh, "ja": ja}), ["zh", "ja"])
    assert any(i["category"] == "consistency" and "编号" in i["message"] for i in issues)


def test_missing_acceptance_criteria_is_blocker():
    prd = _prd({"zh": _doc("zh", with_ac=False)})
    issues = structural_issues(prd, ["zh"])
    assert any(i["category"] == "testability" and i["severity"] == "blocker" for i in issues)


def test_empty_stories_and_fields():
    doc = _doc("zh")
    doc["user_stories"] = []
    doc["goal"] = ""
    issues = structural_issues(_prd({"zh": doc}), ["zh"])
    severities = {i["severity"] for i in issues}
    assert "blocker" in severities and "major" in severities


def test_missing_glossary_for_multilang_is_minor():
    prd = _prd({"zh": _doc("zh"), "en": _doc("en")}, glossary=[])
    issues = structural_issues(prd, ["zh", "en"])
    assert any(i["severity"] == "minor" and "术语" in i["message"] for i in issues)


def test_incomplete_glossary_entry():
    prd = _prd({"zh": _doc("zh"), "en": _doc("en")}, glossary=[{"term_zh": "下单", "term_en": "", "term_ja": "注文"}])
    issues = structural_issues(prd, ["zh", "en"])
    assert any("术语表第 1 条" in i["message"] for i in issues)
