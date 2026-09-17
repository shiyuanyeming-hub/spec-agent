"""三语一致性量化评分：把"三个语种说的是不是同一件事"变成一个可解释的分数。

三种方法（CONSISTENCY_METHOD）：
- structural（默认，零额外成本）：只用确定性信号
  · 故事编号覆盖、每故事 AC 数量对齐
  · 数字阈值一致性（18pt / 3 步 / 4.5:1 这类阈值跨语种必须对得上）
  · 技术词保留率（WCAG 2.1 / AA / TTS / PayPay 这类词不应在某语种里消失）
- backtranslate：在 structural 之上，用一次 LLM 调用把所有非基准语种回译到基准语言，比较词面重合
- embeddings：在 structural 之上，用跨语言向量相似度替代回译（需要 /embeddings 接口）

评分只用于"排风险、给人工复核排序"，不是语义等价的证明：词面重合度对同义改写是宽容的，
因此编号 / AC 数量 / 数字 / 技术词这些硬信号权重更高，回译或向量只占 20%。
"""
import json
import re
from dataclasses import dataclass, field

from app.config import LANG_LABEL, settings
from app.llm import LLMResult
from app.schemas import BackTranslationRaw
from app.similarity import cosine_vectors, matches_language, mean, numbers, numbers_similarity, similarity

ENTITY_RE = re.compile(r"[A-Za-z][A-Za-z0-9.+_/-]*")

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "must", "should", "will", "from", "into", "than",
    "user", "users", "when", "then", "each", "over", "under", "about", "after", "before", "which",
}

# 权重：硬信号（编号 / 数字阈值 / AC 数量 / 技术词）合计 80%，语义信号（回译或向量）占 20%。
# 缺失的维度会被重新归一化，因此 structural 模式与 backtranslate 模式的分数是可比的。
WEIGHTS = {"ids": 0.25, "ac": 0.15, "numeric": 0.25, "entity": 0.15, "semantic": 0.20}

# 回译/向量相似度的校准曲线：原始相似度在这个区间内线性映射到 0~1，区间外截断。
# 校准依据（真实模型 deepseek-chat，见 docs/HANDOVER.md）：
#   忠实回译的原始 Dice 落在 0.50 ~ 0.75（样本：0.498/0.517/0.531/0.533/0.57/0.605/0.669/0.678/0.713/0.745）
#   因此把 0.50 以上一律视为"忠实"，0.30 以下视为"说的不是另一件事"（触发硬否决）。
# 语义只是软信号：数字阈值、AC 数量、技术词这些硬信号才是精确判据。
SEMANTIC_FLOOR = 0.30
SEMANTIC_CEIL = 0.50

# 语义硬否决：回译/向量与基准语种几乎没有重合时，不论结构多整齐都判为严重漂移
SEMANTIC_VETO = 0.30
VETO_SCORE = 40.0

# 数字阈值冲突（同一条 AC 对齐后数字完全对不上，如 18pt vs 24pt）：压到建议线以下送人工复核，
# 但不直接触发额外迭代——数字可能只是表述差异（iOS 16 vs iOS 17）。
NUMERIC_CONFLICT_SCORE = 55.0

BACKTRANSLATE_SYSTEM_PROMPT = """你是专业本地化回译员。输入是某语种 PRD 的字段内容与目标基准语言。
任务：把内容**逐字段回译**成基准语言（{pivot_label}），用于跨语种一致性比对。
硬性要求：
1. 保留 story 的 id 原样，不要改动编号
2. 忠实回译：不要润色、不要补充、不要删减、不要合并或拆分用户故事与验收标准
3. 如果原文含糊或缺少信息，就照原样含糊地回译，不要替它补全
4. lang 字段填**被回译的源语种**代码（{source_langs}）
只输出 JSON，不要输出任何解释文字。字段名必须与给定 JSON Schema 完全一致：
{schema}"""


@dataclass
class StoryComparison:
    story_id: str
    score: float
    components: dict = field(default_factory=dict)
    pivot_text: str = ""
    back_text: str = ""
    veto: bool = False
    raw_semantic: float | None = None
    numeric_conflicts: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "story_id": self.story_id,
            "score": round(self.score, 1),
            "components": {k: round(v, 3) for k, v in self.components.items() if v is not None},
            "raw_semantic": None if self.raw_semantic is None else round(self.raw_semantic, 3),
            "veto": self.veto,
            "numeric_conflicts": self.numeric_conflicts,
            "pivot_text": self.pivot_text,
            "back_text": self.back_text,
        }


@dataclass
class PairReport:
    lang: str
    pivot: str
    score: float
    components: dict = field(default_factory=dict)
    stories: list[StoryComparison] = field(default_factory=list)
    missing_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "lang": self.lang,
            "pivot": self.pivot,
            "label": LANG_LABEL.get(self.lang, self.lang),
            "score": round(self.score, 1),
            "components": {k: round(v, 3) for k, v in self.components.items() if v is not None},
            "stories": [s.to_dict() for s in self.stories],
            "missing_ids": self.missing_ids,
        }


@dataclass
class ConsistencyReport:
    method: str
    pivot: str
    overall: float
    terminology_coverage: float = 1.0
    pairs: list[PairReport] = field(default_factory=list)
    divergences: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def worst_stories(self) -> list[StoryComparison]:
        stories = [s for pair in self.pairs for s in pair.stories]
        return sorted(stories, key=lambda s: s.score)

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "pivot": self.pivot,
            "pivot_label": LANG_LABEL.get(self.pivot, self.pivot),
            "overall": round(self.overall, 1),
            "terminology_coverage": round(self.terminology_coverage, 3),
            "pairs": [p.to_dict() for p in self.pairs],
            "divergences": self.divergences,
            "notes": self.notes,
            "thresholds": {
                "min_score": settings.consistency_min_score,
                "blocker_score": settings.consistency_blocker_score,
            },
        }


# ---------- 基础工具 ----------

def _story_ids(doc: dict) -> list[str]:
    return [str(story.get("id") or f"#{index + 1}") for index, story in enumerate(doc.get("user_stories") or [])]


def _doc_corpus(doc: dict) -> str:
    parts = [str(doc.get(k) or "") for k in ("title", "background", "goal")]
    parts += [str(x) for x in (doc.get("functional_reqs") or [])]
    parts += [str(x) for x in (doc.get("nonfunctional_reqs") or [])]
    parts += [str(x) for x in (doc.get("risks") or [])]
    return " ".join(parts)


def _story_corpus(story: dict) -> str:
    return " ".join([str(story.get("story") or "")] + [str(ac) for ac in (story.get("acceptance_criteria") or [])])


def entity_tokens(text: str) -> set[str]:
    """技术词/缩写（WCAG、2.1、AA、TTS、PayPay…）：本地化时不应被翻译掉。"""
    tokens = set()
    for raw in ENTITY_RE.findall(text or ""):
        token = raw.strip("._-/")
        if len(token) < 2:
            continue
        if token.isupper() or re.search(r"\d", token) or (len(token) >= 4 and token.lower() not in STOPWORDS):
            tokens.add(token.lower())
    return tokens


def _entity_retention(pivot_text: str, other_text: str) -> float:
    pivot_tokens = entity_tokens(pivot_text)
    if not pivot_tokens:
        return 1.0
    return len(pivot_tokens & entity_tokens(other_text)) / len(pivot_tokens)


def _weighted(components: dict) -> float:
    available = {k: v for k, v in components.items() if v is not None and k in WEIGHTS}
    total_weight = sum(WEIGHTS[k] for k in available)
    if not total_weight:
        return 0.0
    return sum(WEIGHTS[k] * available[k] for k in available) / total_weight


def align_acceptance_criteria(pivot_acs: list[str], acs: list[str]) -> list[tuple[str, str, float]]:
    """把基准语种的每条 AC 对齐到对方语种最相似的一条 AC。"""
    if not pivot_acs:
        return []
    if not acs:
        return [(ac, "", 0.0) for ac in pivot_acs]
    aligned: list[tuple[str, str, float]] = []
    for ac in pivot_acs:
        best = max(acs, key=lambda candidate: similarity(ac, candidate))
        aligned.append((ac, best, similarity(ac, best)))
    return aligned


def numeric_alignment(aligned: list[tuple[str, str, float]]) -> tuple[float, list[dict]]:
    """对齐后的 AC 逐条比数字：返回 (数字一致度, 冲突列表)。"""
    scores: list[float] = []
    conflicts: list[dict] = []
    for pivot_ac, other_ac, _sim in aligned:
        pivot_numbers = numbers(pivot_ac)
        other_numbers = numbers(other_ac)
        if not pivot_numbers or not other_numbers:
            continue
        score = numbers_similarity(pivot_ac, other_ac)
        scores.append(score)
        if score == 0.0:
            conflicts.append({"pivot_ac": pivot_ac[:120], "other_ac": other_ac[:120]})
    return (mean(scores) if scores else 1.0), conflicts


def calibrate_semantic(raw: float) -> float:
    """把原始相似度映射到 [0,1] 的语义分：低于 FLOOR 视为不相干，高于 CEIL 视为忠实。"""
    if raw <= SEMANTIC_FLOOR:
        return 0.0
    if raw >= SEMANTIC_CEIL:
        return 1.0
    return (raw - SEMANTIC_FLOOR) / (SEMANTIC_CEIL - SEMANTIC_FLOOR)


def _pair_stories(pivot_doc: dict, doc: dict) -> tuple[dict, dict]:
    pivot_stories = {str(s.get("id") or f"#{i + 1}"): s for i, s in enumerate(pivot_doc.get("user_stories") or [])}
    stories = {str(s.get("id") or f"#{i + 1}"): s for i, s in enumerate(doc.get("user_stories") or [])}
    return pivot_stories, stories


# ---------- 三语一致性评分 ----------

def split_doc_chunks(doc: dict, max_chars: int) -> list[dict]:
    """按体积把一份 PRD 拆成若干分片：头部字段留在第一片，用户故事分批。

    真实模型的输出长度有限：8 条故事 × 3 条 AC 的 PRD 一次性回译容易被截断成非法 JSON，
    分片后每次请求都很小，也天然带上"失败就二分再试"的容错空间。
    """
    stories = list(doc.get("user_stories") or [])
    header = {key: value for key, value in doc.items() if key != "user_stories"}
    if not stories:
        return [dict(doc, user_stories=[])]

    chunks: list[dict] = []
    current: list[dict] = []
    for story in stories:
        candidate = current + [story]
        size = len(json.dumps(candidate, ensure_ascii=False))
        if current and size > max_chars:
            chunks.append(current)
            current = [story]
        else:
            current = candidate
    if current:
        chunks.append(current)

    parts: list[dict] = []
    for index, batch in enumerate(chunks):
        part = dict(header, user_stories=batch) if index == 0 else {"lang": doc.get("lang"), "user_stories": batch}
        parts.append(part)
    return parts


async def _backtranslate_chunk(
    llm, chunk: dict, pivot: str, lang: str, prompt: str, pivot_doc: dict
) -> tuple[dict | None, str | None]:
    payload = {"pivot_lang": pivot, "pivot_label": LANG_LABEL.get(pivot, pivot), "docs": [chunk]}
    try:
        result: LLMResult = await llm.chat_json(
            system=prompt,
            user=json.dumps(payload, ensure_ascii=False),
            schema=BackTranslationRaw,
            extras={
                "pivot": pivot,
                "pivot_doc": pivot_doc,
                "chunk_doc": chunk,
                "source_langs": [lang],
                "target_langs": [pivot, lang],
            },
        )
        data = BackTranslationRaw.model_validate(result.data)
        for doc in data.docs:
            if doc.lang == lang:
                return doc.model_dump(), None
        return None, f"回译结果缺少语种 {lang}"
    except Exception as exc:
        return None, str(exc)


async def _backtranslate_part(
    llm, part: dict, pivot: str, lang: str, prompt: str, pivot_doc: dict, depth: int = 0
) -> tuple[dict | None, str | None]:
    """回译一个分片；失败时二分重试（最多 2 层），把"长输出破损"降级成"多次短输出"。"""
    doc, failure = await _backtranslate_chunk(llm, part, pivot, lang, prompt, pivot_doc)
    if doc is not None or depth >= 2:
        return doc, failure
    stories = list(part.get("user_stories") or [])
    if len(stories) <= 1:
        return None, failure
    middle = len(stories) // 2
    head = dict(part, user_stories=stories[:middle])
    tail = {"lang": lang, "user_stories": stories[middle:]}
    merged: dict = {}
    for sub in (head, tail):
        sub_doc, sub_failure = await _backtranslate_part(llm, sub, pivot, lang, prompt, pivot_doc, depth + 1)
        if sub_doc is None:
            return None, sub_failure
        if not merged:
            merged = sub_doc
        else:
            merged = dict(merged, user_stories=list(merged.get("user_stories") or []) + list(sub_doc.get("user_stories") or []))
    return merged, None


async def backtranslate(prd, llm, pivot: str, targets: list[str]) -> tuple[dict, str | None]:
    """把非基准语种的 PRD 分片回译到基准语言；局部失败只丢该分片，并给出说明。"""
    sources = [lang for lang in targets if lang != pivot and prd.docs.get(lang)]
    if not sources:
        return {}, None

    prompt = BACKTRANSLATE_SYSTEM_PROMPT.format(
        pivot_label=LANG_LABEL.get(pivot, pivot),
        source_langs="/".join(sources),
        schema=BackTranslationRaw.model_json_schema(),
    )
    merged: dict[str, dict] = {}
    failures: list[str] = []
    pivot_doc = prd.docs.get(pivot) or {}

    for lang in sources:
        doc = prd.docs.get(lang) or {}
        parts = split_doc_chunks(doc, settings.backtranslate_chunk_chars)
        combined: dict = {}
        for index, part in enumerate(parts):
            translated, failure = await _backtranslate_part(llm, part, pivot, lang, prompt, pivot_doc)
            if translated is None:
                failures.append(f"{lang} 第 {index + 1}/{len(parts)} 片回译失败：{failure}")
                continue
            if not combined:
                combined = translated
            else:
                combined = dict(combined, user_stories=list(combined.get("user_stories") or []) + list(translated.get("user_stories") or []))
        if combined:
            merged[lang] = combined

    # 回译结果必须真的落在基准语言里：模型偶尔会把原文抄回来（或返回英文），
    # 那样算出来的"语义不重合"是假阳性，宁可丢弃这个语种的语义信号。
    for lang in list(merged):
        doc = merged[lang]
        text = " ".join(
            [str(doc.get("title") or ""), str(doc.get("background") or ""), str(doc.get("goal") or "")]
            + [_story_corpus(story) for story in (doc.get("user_stories") or [])]
        )
        if not matches_language(text, pivot):
            merged.pop(lang)
            failures.append(f"{lang} 回译结果不是{LANG_LABEL.get(pivot, pivot)}（疑似未真正翻译），已忽略其语义信号")

    note = None
    if failures:
        note = "部分回译不可用（" + "；".join(failures[:2]) + "），一致性评分对该语种退化为确定性信号。"
    return merged, note


async def _embedding_scores(prd, pivot: str, targets: list[str], embeddings) -> tuple[dict, str | None]:
    """用跨语言向量相似度替代回译；返回 {lang: {story_id: score}}。"""
    try:
        pivot_doc = prd.docs.get(pivot) or {}
        scores: dict[str, dict[str, float]] = {}
        for lang in targets:
            if lang == pivot:
                continue
            doc = prd.docs.get(lang) or {}
            pivot_stories, stories = _pair_stories(pivot_doc, doc)
            shared = [sid for sid in pivot_stories if sid in stories]
            if not shared:
                continue
            texts = [_story_corpus(pivot_stories[sid]) for sid in shared]
            texts += [_story_corpus(stories[sid]) for sid in shared]
            vectors = await embeddings.embed(texts)
            half = len(shared)
            scores[lang] = {
                sid: cosine_vectors(vectors[index], vectors[half + index]) for index, sid in enumerate(shared)
            }
        return scores, None
    except Exception as exc:
        return {}, f"向量相似度计算失败（{exc}），一致性评分退化为确定性信号。"


def _terminology_coverage(prd) -> tuple[float, list[str]]:
    """术语表里的每个词，是否真的出现在对应语种的正文里。"""
    glossary = getattr(prd, "glossary", None) or []
    langs = [lang for lang in getattr(prd, "target_langs", []) or []]
    if not glossary or not langs:
        return 1.0, []
    misses: list[str] = []
    checks = 0
    hits = 0
    for entry in glossary:
        for lang in langs:
            term = str(entry.get(f"term_{lang}") or "").strip()
            if not term:
                continue
            checks += 1
            corpus = json.dumps(prd.docs.get(lang, {}), ensure_ascii=False).lower()
            if term.lower() in corpus:
                hits += 1
            else:
                misses.append(f"{term}（{lang}）")
    if checks == 0:
        return 1.0, []
    return hits / checks, misses


async def evaluate_consistency(prd, llm=None, embeddings=None) -> ConsistencyReport:
    """计算三语一致性报告（method 由配置决定；调用方负责判断是否跳过）。"""
    from app.llm import get_llm

    method = settings.consistency_method
    targets = [lang for lang in (getattr(prd, "target_langs", None) or list(prd.docs)) if prd.docs.get(lang)]
    pivot = targets[0] if targets else "zh"
    notes: list[str] = []
    coverage, terminology_misses = _terminology_coverage(prd)

    if len(targets) < 2:
        if terminology_misses:
            notes.append("术语表未在正文中出现的条目：" + "、".join(terminology_misses[:5]))
        return ConsistencyReport(
            method=method,
            pivot=pivot,
            overall=round(100.0 * coverage, 1),
            terminology_coverage=coverage,
            pairs=[],
            divergences=[],
            notes=notes + ["单语种输出：未做跨语言一致性校验。"],
        )

    back_docs: dict = {}
    embedding_story_scores: dict = {}
    if method == "backtranslate":
        llm = llm or get_llm()
        back_docs, failure = await backtranslate(prd, llm, pivot, targets)
        if failure:
            notes.append(failure)
        elif not back_docs:
            notes.append("回译未返回内容，一致性评分退化为确定性信号。")
    elif method == "embeddings":
        if embeddings is None:
            from app.embeddings import get_embeddings

            embeddings = get_embeddings()
        embedding_story_scores, failure = await _embedding_scores(prd, pivot, targets, embeddings)
        if failure:
            notes.append(failure)

    pivot_doc = prd.docs.get(pivot, {})
    pairs: list[PairReport] = []
    divergences: list[dict] = []

    for lang in targets:
        if lang == pivot:
            continue
        doc = prd.docs.get(lang) or {}
        pivot_stories, stories = _pair_stories(pivot_doc, doc)
        shared = [sid for sid in pivot_stories if sid in stories]
        missing = sorted(set(pivot_stories) - set(stories)) + sorted(set(stories) - set(pivot_stories))
        back_doc = back_docs.get(lang) or {}
        back_stories = {
            str(s.get("id") or f"#{i + 1}"): s for i, s in enumerate(back_doc.get("user_stories") or [])
        }

        id_union = set(pivot_stories) | set(stories)
        ids_component = len(set(pivot_stories) & set(stories)) / len(id_union) if id_union else 0.0
        ac_values = []
        numeric_values = []
        entity_values = []
        story_reports: list[StoryComparison] = []

        for sid in shared:
            pivot_story, story = pivot_stories[sid], stories[sid]
            pivot_acs = [str(ac) for ac in (pivot_story.get("acceptance_criteria") or [])]
            acs = [str(ac) for ac in (story.get("acceptance_criteria") or [])]
            ac_score = 1.0
            if pivot_acs or acs:
                ac_score = min(len(pivot_acs), len(acs)) / max(len(pivot_acs), len(acs), 1)
            aligned_acs = align_acceptance_criteria(pivot_acs, acs)
            numeric_score, numeric_conflicts = numeric_alignment(aligned_acs)
            entity_score = _entity_retention(_story_corpus(pivot_story), _story_corpus(story))
            semantic_score = None
            raw_semantic = None
            back_text = ""
            if back_stories.get(sid):
                back_story = back_stories[sid]
                back_text = _story_corpus(back_story)
                raw_semantic = similarity(_story_corpus(pivot_story), back_text)
            elif sid in (embedding_story_scores.get(lang) or {}):
                raw_semantic = embedding_story_scores[lang][sid]
            if raw_semantic is not None:
                semantic_score = calibrate_semantic(raw_semantic)

            components = {"ac": ac_score, "numeric": numeric_score, "entity": entity_score, "semantic": semantic_score}
            story_score = 100.0 * _weighted(components)
            veto = raw_semantic is not None and raw_semantic < SEMANTIC_VETO
            if veto:  # 语义硬否决：结构与数字都对，但两语种说的不是同一件事
                story_score = min(story_score, VETO_SCORE)
            if numeric_conflicts:  # 阈值冲突：同一条 AC 的数字对不上（18pt vs 24pt）
                story_score = min(story_score, NUMERIC_CONFLICT_SCORE)
            ac_values.append(ac_score)
            numeric_values.append(numeric_score)
            entity_values.append(entity_score)
            story_reports.append(
                StoryComparison(
                    story_id=sid,
                    score=story_score,
                    components={k: v for k, v in components.items() if v is not None},
                    pivot_text=_story_corpus(pivot_story)[:160],
                    back_text=back_text[:160],
                    veto=veto,
                    raw_semantic=raw_semantic,
                    numeric_conflicts=numeric_conflicts,
                )
            )

        semantic_available = bool(back_stories) or bool(embedding_story_scores.get(lang))
        doc_level_entity = _entity_retention(_doc_corpus(pivot_doc), _doc_corpus(doc))
        pair_components = {
            "ids": ids_component,
            "ac": mean(ac_values) if ac_values else None,
            "numeric": mean(numeric_values) if numeric_values else None,
            "entity": mean([doc_level_entity, *entity_values]),
            "semantic": mean([s.components.get("semantic", 0.0) for s in story_reports]) if semantic_available else None,
        }
        pair_score = 100.0 * _weighted(pair_components)
        pairs.append(
            PairReport(
                lang=lang,
                pivot=pivot,
                score=pair_score,
                components=pair_components,
                stories=story_reports,
                missing_ids=missing,
            )
        )

        threshold = settings.consistency_min_score
        for story in story_reports:
            if story.score < threshold:
                if story.veto:
                    reason = "回译后与基准语种几乎无重合，疑似说的是另一件事"
                elif story.numeric_conflicts:
                    conflict = story.numeric_conflicts[0]
                    reason = (
                        "同一条验收标准的数字阈值不一致（例："
                        f"{conflict['pivot_ac']} vs {conflict['other_ac']}）"
                    )
                else:
                    reason = "编号/阈值/AC 数量/词面重合度偏低，两语种可能已经不一致"
                divergences.append(
                    {
                        "lang": lang,
                        "label": LANG_LABEL.get(lang, lang),
                        "story_id": story.story_id,
                        "score": round(story.score, 1),
                        "reason": reason,
                        "pivot_text": story.pivot_text,
                        "back_text": story.back_text,
                        "numeric_conflicts": story.numeric_conflicts[:3],
                    }
                )
        if missing:
            divergences.append(
                {
                    "lang": lang,
                    "label": LANG_LABEL.get(lang, lang),
                    "story_id": "—",
                    "score": round(100.0 * ids_component, 1),
                    "reason": "故事编号未一一对应",
                    "pivot_text": "、".join(sorted(pivot_stories)),
                    "back_text": "、".join(sorted(stories)),
                }
            )

    divergences.sort(key=lambda item: item["score"])
    pair_mean = mean([pair.score for pair in pairs])
    if (getattr(prd, "glossary", None) or []) and pairs:
        overall = 0.85 * pair_mean + 0.15 * 100.0 * coverage
    else:
        overall = pair_mean if pairs else 100.0 * coverage
    if terminology_misses:
        notes.append("术语表未在正文中出现的条目：" + "、".join(terminology_misses[:5]))
    if method == "structural":
        notes.append("当前为 structural 模式：未做回译/向量语义比对（可用 CONSISTENCY_METHOD=backtranslate|embeddings 打开）。")

    return ConsistencyReport(
        method=method,
        pivot=pivot,
        overall=overall,
        terminology_coverage=coverage,
        pairs=pairs,
        divergences=divergences[:10],
        notes=notes,
    )


def consistency_issues(report: ConsistencyReport) -> list[dict]:
    """把一致性报告映射成校验问题：严重漂移 → blocker，轻度 → major，术语缺失 → minor。"""
    issues: list[dict] = []
    min_score = settings.consistency_min_score
    blocker_score = settings.consistency_blocker_score
    method_note = f"（方法：{report.method}，基准语种：{LANG_LABEL.get(report.pivot, report.pivot)}）"

    if report.overall < blocker_score:
        issues.append(
            {
                "severity": "blocker",
                "category": "consistency",
                "message": f"三语一致性仅 {report.overall:.0f} 分（低于 {blocker_score:.0f} 分的阻塞线）{method_note}",
                "suggestion": "对照 divergences 中分数最低的条目逐条核对，必要时重写对应语种的故事与验收标准",
            }
        )
    elif report.overall < min_score:
        issues.append(
            {
                "severity": "major",
                "category": "consistency",
                "message": f"三语一致性 {report.overall:.0f} 分（低于建议线 {min_score:.0f}）{method_note}",
                "suggestion": "优先复核 divergences 中列出的低分故事，确认各语种表达的是同一件事",
            }
        )

    # 同一条故事在多个语种里都会低于阈值：合并成一条问题，避免复读
    grouped: dict[str, dict] = {}
    for pair in report.pairs:
        for story in pair.stories:
            if story.score >= min_score:
                continue
            entry = grouped.setdefault(story.story_id, {"score": story.score, "langs": [], "veto": False, "conflict": None})
            entry["score"] = min(entry["score"], story.score)
            entry["langs"].append(LANG_LABEL.get(pair.lang, pair.lang))
            entry["veto"] = entry["veto"] or story.veto
            if entry["conflict"] is None and story.numeric_conflicts:
                entry["conflict"] = story.numeric_conflicts[0]

    for story_id, entry in sorted(grouped.items(), key=lambda item: item[1]["score"])[:2]:
        severity = "blocker" if entry["score"] < blocker_score else "major"
        if entry["veto"]:
            reason = "回译后与基准语种几乎无重合，疑似说的不是同一件事"
        elif entry["conflict"]:
            conflict = entry["conflict"]
            reason = f"同一条验收标准的数字阈值不一致：{conflict['pivot_ac']} vs {conflict['other_ac']}"
        else:
            reason = "编号/阈值/AC 数量/词面重合度偏低"
        issues.append(
            {
                "severity": severity,
                "category": "consistency",
                "message": f"故事 {story_id} 在 {'、'.join(entry['langs'])} 与基准语种的一致性仅 {entry['score']:.0f} 分：{reason}",
                "suggestion": "以基准语种为准重写该故事及其验收标准，保持编号与 AC 数量一致",
            }
        )

    if report.terminology_coverage < 0.6:
        issues.append(
            {
                "severity": "minor",
                "category": "consistency",
                "message": f"术语表在正文中的出现率仅 {report.terminology_coverage * 100:.0f}%，术语可能未被统一使用",
                "suggestion": "在正文中统一使用术语表里的对应语种写法",
            }
        )
    return issues
