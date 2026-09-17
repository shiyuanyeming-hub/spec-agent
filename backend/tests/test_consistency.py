"""三语一致性量化评分：度量、阈值映射与三种方法的测试。"""
import copy

import httpx
import pytest

from app.agents.structurer import PRD
from app.agents.validator import ValidatorAgent
from app.consistency import backtranslate, consistency_issues, evaluate_consistency
from app.embeddings import FakeEmbeddings, OpenAICompatEmbeddings
from app.llm import FakeLLM
from app.similarity import containment, dice_counters, numbers_similarity, similarity, vector

Story = dict


def base_docs() -> dict[str, dict]:
    zh = {
        "lang": "zh",
        "title": "银发支付优化 PRD",
        "background": "高龄用户在支付页流失严重，需要在下一季度完成优化。",
        "goal": "让 65 岁以上用户顺利完成支付。",
        "user_stories": [
            {
                "id": "US-1",
                "story": "作为年长用户，我希望看清按钮，以便快速完成支付。",
                "acceptance_criteria": ["主按钮字号 >= 18pt", "支付流程 <= 3 步", "对比度符合 WCAG 2.1 AA"],
            },
            {
                "id": "US-2",
                "story": "作为运营同学，我希望看到漏斗数据，以便优先修复。",
                "acceptance_criteria": ["提供漏斗看板"],
            },
        ],
        "functional_reqs": ["简化支付流程"],
        "nonfunctional_reqs": ["首屏 1.5s 内渲染"],
        "risks": ["本地支付渠道未定"],
        "open_questions": ["是否支持 PayPay？"],
    }
    ja = copy.deepcopy(zh)
    ja["lang"] = "ja"
    ja["title"] = "支払いフロー改善 PRD"
    ja["background"] = "高齢ユーザーの離脱が深刻で、次の四半期に対応が必要。"
    ja["goal"] = "65 歳以上のユーザーが支払いを完了できるようにする。"
    ja["user_stories"][0]["story"] = "高齢ユーザーとして、ボタンを判別しやすくして支払いを素早く完了したい。"
    ja["user_stories"][0]["acceptance_criteria"] = ["主要ボタン >= 18pt", "支払い <= 3 ステップ", "WCAG 2.1 AA 相当"]
    ja["user_stories"][1]["story"] = "運用担当として、ファネルを見て優先的に修正したい。"
    ja["user_stories"][1]["acceptance_criteria"] = ["ファネル計測を提供"]
    en = copy.deepcopy(zh)
    en["lang"] = "en"
    en["title"] = "Senior Payment PRD"
    en["background"] = "Senior users drop off on the payment page; fix next quarter."
    en["goal"] = "Let users aged 65+ complete payment."
    en["user_stories"][0]["story"] = "As a senior user I want readable buttons so that I can pay quickly."
    en["user_stories"][0]["acceptance_criteria"] = ["Primary button >= 18pt", "Payment <= 3 steps", "Contrast meets WCAG 2.1 AA"]
    en["user_stories"][1]["story"] = "As an ops owner I want funnel data so that I can prioritise fixes."
    en["user_stories"][1]["acceptance_criteria"] = ["Provide a funnel dashboard"]
    return {"zh": zh, "ja": ja, "en": en}


def make_prd(langs=("zh", "ja", "en"), glossary=None) -> PRD:
    docs = base_docs()
    chosen = {lang: docs[lang] for lang in langs}
    return PRD(
        product_name="银发支付优化",
        docs=chosen,
        glossary=glossary
        if glossary is not None
        else [
            {"term_zh": "漏斗看板", "term_en": "funnel dashboard", "term_ja": "ファネル計測", "note": ""},
            {"term_zh": "支付", "term_en": "payment", "term_ja": "支払い", "note": ""},
        ],
        target_langs=list(langs),
    )


# ---------- 度量本身 ----------

def test_dice_and_containment_behave_sensibly():
    assert similarity("主按钮字号至少 18pt", "主按钮字号至少 18pt") == 1.0
    assert similarity("主按钮字号至少 18pt", "支持语音播报提示音") < 0.1
    assert containment("主按钮", "主按钮字号至少 18pt") > 0.9
    assert dice_counters(vector("abc"), vector("")) == 0.0


def test_numbers_similarity_detects_threshold_drift():
    assert numbers_similarity("字号 >= 18pt", "字号 >= 18pt") == 1.0
    assert numbers_similarity("字号 >= 18pt", "字号 >= 24pt") < 1.0
    assert numbers_similarity("没有数字", "也没有数字") == 1.0


# ---------- structural 模式（默认，零成本） ----------

async def test_perfect_alignment_scores_100(monkeypatch):
    monkeypatch.setenv("CONSISTENCY_METHOD", "structural")
    report = await evaluate_consistency(make_prd())
    assert report.overall == pytest.approx(100.0, abs=0.5)
    assert report.terminology_coverage == 1.0
    assert report.divergences == []
    assert consistency_issues(report) == []


async def test_missing_story_id_lowers_score_and_is_reported(monkeypatch):
    monkeypatch.setenv("CONSISTENCY_METHOD", "structural")
    prd = make_prd()
    prd.docs["ja"]["user_stories"] = prd.docs["ja"]["user_stories"][:1]
    report = await evaluate_consistency(prd)
    ja_pair = next(pair for pair in report.pairs if pair.lang == "ja")
    assert ja_pair.components["ids"] == pytest.approx(0.5)
    assert "US-2" in ja_pair.missing_ids
    assert any(item["reason"] == "故事编号未一一对应" for item in report.divergences)


async def test_ac_count_mismatch_lowers_ac_component(monkeypatch):
    monkeypatch.setenv("CONSISTENCY_METHOD", "structural")
    prd = make_prd()
    prd.docs["en"]["user_stories"][0]["acceptance_criteria"] = ["Primary button >= 18pt"]
    report = await evaluate_consistency(prd)
    en_pair = next(pair for pair in report.pairs if pair.lang == "en")
    assert en_pair.components["ac"] < 0.8


async def test_numeric_drift_is_flagged(monkeypatch):
    monkeypatch.setenv("CONSISTENCY_METHOD", "structural")
    prd = make_prd()
    prd.docs["ja"]["user_stories"][0]["acceptance_criteria"] = ["主要ボタン >= 24pt", "支払い <= 3 ステップ", "WCAG 2.1 AA 相当"]
    report = await evaluate_consistency(prd)
    story = next(s for pair in report.pairs if pair.lang == "ja" for s in pair.stories if s.story_id == "US-1")
    assert story.components["numeric"] < 1.0
    assert any(item["story_id"] == "US-1" and item["lang"] == "ja" for item in report.divergences)


async def test_dropped_technical_term_lowers_entity_component(monkeypatch):
    monkeypatch.setenv("CONSISTENCY_METHOD", "structural")
    prd = make_prd()
    prd.docs["en"]["user_stories"][0]["acceptance_criteria"] = ["Primary button >= 18pt", "Payment <= 3 steps"]
    report = await evaluate_consistency(prd)
    en_pair = next(pair for pair in report.pairs if pair.lang == "en")
    assert en_pair.components["entity"] < 1.0


async def test_terminology_coverage_and_minor_issue(monkeypatch):
    monkeypatch.setenv("CONSISTENCY_METHOD", "structural")
    prd = make_prd()
    prd.glossary = [{"term_zh": "支付", "term_en": "payment", "term_ja": "支払い", "note": ""},
                    {"term_zh": "不存在的术语", "term_en": "ghost term", "term_ja": "存在しない用語", "note": ""}]
    report = await evaluate_consistency(prd)
    assert report.terminology_coverage == pytest.approx(0.5)
    assert any(issue["severity"] == "minor" for issue in consistency_issues(report))


async def test_single_language_skips_cross_language_scoring(monkeypatch):
    monkeypatch.setenv("CONSISTENCY_METHOD", "structural")
    report = await evaluate_consistency(make_prd(langs=("zh",)))
    assert report.pairs == []
    assert any("单语种" in note for note in report.notes)


# ---------- backtranslate 模式 ----------

async def test_backtranslate_scores_semantics(monkeypatch):
    monkeypatch.setenv("CONSISTENCY_METHOD", "backtranslate")
    llm = FakeLLM()
    report = await evaluate_consistency(make_prd(), llm=llm)
    assert report.method == "backtranslate"
    assert llm.calls.count("BackTranslationRaw") == 2, "每个非基准语种一次回译调用"
    for pair in report.pairs:
        assert pair.components["semantic"] is not None
    assert report.overall > 90


def _long_story(index: int) -> dict:
    filler = "这是一段用于撑大回译请求体积的描述文字，" * 6
    return {
        "id": f"US-{index}",
        "story": f"作为用户 {index}，我希望{ '完成支付流程' * 4 }，以便快速拿到结果。{filler}",
        "acceptance_criteria": [f"步骤 {index} 不超过 3 步，{filler}", f"响应时间 {index} 秒以内，{filler}"],
    }


async def test_long_documents_are_split_into_smaller_backtranslation_calls(monkeypatch):
    monkeypatch.setenv("CONSISTENCY_METHOD", "backtranslate")
    monkeypatch.setenv("BACKTRANSLATE_CHUNK_CHARS", "900")
    prd = make_prd(langs=("zh", "ja"))
    prd.docs["zh"]["user_stories"] = [_long_story(index) for index in range(1, 7)]
    prd.docs["ja"]["user_stories"] = [_long_story(index) for index in range(1, 7)]
    llm = FakeLLM()
    report = await evaluate_consistency(prd, llm=llm)
    assert llm.calls.count("BackTranslationRaw") > 1, "超长 PRD 应被分片回译"
    assert report.pairs[0].components["semantic"] is not None
    assert report.overall > 90


class FlakyChunkLLM(FakeLLM):
    """故事数超过阈值就报 JSON 破损：验证分片失败后能二分重试恢复。"""

    max_stories = 2

    async def chat_json(self, system, user, schema, extras=None, temperature=None):
        if schema.__name__ == "BackTranslationRaw":
            stories = (extras or {}).get("chunk_doc", {}).get("user_stories") or []
            if len(stories) > self.max_stories:
                from app.llm import LLMError

                raise LLMError("模拟长输出 JSON 破损")
        return await super().chat_json(system, user, schema, extras=extras, temperature=temperature)


async def test_backtranslation_bisects_and_recovers_from_broken_chunks(monkeypatch):
    monkeypatch.setenv("CONSISTENCY_METHOD", "backtranslate")
    monkeypatch.setenv("BACKTRANSLATE_CHUNK_CHARS", "900")
    prd = make_prd(langs=("zh", "ja"))
    prd.docs["zh"]["user_stories"] = [_long_story(index) for index in range(1, 5)]
    prd.docs["ja"]["user_stories"] = [_long_story(index) for index in range(1, 5)]
    docs, note = await backtranslate(prd, FlakyChunkLLM(), "zh", ["zh", "ja"])
    assert note is None, "二分重试后应完整恢复，不应留下失败说明"
    assert [story["id"] for story in docs["ja"]["user_stories"]] == ["US-1", "US-2", "US-3", "US-4"]


class DriftingLLM(FakeLLM):
    """回译时把第一条故事换成完全无关的内容：应被判为严重漂移。"""

    def _backtranslation(self, extras: dict) -> dict:
        data = super()._backtranslation(extras)
        for doc in data["docs"]:
            doc["user_stories"][0]["story"] = "把页面背景换成蓝色，与支付流程无关。"
            doc["user_stories"][0]["acceptance_criteria"] = ["背景色为蓝色"]
        return data


async def test_backtranslate_drift_produces_blocker(monkeypatch):
    monkeypatch.setenv("CONSISTENCY_METHOD", "backtranslate")
    report = await evaluate_consistency(make_prd(), llm=DriftingLLM())
    issues = consistency_issues(report)
    assert any(issue["severity"] == "blocker" for issue in issues)
    assert report.worst_stories[0].story_id == "US-1"


class EnglishEchoLLM(FakeLLM):
    """回译时把英文原文抄回来（没有真的翻成基准语言）：语义信号应被丢弃，而不是报假漂移。"""

    def _backtranslation(self, extras: dict) -> dict:
        data = super()._backtranslation(extras)
        for doc in data["docs"]:
            doc["title"] = "Senior Payment PRD"
            doc["background"] = "Senior users drop off on the payment page."
            doc["goal"] = "Let users aged 65+ complete payment."
            for story in doc["user_stories"]:
                story["story"] = "As a senior user I want readable buttons so that I can pay quickly."
                story["acceptance_criteria"] = ["Primary button >= 18pt", "Payment <= 3 steps"]
        return data


async def test_backtranslation_in_wrong_language_is_ignored(monkeypatch):
    monkeypatch.setenv("CONSISTENCY_METHOD", "backtranslate")
    report = await evaluate_consistency(make_prd(), llm=EnglishEchoLLM())
    assert all(pair.components.get("semantic") is None for pair in report.pairs), "语言不符的回译不该参与打分"
    assert any("不是简体中文" in note for note in report.notes)
    assert not any(issue["severity"] == "blocker" for issue in consistency_issues(report)), "不该因为抄回原文而报阻塞"
    assert report.overall > 90


async def test_backtranslate_failure_degrades_gracefully(monkeypatch):
    monkeypatch.setenv("CONSISTENCY_METHOD", "backtranslate")

    class BrokenLLM(FakeLLM):
        async def chat_json(self, *args, **kwargs):
            from app.llm import LLMError

            raise LLMError("模拟回译失败")

    report = await evaluate_consistency(make_prd(), llm=BrokenLLM())
    assert report.method == "backtranslate"
    assert any("回译失败" in note for note in report.notes)
    assert report.overall > 80, "确定性信号仍应给出可用分数"
    assert all(pair.components.get("semantic") is None for pair in report.pairs)


async def test_backtranslate_prompt_and_schema_are_used(monkeypatch):
    monkeypatch.setenv("CONSISTENCY_METHOD", "backtranslate")
    prd = make_prd()
    docs, error = await backtranslate(prd, FakeLLM(), "zh", ["zh", "ja", "en"])
    assert error is None
    assert set(docs) == {"ja", "en"}
    assert docs["ja"]["user_stories"][0]["id"] == "US-1"


# ---------- embeddings 模式 ----------

async def test_embeddings_method_scores_semantics(monkeypatch):
    monkeypatch.setenv("CONSISTENCY_METHOD", "embeddings")
    report = await evaluate_consistency(make_prd(), embeddings=FakeEmbeddings())
    assert report.method == "embeddings"
    assert all(pair.components["semantic"] is not None for pair in report.pairs)


async def test_fake_embeddings_are_deterministic():
    embeddings = FakeEmbeddings()
    first = await embeddings.embed(["银发支付", "senior payment"])
    second = await embeddings.embed(["银发支付", "senior payment"])
    assert first == second
    assert len(first[0]) == 64


async def test_openai_compat_embeddings_parses_response(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/embeddings")
        return httpx.Response(200, json={"data": [{"index": 1, "embedding": [0.0, 1.0]}, {"index": 0, "embedding": [1.0, 0.0]}]})

    transport = httpx.MockTransport(handler)
    original = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs.pop("timeout", None)
        return original(transport=transport)

    monkeypatch.setattr(httpx, "AsyncClient", factory)
    client = OpenAICompatEmbeddings(api_key="sk-test", base_url="https://example.com/v1")
    vectors = await client.embed(["a", "b"])
    assert vectors == [[1.0, 0.0], [0.0, 1.0]], "应按 index 排序"


# ---------- 与 Validator / 配置联动 ----------

async def test_validator_attaches_consistency_and_off_switch(monkeypatch):
    monkeypatch.setenv("CONSISTENCY_METHOD", "backtranslate")
    report = await ValidatorAgent(FakeLLM()).run(make_prd())
    assert report.consistency is not None
    assert report.consistency_score is not None

    monkeypatch.setenv("CONSISTENCY_METHOD", "off")
    llm = FakeLLM()
    report = await ValidatorAgent(llm).run(make_prd())
    assert report.consistency is None
    assert "BackTranslationRaw" not in llm.calls


async def test_thresholds_are_configurable(monkeypatch):
    monkeypatch.setenv("CONSISTENCY_METHOD", "structural")
    prd = make_prd()
    prd.docs["ja"]["user_stories"][0]["acceptance_criteria"] = ["主要ボタン >= 24pt", "支払い <= 3 ステップ"]
    report = await evaluate_consistency(prd)

    monkeypatch.setenv("CONSISTENCY_MIN_SCORE", "99")
    monkeypatch.setenv("CONSISTENCY_BLOCKER_SCORE", "20")
    severities = {issue["severity"] for issue in consistency_issues(report)}
    assert "major" in severities and "blocker" not in severities

    monkeypatch.setenv("CONSISTENCY_BLOCKER_SCORE", "99")
    assert any(issue["severity"] == "blocker" for issue in consistency_issues(report))
