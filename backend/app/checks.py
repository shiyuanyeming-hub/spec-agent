"""确定性结构校验：不依赖 LLM 即可发现的多语种/结构缺陷。

LLM 评审负责 INVEST、可测试性语义、三语语义等价等主观判断；
本模块负责"机器一眼可判定"的部分（缺语种、故事数量不一致、验收标准缺失…），
两者相加构成 Validator 的判定结果。
"""
from collections.abc import Iterable

SEVERITY_RANK = {"blocker": 3, "major": 2, "minor": 1}


def _issue(severity: str, category: str, message: str, suggestion: str = "") -> dict:
    return {"severity": severity, "category": category, "message": message, "suggestion": suggestion}


def _story_ids(doc: dict) -> list[str]:
    return [str(s.get("id") or f"#{i + 1}") for i, s in enumerate(doc.get("user_stories") or [])]


def structural_issues(prd, target_langs: Iterable[str] | None = None) -> list[dict]:
    langs = list(target_langs or getattr(prd, "target_langs", None) or list(getattr(prd, "docs", {}).keys()))
    docs = getattr(prd, "docs", {}) or {}
    issues: list[dict] = []

    for lang in langs:
        doc = docs.get(lang)
        if not doc:
            issues.append(
                _issue("blocker", "completeness", f"[{lang}] 缺失该语种的 PRD", "请补齐该语种完整 PRD（不得只输出部分语种）")
            )
            continue
        for field_name, label in (("title", "标题"), ("background", "背景"), ("goal", "目标")):
            if not str(doc.get(field_name) or "").strip():
                issues.append(
                    _issue("major", "completeness", f"[{lang}] {label}为空", f"补充{label}内容，需与其它语种语义一致")
                )
        stories = doc.get("user_stories") or []
        if not stories:
            issues.append(_issue("blocker", "completeness", f"[{lang}] 没有任何用户故事", "至少产出 1 条带验收标准的用户故事"))
        for index, story in enumerate(stories, start=1):
            sid = str(story.get("id") or f"#{index}")
            text = str(story.get("story") or "").strip()
            acs = [str(a).strip() for a in (story.get("acceptance_criteria") or [])]
            if len(text) < 8:
                issues.append(_issue("major", "invest", f"[{lang}] {sid} 故事描述过短", "按「作为/我可以/以便」补全故事描述"))
            if not acs:
                issues.append(
                    _issue("blocker", "testability", f"[{lang}] {sid} 没有验收标准", "为每条故事补至少 1 条可判定的验收标准")
                )
            for ac in acs:
                if len(ac) < 6:
                    issues.append(
                        _issue("minor", "testability", f"[{lang}] {sid} 的验收标准过短：{ac!r}", "把验收标准写成可判定通过/不通过的条件")
                    )

    if len(langs) > 1:
        id_sets = {lang: set(_story_ids(docs.get(lang) or {})) for lang in langs if docs.get(lang)}
        counts = {lang: len(_story_ids(docs.get(lang) or {})) for lang in langs if docs.get(lang)}
        if len(set(counts.values())) > 1:
            detail = "、".join(f"{lang}={counts[lang]}" for lang in counts)
            issues.append(
                _issue(
                    "blocker",
                    "consistency",
                    f"各语种用户故事数量不一致（{detail}）",
                    "以条目最全的语种为基准补齐其余语种，保持故事编号一一对应",
                )
            )
        if len(id_sets) > 1:
            union = set().union(*id_sets.values())
            for lang, ids in id_sets.items():
                if ids and ids != union:
                    issues.append(
                        _issue(
                            "major",
                            "consistency",
                            f"[{lang}] 用户故事编号与其它语种不对应：{sorted(ids)} vs {sorted(union)}",
                            "各语种使用完全相同的故事编号集合",
                        )
                    )
        if not (getattr(prd, "glossary", None) or []):
            issues.append(
                _issue("minor", "consistency", "多语种输出缺少术语对照表", "补充关键术语的 zh/ja/en 对照表")
            )
        else:
            for index, entry in enumerate(prd.glossary, start=1):
                missing = [k for k in ("term_zh", "term_en", "term_ja") if not str(entry.get(k) or "").strip()]
                if missing:
                    issues.append(
                        _issue("minor", "consistency", f"术语表第 {index} 条缺少字段：{', '.join(missing)}", "补齐三语术语")
                    )
    return issues


def has_blocking_issues(issues: Iterable[dict]) -> bool:
    return any(i.get("severity") in ("blocker", "major") for i in issues)
