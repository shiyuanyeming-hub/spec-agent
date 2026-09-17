import json

from app.agents.clarifier import ClarifierAgent
from app.llm import FakeLLM


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["provider"] == "fake"


def test_meta_exposes_samples_and_limits(client):
    body = client.get("/api/meta").json()
    assert body["supported_langs"] == ["zh", "ja", "en"]
    assert body["max_validation_rounds"] >= 1
    assert body["samples"] and {"id", "label", "text"} <= set(body["samples"][0])


def test_generate_returns_multilingual_prd(client, demo_text):
    resp = client.post("/api/generate", json={"raw_text": demo_text, "target_langs": ["zh", "ja", "en"]})
    assert resp.status_code == 200
    body = resp.json()
    assert set(body["prd"]["docs"]) == {"zh", "ja", "en"}
    assert set(body["markdown"]) == {"zh", "ja", "en"}
    assert body["glossary"]
    assert body["validation"]["passed"] is True
    assert body["rounds_used"] >= 1
    assert body["trace"][-1]["stage"] == "done"
    consistency = body["consistency"]
    assert consistency is not None
    assert consistency["method"] == "structural"
    assert consistency["overall"] > 0
    assert {pair["lang"] for pair in consistency["pairs"]} == {"ja", "en"}
    assert "三语一致性" in next(e["detail"] for e in body["trace"] if e["stage"] == "validator" and e["round"] == 1 and e["status"] != "start")


def test_generate_defaults_to_three_langs(client, demo_text):
    body = client.post("/api/generate", json={"raw_text": demo_text}).json()
    assert set(body["prd"]["docs"]) == {"zh", "ja", "en"}


def test_generate_rejects_short_text(client):
    resp = client.post("/api/generate", json={"raw_text": "太短"})
    assert resp.status_code == 422


def test_generate_rejects_unknown_lang(client, demo_text):
    resp = client.post("/api/generate", json={"raw_text": demo_text, "target_langs": ["zh", "fr"]})
    assert resp.status_code == 422


def test_generate_rejects_empty_langs(client, demo_text):
    resp = client.post("/api/generate", json={"raw_text": demo_text, "target_langs": []})
    assert resp.status_code == 422


def test_stream_emits_stage_events_then_result(client, demo_text):
    with client.stream("POST", "/api/generate/stream", json={"raw_text": demo_text}) as resp:
        assert resp.status_code == 200
        payload = "".join(resp.iter_text()).replace("\r\n", "\n")

    events = [block for block in payload.split("\n\n") if block.strip()]
    stages, results = [], []
    for block in events:
        event_line = next((line for line in block.splitlines() if line.startswith("event:")), "")
        data_line = next((line for line in block.splitlines() if line.startswith("data:")), "")
        if not data_line:
            continue
        data = json.loads(data_line[len("data:"):].strip())
        if "stage" in event_line:
            stages.append(data["stage"])
        elif "result" in event_line:
            results.append(data)

    assert stages[:1] == ["clarifier"]
    assert "structurer" in stages and "validator" in stages
    assert results and set(results[-1]["markdown"]) == {"zh", "ja", "en"}


def test_stream_reports_error_without_hanging(client, demo_text, monkeypatch):
    class BoomLLM(FakeLLM):
        async def chat_json(self, *args, **kwargs):
            from app.llm import LLMError

            raise LLMError("模拟失败")

    monkeypatch.setattr("app.main.iter_pipeline", lambda *_a, **_kw: _boom())

    with client.stream("POST", "/api/generate/stream", json={"raw_text": demo_text}) as resp:
        payload = "".join(resp.iter_text())
    assert "event: error" in payload


async def _boom():
    from app.llm import LLMError

    raise LLMError("模拟失败")
    yield  # pragma: no cover


async def test_clarifier_parses_structured_output(demo_text):
    clarified = await ClarifierAgent(FakeLLM()).run(demo_text)
    assert clarified.goal and clarified.target_users
    assert clarified.open_questions
    assert clarified.original == demo_text
