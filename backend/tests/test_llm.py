import httpx
import pytest

from app.llm import FakeLLM, LLMError, OpenAICompatLLM, extract_json, salvage_truncated_json
from app.schemas import ClarificationRaw, PRDRaw


def test_extract_json_plain():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_fenced_and_prose():
    text = '好的，结果如下：\n```json\n{"a": [1, 2]}\n```\n希望有帮助'
    assert extract_json(text) == {"a": [1, 2]}


def test_extract_json_salvages_truncated_prd():
    """多语种 PRD 被 token 上限截断时，应救回已完成的语种而不是整轮失败。"""
    truncated = '{"product_name": "Demo", "glossary": [{"term_zh": "支付"}], "docs": [{"lang": "ja", "title": "PRD"}, {"lang": "en", "tit'
    parsed = extract_json(truncated)
    assert parsed["product_name"] == "Demo"
    assert parsed["glossary"] == [{"term_zh": "支付"}]
    assert parsed["docs"] == [{"lang": "ja", "title": "PRD"}]


def test_salvage_returns_none_for_garbage():
    assert salvage_truncated_json("not json at all") is None
    assert salvage_truncated_json('{"a": ') is None
    assert salvage_truncated_json('{"a": 1}')["a"] == 1


def test_extract_json_invalid():
    with pytest.raises(LLMError):
        extract_json("完全不是 JSON")
    with pytest.raises(LLMError):
        extract_json("")


def _patch_transport(monkeypatch, handler):
    transport = httpx.MockTransport(handler)
    original = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs.pop("timeout", None)
        return original(transport=transport)

    monkeypatch.setattr(httpx, "AsyncClient", factory)


def test_openai_compat_success(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/chat/completions")
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"passed": true, "summary": "ok", "issues": []}'}}],
                "usage": {"total_tokens": 42},
            },
        )

    _patch_transport(monkeypatch, handler)
    llm = OpenAICompatLLM(api_key="sk-test", base_url="https://example.com/v1", model="test-model")
    import asyncio

    from app.schemas import ValidationRaw

    result = asyncio.run(llm.chat_json(system="s", user="u", schema=ValidationRaw))
    assert result.data["passed"] is True
    assert result.tokens == 42


def test_openai_compat_retries_then_raises(monkeypatch):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(500, text="boom")

    _patch_transport(monkeypatch, handler)

    async def _no_sleep(_seconds):
        return None

    monkeypatch.setattr("app.llm.asyncio.sleep", _no_sleep)
    monkeypatch.setenv("LLM_MAX_RETRIES", "2")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "5")
    llm = OpenAICompatLLM(api_key="sk-test", base_url="https://example.com/v1")
    import asyncio

    from app.schemas import ValidationRaw

    with pytest.raises(LLMError):
        asyncio.run(llm.chat_json(system="s", user="u", schema=ValidationRaw))
    assert calls["n"] == 2


def test_openai_compat_requires_key():
    import asyncio

    from app.schemas import ValidationRaw

    llm = OpenAICompatLLM(api_key="")
    with pytest.raises(LLMError):
        asyncio.run(llm.chat_json(system="s", user="u", schema=ValidationRaw))


def test_fake_llm_is_deterministic_and_complete():
    import asyncio

    llm = FakeLLM()
    first = asyncio.run(llm.chat_json(system="", user="", schema=PRDRaw, extras={"raw_text": "需求", "target_langs": ["zh", "ja", "en"]}))
    second = asyncio.run(llm.chat_json(system="", user="", schema=PRDRaw, extras={"raw_text": "需求", "target_langs": ["zh", "ja", "en"]}))
    assert first.data == second.data

    prd = PRDRaw.model_validate(first.data)
    assert {doc.lang for doc in prd.docs} == {"zh", "ja", "en"}
    assert prd.glossary
    counts = {len(doc.user_stories) for doc in prd.docs}
    assert counts == {3}
    assert all(story.acceptance_criteria for doc in prd.docs for story in doc.user_stories)

    clarification = asyncio.run(llm.chat_json(system="", user="", schema=ClarificationRaw, extras={"raw_text": "需求"}))
    assert ClarificationRaw.model_validate(clarification.data).goal


def test_fake_llm_rejects_unknown_schema():
    import asyncio

    class Unknown(ClarificationRaw):
        pass

    llm = FakeLLM()
    with pytest.raises(LLMError):
        asyncio.run(llm.chat_json(system="", user="", schema=Unknown))
