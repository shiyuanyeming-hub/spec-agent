"""LLM 客户端：OpenAI 兼容接口 + 离线 fake 模式，统一结构化（JSON）输出。

- `OpenAICompatLLM`：任何兼容 /chat/completions 的服务（OpenAI、DeepSeek、Ollama、vLLM…）
- `FakeLLM`：无 API key 时的确定性 Mock，输出结构合法，保证零配置可跑通全流程
"""
import asyncio
import json
import re
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from .config import settings

FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


class LLMError(RuntimeError):
    """LLM 调用或结构化解析失败。"""


@dataclass
class LLMResult:
    data: dict
    tokens: int = 0


def salvage_truncated_json(text: str) -> dict | None:
    """从被截断的 JSON 里救回"最后一个完整元素之前"的内容。

    多语种 PRD 很长，模型偶尔会在 glossary/docs 中途被 token 上限切断。
    这里一次性扫描并记录所有"完整的数组/对象结束位置"，取最后一个，补上闭合括号即可解析——
    丢掉的是尾部未完成的部分，而不是整轮生成。
    """
    stack: list[str] = []
    in_string = False
    escaped = False
    last_boundary: tuple[int, list[str]] | None = None
    pairs = {"{": "}", "[": "]"}

    for index, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char in pairs:
            stack.append(char)
        elif char in ("}", "]"):
            if stack and pairs[stack[-1]] == char:
                stack.pop()
                if stack:
                    last_boundary = (index + 1, list(stack))
                elif index + 1 == len(text):
                    last_boundary = (index + 1, [])

    if not last_boundary:
        return None
    end, remaining = last_boundary
    candidate = text[:end] + "".join(pairs[open_bracket] for open_bracket in reversed(remaining))
    try:
        repaired = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return repaired if isinstance(repaired, dict) else None


def extract_json(text: str) -> dict:
    """从模型输出里取出 JSON 对象：容忍 ```json 围栏与前后废话。"""
    if not text or not text.strip():
        raise LLMError("模型返回空内容")
    candidate = text.strip()
    fenced = FENCE_RE.search(candidate)
    if fenced:
        candidate = fenced.group(1).strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start == -1 or end <= start:
            salvaged = salvage_truncated_json(text)
            if salvaged is not None:
                return salvaged
            raise LLMError(f"模型返回内容不是 JSON：{text[:200]}") from None
        try:
            parsed = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError as exc:
            salvaged = salvage_truncated_json(candidate[start:])
            if salvaged is not None:
                return salvaged
            raise LLMError(f"模型返回 JSON 解析失败：{exc}; 原文片段：{text[:200]}") from exc
    if not isinstance(parsed, dict):
        raise LLMError("模型返回的顶层 JSON 必须是对象")
    return parsed


class OpenAICompatLLM:
    """OpenAI 兼容 Chat Completions 客户端（JSON 模式 + 重试）。"""

    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None):
        self.api_key = api_key if api_key is not None else settings.llm_api_key
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self.model = model or settings.llm_model

    async def chat_json(
        self,
        system: str,
        user: str,
        schema: type[BaseModel],
        extras: dict | None = None,
        temperature: float | None = None,
    ) -> LLMResult:
        if not self.api_key:
            raise LLMError("缺少 LLM_API_KEY，无法调用真实模型")

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": settings.llm_temperature if temperature is None else temperature,
            "response_format": {"type": "json_object"},
        }
        if settings.llm_max_tokens:
            payload["max_tokens"] = settings.llm_max_tokens
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        url = f"{self.base_url}/chat/completions"

        last_error: Exception | None = None
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            for attempt in range(1, settings.llm_max_retries + 1):
                try:
                    resp = await client.post(url, json=payload, headers=headers)
                    if resp.status_code >= 400:
                        raise LLMError(f"LLM 接口返回 {resp.status_code}: {resp.text[:200]}")
                    body = resp.json()
                    content = body["choices"][0]["message"]["content"]
                    data = extract_json(content)
                    schema.model_validate(data)
                    usage = body.get("usage") or {}
                    return LLMResult(data=data, tokens=int(usage.get("total_tokens") or 0))
                except (httpx.HTTPError, KeyError, IndexError, LLMError, ValidationError) as exc:
                    last_error = exc
                    if attempt < settings.llm_max_retries:
                        await asyncio.sleep(min(2 ** attempt, 8))
        raise LLMError(f"LLM 调用失败（{settings.llm_max_retries} 次尝试）：{last_error}")


def _clip(text: str, limit: int = 60) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


class FakeLLM:
    """确定性 Mock：结构合法、多语种齐全，用于无 key 演示与单测。"""

    def __init__(self, fail_validation_rounds: int = 0):
        # >0 时前 N 轮校验返回不通过，用于演示/测试 Validator 回注闭环
        self.fail_validation_rounds = fail_validation_rounds
        self.calls: list[str] = []

    async def chat_json(
        self,
        system: str,
        user: str,
        schema: type[BaseModel],
        extras: dict | None = None,
        temperature: float | None = None,
    ) -> LLMResult:
        extras = extras or {}
        name = schema.__name__
        self.calls.append(name)
        if name == "ClarificationRaw":
            return LLMResult(self._clarification(extras))
        if name == "PRDRaw":
            return LLMResult(self._prd(extras))
        if name == "ValidationRaw":
            return LLMResult(self._validation(extras, schema))
        if name == "BackTranslationRaw":
            return LLMResult(self._backtranslation(extras))
        raise LLMError(f"FakeLLM 不支持的 schema：{name}")

    def _backtranslation(self, extras: dict) -> dict:
        """Mock 回译：把基准语种原文当作回译结果（一致性接近满分，链路可验证）。

        分片回译时只回译本片包含的故事编号，因此用 chunk_doc 决定"回译哪几条"，
        内容仍取基准语种原文——这正是忠实回译应有的样子。
        """
        pivot_doc = extras.get("pivot_doc") or {}
        chunk_doc = extras.get("chunk_doc") or pivot_doc
        sources = list(extras.get("source_langs") or [])
        by_id = {str(story.get("id")): story for story in (pivot_doc.get("user_stories") or [])}
        ids = [str(story.get("id")) for story in (chunk_doc.get("user_stories") or [])] or list(by_id)
        stories = [
            {
                "id": story_id,
                "story": by_id[story_id].get("story", ""),
                "acceptance_criteria": list(by_id[story_id].get("acceptance_criteria") or []),
            }
            for story_id in ids
            if story_id in by_id
        ]
        return {
            "docs": [
                {
                    "lang": lang,
                    "title": pivot_doc.get("title", "") if chunk_doc is pivot_doc else "",
                    "background": pivot_doc.get("background", "") if chunk_doc is pivot_doc else "",
                    "goal": pivot_doc.get("goal", "") if chunk_doc is pivot_doc else "",
                    "user_stories": stories,
                }
                for lang in sources
            ]
        }

    def _clarification(self, extras: dict) -> dict:
        raw = _clip(str(extras.get("raw_text", "")), 80)
        return {
            "goal": f"（Mock 模式）落实需求：{raw}",
            "target_users": "（Mock 模式）该需求直接影响的终端用户与一线运营同学",
            "success_metrics": ["核心任务完成率 >= 90%", "相关客诉量下降 30%", "上线后 2 周内拿到可用性验证数据"],
            "scope": "首期只覆盖主流程与最高频的两条支线，长尾场景放入 Open Questions",
            "assumptions": ["（Mock 模式）假设主流程改造不需要后端接口协议变更"],
            "open_questions": ["该需求的目标市场与上线时间是？", "是否有合规/法务前置审查？"],
        }

    def _prd(self, extras: dict) -> dict:
        raw = str(extras.get("raw_text", ""))
        langs = list(extras.get("target_langs") or ["zh", "ja", "en"])
        product_name = f"（Mock）{_clip(raw, 24)}"
        docs = [self._lang_doc(lang, product_name, raw, extras.get("feedback") or []) for lang in langs]
        return {
            "product_name": product_name,
            "glossary": [
                {"term_zh": "进度指示", "term_en": "progress indicator", "term_ja": "進捗インジケータ", "note": "让用户知道当前在第几步"},
                {"term_zh": "支付", "term_en": "payment", "term_ja": "支払い", "note": "本文档讨论的核心动作"},
                {"term_zh": "漏斗看板", "term_en": "funnel dashboard", "term_ja": "ファネル計測", "note": "按环节统计流失的看板"},
            ],
            "docs": docs,
        }

    def _lang_doc(self, lang: str, product_name: str, raw: str, feedback: list) -> dict:
        note = f" （已修正：{_clip(str(feedback[0]), 30)}）" if feedback else ""
        if lang == "ja":
            title = f"{product_name} 要件定義書"
            background = "（Mock モード）現場ヒアリングでは、現行フローの認知負荷が高く離脱が発生しているとの声が多数ありました。" + note
            goal = "対象ユーザーが迷わず主タスクを完了できるようにする。" + note
            stories = [
                {"id": "US-1", "story": "高齢ユーザーとして、拡大せずに主要ボタンを判別したい。そうすれば短時間で支払いを完了できる。", "acceptance_criteria": ["主要ボタンの文字サイズは 18pt 以上", "支払いステップは 3 ステップ以内", "誤操作時の取り消し導線がある"]},
                {"id": "US-2", "story": "初回ユーザーとして、現在地と次の操作を常に把握したい。そうすれば途中で離脱しない。", "acceptance_criteria": ["各画面に進捗インジケータを表示", "戻る操作で入力内容が保持される"]},
                {"id": "US-3", "story": "運用担当として、離脱箇所を把握したい。そうすれば優先的に改善できる。", "acceptance_criteria": ["ファネル計測のダッシュボードを提供", "離脱率を日次で確認できる"]},
            ]
            functional = ["対象ユーザー向けの簡素化フローを提供する", "主要操作に明確なフィードバックを返す"]
            nonfunctional = ["主要画面の表示は 1.5 秒以内", "WCAG 2.1 AA 相当のコントラストとフォーカス可視化"]
            risks = ["ローカル決済手段との連携仕様が未確定", "法規制・社内審査のリードタイム"]
            questions = ["対象年齢の定義は？（65 歳以上か）", "ローカル決済は今回のスコープに含めるか？"]
        elif lang == "en":
            title = f"{product_name} PRD"
            background = "（Mock mode）Field interviews show the current flow imposes a high cognitive load, causing drop-offs." + note
            goal = "Let target users finish the primary task without confusion." + note
            stories = [
                {"id": "US-1", "story": "As an older user, I want to read primary buttons without zooming, so that I can complete payment quickly.", "acceptance_criteria": ["Primary button label >= 18pt", "Payment takes <= 3 steps", "A clear undo path exists for mistakes"]},
                {"id": "US-2", "story": "As a first-time user, I want to always know where I am and what comes next, so that I do not abandon the flow.", "acceptance_criteria": ["Every screen shows a progress indicator", "Going back preserves entered data"]},
                {"id": "US-3", "story": "As an operations owner, I want to see where users drop off, so that I can prioritize fixes.", "acceptance_criteria": ["A funnel dashboard is available", "Drop-off rate is visible daily"]},
            ]
            functional = ["Provide a simplified flow for the target users", "Return clear feedback for primary actions"]
            nonfunctional = ["Primary screens render within 1.5s", "WCAG 2.1 AA level contrast and focus visibility"]
            risks = ["Local payment integration spec is not finalized", "Regulatory and internal review lead time"]
            questions = ["How is the target age defined (65+)?", "Are local payment methods in scope for phase 1?"]
        else:
            title = f"{product_name} 产品需求文档"
            background = "（Mock 模式）一线访谈显示现有流程认知负担偏高，用户在中途流失。" + note
            goal = "让目标用户在不困惑的前提下完成主任务。" + note
            stories = [
                {"id": "US-1", "story": "作为年长用户，我希望不必缩放就能看清主要按钮，以便快速完成支付。", "acceptance_criteria": ["主按钮字号 >= 18pt", "支付流程 <= 3 步", "误操作有明确撤销路径"]},
                {"id": "US-2", "story": "作为首次使用的用户，我希望随时知道自己在哪一步、下一步做什么，以便不会中途放弃。", "acceptance_criteria": ["每个页面展示进度指示", "返回上一步时保留已填写内容"]},
                {"id": "US-3", "story": "作为运营同学，我希望看到用户在哪个环节流失，以便优先修复。", "acceptance_criteria": ["提供漏斗看板", "可查看每日流失率"]},
            ]
            functional = ["为目标用户提供简化流程", "对主要操作给出明确反馈"]
            nonfunctional = ["主要页面首屏 1.5s 内渲染", "对比度与聚焦样式达到 WCAG 2.1 AA"]
            risks = ["本地支付渠道接入规格未定", "合规与内部评审周期不可控"]
            questions = ["目标年龄如何界定（是否 65 岁以上）？", "本地支付方式是否纳入首期范围？"]
        return {
            "lang": lang,
            "title": title,
            "background": background,
            "goal": goal,
            "user_stories": stories,
            "functional_reqs": functional,
            "nonfunctional_reqs": nonfunctional,
            "risks": risks,
            "open_questions": questions,
        }

    def _validation(self, extras: dict, schema: type[BaseModel]) -> dict:
        round_no = int(extras.get("round", 1))
        if round_no <= self.fail_validation_rounds:
            return {
                "passed": False,
                "summary": "（Mock 模式）首轮校验不通过，回注 Structurer 修正。",
                "issues": [
                    {
                        "severity": "major",
                        "category": "testability",
                        "message": "（Mock 模式）部分验收标准尚无量化阈值。",
                        "suggestion": "为每条验收标准补上可判定的阈值或判定条件。",
                    }
                ],
            }
        return {"passed": True, "summary": "（Mock 模式）INVEST、可测试性与多语种一致性检查通过。", "issues": []}


def get_llm():
    """按配置返回 LLM 客户端；未配置 key 时返回 FakeLLM（零配置可跑）。"""
    if settings.llm_provider == "fake" or not settings.llm_api_key:
        return FakeLLM()
    return OpenAICompatLLM()
