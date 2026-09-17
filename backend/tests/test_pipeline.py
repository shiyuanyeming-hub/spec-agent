import pytest

from app.llm import FakeLLM
from app.pipeline import run_pipeline

LANGS = ["zh", "ja", "en"]


async def test_fake_pipeline_passes_first_round(demo_text):
    result = await run_pipeline(demo_text, LANGS, llm=FakeLLM())
    assert result.rounds_used == 1
    assert result.validation.passed is True
    assert set(result.prd.docs) == set(LANGS)
    assert set(result.markdown) == set(LANGS)
    assert result.provider == "fake"
    stages = [e["stage"] for e in result.trace]
    assert stages[:1] == ["clarifier"]
    assert "structurer" in stages and "validator" in stages and stages[-1] == "done"


async def test_validator_feedback_triggers_second_round(demo_text):
    llm = FakeLLM(fail_validation_rounds=1)
    result = await run_pipeline(demo_text, LANGS, llm=llm)
    assert result.rounds_used == 2
    assert result.validation.passed is True
    assert result.clarifications.feedback, "校验问题应回注到澄清结果"
    assert any("已修正" in doc["background"] for doc in result.prd.docs.values())


class ScriptedValidatorLLM(FakeLLM):
    """按轮次返回脚本化的校验问题，用于验证"迭代 + 收敛 + 止损"逻辑。"""

    def __init__(self, blockers_per_round: list[int], majors_per_round: list[int] | None = None):
        super().__init__()
        self.blockers_per_round = blockers_per_round
        self.majors_per_round = majors_per_round or []

    def _validation(self, extras: dict, schema) -> dict:
        round_no = min(int(extras.get("round", 1)), len(self.blockers_per_round))
        blockers = self.blockers_per_round[round_no - 1]
        majors = self.majors_per_round[round_no - 1] if round_no <= len(self.majors_per_round) else 0
        issues = [
            {
                "severity": "blocker",
                "category": "consistency",
                "message": f"（脚本化）第 {round_no} 轮仍有 {blockers} 个 blocker",
                "suggestion": "补齐缺失语种/故事/验收标准",
            }
        ] * blockers + [
            {
                "severity": "major",
                "category": "testability",
                "message": f"（脚本化）第 {round_no} 轮仍有 {majors} 个 major",
                "suggestion": "补上可判定阈值",
            }
        ] * majors
        return {"passed": blockers == 0, "summary": f"第 {round_no} 轮：blocker={blockers} major={majors}", "issues": issues}


async def test_rounds_are_capped_at_max_rounds(demo_text):
    llm = ScriptedValidatorLLM(blockers_per_round=[3, 2, 1])
    result = await run_pipeline(demo_text, LANGS, llm=llm, max_rounds=2)
    assert result.rounds_used == 2
    assert result.validation.passed is False
    assert result.validation.blockers
    assert result.validation.status == "blocked"
    assert result.stalled is False


async def test_loop_converges_when_blockers_shrink(demo_text):
    llm = ScriptedValidatorLLM(blockers_per_round=[2, 1, 0])
    result = await run_pipeline(demo_text, LANGS, llm=llm, max_rounds=3)
    assert result.rounds_used == 3
    assert result.validation.passed is True


async def test_loop_stops_early_when_no_progress(demo_text):
    llm = ScriptedValidatorLLM(blockers_per_round=[2, 2, 2])
    result = await run_pipeline(demo_text, LANGS, llm=llm, max_rounds=3)
    assert result.rounds_used == 2, "问题数不再下降时应提前止损"
    assert result.stalled is True
    assert result.status == "blocked"


async def test_major_only_issues_do_not_block_delivery(demo_text):
    result = await run_pipeline(demo_text, LANGS, llm=FakeLLM(fail_validation_rounds=99), max_rounds=3)
    assert result.validation.passed is True
    assert result.status == "needs_review"
    assert result.validation.majors and not result.validation.blockers
    assert result.rounds_used == 2, "首轮 major 会回注一次，第二轮无改善即止损"


async def test_lang_subset_is_respected(demo_text):
    result = await run_pipeline(demo_text, ["ja", "en"], llm=FakeLLM())
    assert result.prd.target_langs == ["ja", "en"]
    assert set(result.markdown) == {"ja", "en"}


class DroppingLLM(FakeLLM):
    """模拟模型漏输出某个语种：应被确定性结构校验拦下。"""

    async def chat_json(self, system, user, schema, extras=None, temperature=None):
        result = await super().chat_json(system, user, schema, extras=extras, temperature=temperature)
        if schema.__name__ == "PRDRaw":
            result.data["docs"] = [d for d in result.data["docs"] if d["lang"] != "ja"]
        return result


async def test_missing_lang_from_model_is_reported(demo_text):
    result = await run_pipeline(demo_text, LANGS, llm=DroppingLLM(), max_rounds=1)
    assert result.validation.passed is False
    assert any("blocker" == i["severity"] for i in result.validation.issues)
    assert any("ja" in i["message"] for i in result.validation.issues)
    # 兜底：即使模型漏语种，返回结构仍然完整，前端不会崩
    assert set(result.prd.docs) == set(LANGS)


async def test_inconsistent_story_counts_are_blocking(demo_text):
    class InconsistentLLM(FakeLLM):
        async def chat_json(self, system, user, schema, extras=None, temperature=None):
            result = await super().chat_json(system, user, schema, extras=extras, temperature=temperature)
            if schema.__name__ == "PRDRaw":
                for doc in result.data["docs"]:
                    if doc["lang"] == "en":
                        doc["user_stories"] = doc["user_stories"][:1]
            return result

    result = await run_pipeline(demo_text, LANGS, llm=InconsistentLLM(), max_rounds=1)
    assert result.validation.passed is False
    assert any(i["category"] == "consistency" for i in result.validation.issues)


@pytest.mark.parametrize("fail_rounds,expected_rounds", [(0, 1), (1, 2), (5, 2)])
async def test_validation_round_matrix(demo_text, fail_rounds, expected_rounds):
    result = await run_pipeline(demo_text, LANGS, llm=FakeLLM(fail_validation_rounds=fail_rounds), max_rounds=3)
    assert result.rounds_used == expected_rounds
