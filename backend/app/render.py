"""PRD → Markdown 渲染：让人能直接复制进文档/Issue，而不只是看 JSON。"""

LABELS = {
    "zh": {
        "goal": "目标", "users": "目标用户", "metrics": "成功指标", "scope": "范围",
        "background": "背景", "stories": "用户故事", "functional": "功能需求",
        "nonfunctional": "非功能需求", "risks": "风险", "questions": "待确认问题",
        "glossary": "术语对照表", "assumptions": "显式假设", "ac": "验收标准",
        "source": "原始需求", "feedback": "本轮已修正的校验问题",
    },
    "ja": {
        "goal": "目的", "users": "対象ユーザー", "metrics": "成功指標", "scope": "スコープ",
        "background": "背景", "stories": "ユーザーストーリー", "functional": "機能要件",
        "nonfunctional": "非機能要件", "risks": "リスク", "questions": "確認待ち事項",
        "glossary": "用語対訳表", "assumptions": "明示した前提", "ac": "受入基準",
        "source": "元の要望", "feedback": "今回反映した指摘",
    },
    "en": {
        "goal": "Goal", "users": "Target Users", "metrics": "Success Metrics", "scope": "Scope",
        "background": "Background", "stories": "User Stories", "functional": "Functional Requirements",
        "nonfunctional": "Non-Functional Requirements", "risks": "Risks", "questions": "Open Questions",
        "glossary": "Glossary", "assumptions": "Stated Assumptions", "ac": "Acceptance Criteria",
        "source": "Source Requirement", "feedback": "Validation issues fixed in this round",
    },
}


def _labels(lang: str) -> dict:
    return LABELS.get(lang, LABELS["en"])


def _bullets(items, empty: str = "—") -> str:
    items = [str(i).strip() for i in (items or []) if str(i).strip()]
    if not items:
        return f"- {empty}"
    return "\n".join(f"- {i}" for i in items)


def _numbered(items, empty: str = "—") -> str:
    items = [str(i).strip() for i in (items or []) if str(i).strip()]
    if not items:
        return f"1. {empty}"
    return "\n".join(f"{n}. {i}" for n, i in enumerate(items, start=1))


def render_markdown(prd, lang: str, clarified: object | None = None) -> str:
    labels = _labels(lang)
    doc = (getattr(prd, "docs", {}) or {}).get(lang) or {}
    out: list[str] = [f"# {doc.get('title') or getattr(prd, 'product_name', 'PRD')}", ""]

    if clarified is not None:
        out += [
            f"> **{labels['source']}**：{getattr(clarified, 'original', '')}",
            "",
        ]

    out += [f"## {labels['background']}", doc.get("background") or "—", "", f"## {labels['goal']}", doc.get("goal") or "—", ""]

    if clarified is not None:
        if getattr(clarified, "success_metrics", None):
            out += [f"## {labels['metrics']}", _bullets(clarified.success_metrics), ""]
        if getattr(clarified, "assumptions", None):
            out += [f"## {labels['assumptions']}", _bullets(clarified.assumptions), ""]

    out += [f"## {labels['stories']}", ""]
    stories = doc.get("user_stories") or []
    if not stories:
        out += ["—", ""]
    for story in stories:
        acs = story.get("acceptance_criteria") or []
        out += [f"### {story.get('id', 'US-?')} · {story.get('story', '')}", ""]
        out += [f"- {labels['ac']}：{ac}" for ac in acs] or [f"- {labels['ac']}：—"]
        out += [""]

    out += [f"## {labels['functional']}", _bullets(doc.get("functional_reqs")), ""]
    out += [f"## {labels['nonfunctional']}", _bullets(doc.get("nonfunctional_reqs")), ""]
    out += [f"## {labels['risks']}", _bullets(doc.get("risks")), ""]
    out += [f"## {labels['questions']}", _numbered(doc.get("open_questions")), ""]

    glossary = getattr(prd, "glossary", None) or []
    if glossary:
        out += [f"## {labels['glossary']}", "", "| zh | en | ja | note |", "| --- | --- | --- | --- |"]
        for entry in glossary:
            cells = [
                str(entry.get("term_zh", "")), str(entry.get("term_en", "")),
                str(entry.get("term_ja", "")), str(entry.get("note", "")),
            ]
            out.append("| " + " | ".join(c.replace("|", "/") for c in cells) + " |")
        out.append("")

    if clarified is not None and getattr(clarified, "feedback", None):
        out += [f"<!-- {labels['feedback']}: " + "；".join(clarified.feedback) + " -->", ""]

    return "\n".join(out).strip() + "\n"


def render_all(prd, clarified: object | None = None) -> dict[str, str]:
    return {lang: render_markdown(prd, lang, clarified) for lang in getattr(prd, "target_langs", []) or []}
