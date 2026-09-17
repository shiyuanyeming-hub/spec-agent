# Spec Agent · 多语种 PRD 生成

> 把一句模糊的需求，变成中日英三语对齐的标准 PRD。
> Turn a vague one-liner into an aligned zh / ja / en PRD — before development starts.

[![Status](https://img.shields.io/badge/status-v0.3-blue)]() [![Python](https://img.shields.io/badge/python-3.11+-blue)]() [![Next.js](https://img.shields.io/badge/Next.js-14-black)]() [![Tests](https://img.shields.io/badge/tests-65%20passed-brightgreen)]() [![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

[English](README.en.md) · [日本語](README.ja.md)

---

## 这是什么

跨国产品协作里最贵的一段损耗发生在**需求交接**：总部用一句话描述需求，日本市场团队按自己的理解开发，等到验收才发现两边想的不是一回事。

**Spec Agent** 是一条三阶段多智能体流水线，把这段模糊描述变成结构化、可验收、三语对齐的 PRD：

```
一句模糊需求 → 需求澄清 → 结构化 PRD（中文/日本語/English）→ 质量校验（不通过则回注迭代）
```

它不是一个"让 LLM 写文档"的 prompt 包装，而是围绕**可交付**做了三件上游项目基本不做的事：

| 能力 | 说明 |
| --- | --- |
| 🌐 **多语种对齐输出** | 一次输入产出 zh/ja/en 三份 PRD，用户故事编号一一对应，不是逐字翻译而是本地化表达 |
| 📒 **术语对照表** | 关键术语三语对照（如「验收标准 / Acceptance Criteria / 受入基準」），从源头消灭术语漂移 |
| ✅ **可判定的校验语义** | 确定性结构校验（缺语种、故事数量不一致、缺 AC…）+ LLM 语义校验（INVEST、可测试性、三语等价） |
| 📐 **三语一致性打分** | 0~100 的量化一致性分数：故事编号 / 数字阈值 / AC 数量 / 技术词 + 回译或跨语言向量，低分条目按风险排序供人工复核 |
| 🔁 **校验回注迭代** | 校验不通过 → 问题回注 Structurer 重写；问题数不再下降时自动止损，不做无意义的 token 燃烧 |
| 🧭 **假设显式化** | 信息缺失时不偷偷替需求方拍板：补全的部分标为「显式假设」，必须确认的进 Open Questions |
| 🚫 **反占位符** | 提示词层面禁止 `X%` / `TBD` / `待定`，指标必须给出阈值 + 测量口径，否则进 Open Questions |
| 🐳 **零配置可跑** | 没有 LLM API key 时自动降级为确定性 Mock 模式，clone 下来就能看到完整链路 |

---

## 效果示例

输入（一句真实风格的需求原话）：

> 日本市场想要一个能让老年用户更容易用的支付流程，现在很多高龄用户走到支付页就放弃了，大概下个季度要上线，最好也能覆盖我们自己的 App 和网页端。

运行 `python scripts/smoke.py --sample jp-senior-payment` 后（真实模型 `deepseek-chat`，2 轮迭代，三语一致性 97 分）得到的三语 PRD 节选：

```markdown
## 成功指标
- 高龄用户支付页放弃率从当前基线降低 20%（相对值），测量口径：支付页埋点漏斗，对比优化前后各一个完整自然月的数据。
- 高龄用户支付流程平均完成时间缩短至 3 分钟以内，测量口径：进入支付页到支付成功的时间戳差值，取中位数。

### US-1 · 作为日本市场的高龄用户，我可以使用大字体和高对比度的支付界面，以便更轻松地阅读支付信息并完成支付。
- 验收标准：支付页字体大小至少为 18pt，且提供字体放大切换开关，切换后至少 24pt。
- 验收标准：支付页文字与背景对比度至少为 4.5:1，符合 WCAG 2.1 AA 标准。

## 术语对照表
| zh | en | ja | note |
| --- | --- | --- | --- |
| 验收标准 | Acceptance Criteria | 受入基準 | 可逐条判定通过/不通过 |
```

完整成品（三语，均由真实模型生成，未经人工编辑）：

- [docs/example-output.zh.md](docs/example-output.zh.md)
- [docs/example-output.ja.md](docs/example-output.ja.md)
- [docs/example-output.en.md](docs/example-output.en.md)
- [docs/example-consistency.json](docs/example-consistency.json) —— 同一次运行的一致性评分（整体 97.1，中文↔日本語 98.6，中文↔English 98.1，无低分条目）

界面截图（见 [docs/screenshots](docs/screenshots)）：

![输入与PRD](docs/screenshots/02-progress-and-prd.png)

---

## 架构

```
                     ┌──────────────────────────────────────────────┐
 模糊需求（任意语言） │  Clarifier  需求澄清                          │
 ───────────────────▶│  goal / target_users / success_metrics       │
                     │  scope / assumptions / open_questions        │
                     └───────────────────┬──────────────────────────┘
                                         ▼
                     ┌──────────────────────────────────────────────┐
                     │  Structurer  PRD 结构化（zh / ja / en）        │
                     │  用户故事 + 可测试 AC + 术语对照表              │
                     └───────────────────┬──────────────────────────┘
                                         ▼
                     ┌──────────────────────────────────────────────┐
                     │  Validator  质量校验                          │
                     │  ① 确定性结构校验（代码，零成本）              │
                     │  ② LLM 语义校验（INVEST / 可测试性 / 三语等价） │
                     └───────────────────┬──────────────────────────┘
                            有 blocker？ │
                     ┌───────────────────┴──────────────────────────┐
                     │ 是 → 问题回注 Structurer，最多 N 轮            │
                     │ 否 → 交付 PRD + 评审清单（major/minor）        │
                     └──────────────────────────────────────────────┘
```

### 校验语义（为什么它不会"永远打回"）

让 LLM 当评审，最常见的结果是每轮都能挑出问题、永远不通过。Spec Agent 把判定拆成两层：

| 严重度 | 含义 | 是否阻塞交付 |
| --- | --- | --- |
| `blocker` | 不修就不能开发：缺某个语种的整份 PRD、没有用户故事、故事没有 AC、各语种故事数量/编号矛盾、某语种凭空多出或漏掉需求 | **是** —— 回注下一轮 |
| `major` | 影响理解或验收判定，但可以带清单进评审：AC 缺阈值、故事过大、指标是占位符、关键假设未标注 | 否 —— 进评审清单 |
| `minor` | 表述、覆盖度、可读性建议 | 否 |

流水线在一轮内同时产出「PRD」和「评审清单」；只有当问题数**严格下降**时才继续下一轮，否则提前止损（`stalled = true`），把剩余问题交给人。
没有 blocker 时最多再迭代一次——后续轮次多半只是措辞抖动，而且模型抖动可能让某一轮变差，因此**交付的是所有轮次里排序最优的那一轮**（无 blocker 优先，其次看加权分）。

---

## 三语一致性量化评分

"三个语种说的是不是同一件事"可以被量化。每份 PRD 都带一个 0~100 的一致性分数，并把需要人工复核的条目按风险排序列出来。

**评分模型**（每对语种，权重合计 100%）：

| 信号 | 权重 | 判据 |
| --- | --- | --- |
| 故事编号覆盖 | 25% | 各语种故事编号是否一一对应（漏译 / 多译直接扣分） |
| 数字阈值一致 | 25% | 把同一条 AC 对齐后逐条比数字：18pt vs 24pt、3 步 vs 4 步…（同一条 AC 数字完全冲突时压到 55 分以下送人工） |
| AC 数量对齐 | 15% | 每条故事的验收标准条数是否一致 |
| 技术词保留 | 15% | WCAG 2.1 / AA / TTS / PayPay 这类词不该在某语种里消失 |
| 语义重合 | 20% | 回译或跨语言向量与基准语种的相似度（见下） |

**三种方法**（`CONSISTENCY_METHOD`）：

| 方法 | 额外成本 | 说明 |
| --- | --- | --- |
| `structural`（默认） | 0 | 只用确定性信号（编号 / 数字 / AC / 技术词），完全离线、可复现 |
| `backtranslate` | 每轮 1~N 次模型调用 | 把非基准语种 PRD 回译到基准语言后比对词面重合；**长 PRD 自动分片，分片失败自动二分重试，回译语言不符会被忽略** |
| `embeddings` | 每轮 1 次向量调用 | 用跨语言向量相似度替代回译（需要 `/embeddings` 接口） |

**判定规则**：整体或单条故事低于 `CONSISTENCY_BLOCKER_SCORE`（默认 50）→ blocker（触发下一轮修正）；低于 `CONSISTENCY_MIN_SCORE`（默认 75）→ major（进评审清单）；术语在正文里的出现率 < 60% → minor。
**语义硬否决**：回译/向量与基准语种几乎无重合（原始相似度 < 0.30）时，不论结构多整齐都判为严重漂移。

> 阈值是用真实模型样本校准的经验值：忠实回译的原始 Dice 落在 0.50~0.75（样本见 [docs/HANDOVER.md](docs/HANDOVER.md)），因此 0.50 以上视为忠实。
> 它不是"语义等价"的证明，作用是**给人工复核排序**——把最可能出问题的故事排到最前面，并附上基准语种与回译结果的对照文本。
> 确定性信号（编号 / 数字 / AC / 技术词）才是精确判据，语义信号只占 20%。
>
> 输出示例：[docs/example-consistency.json](docs/example-consistency.json)

![三语一致性面板](docs/screenshots/04-consistency.png)

---

## 快速开始

### 1. Docker（推荐）

```bash
git clone https://github.com/shiyuanyeming-hub/spec-agent.git
cd spec-agent

cp backend/.env.example backend/.env    # 填入 LLM_API_KEY（可留空 → Mock 模式）
docker compose up --build

open http://localhost:3000
```

### 2. 本地开发

后端（Python 3.11+）：

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env          # LLM_API_KEY 留空即为 Mock 模式
uvicorn app.main:app --reload --port 8000
```

前端（Node 18+）：

```bash
cd frontend
npm install
npm run dev                   # http://localhost:3000，/api/* 自动代理到 :8000
```

命令行跑一遍完整流水线：

```bash
cd backend
python scripts/smoke.py --sample jp-senior-payment            # 内置示例
python scripts/smoke.py "让客服系统支持批量导出季度报表" --langs zh,en --out /tmp/prd.md
```

---

## LLM 配置

兼容任何 OpenAI 风格的 `/chat/completions` 接口（OpenAI、DeepSeek、Kimi、Ollama、vLLM…）。

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `LLM_API_KEY` | 空 | **留空即自动进入 Mock 模式**（确定性输出，不联网，可跑通全流程） |
| `LLM_BASE_URL` | `https://api.deepseek.com/v1` | OpenAI 兼容 base url |
| `LLM_MODEL` | `deepseek-chat` | 模型名 |
| `LLM_PROVIDER` | 自动 | `openai` / `fake`；留空时按是否有 key 自动判定 |
| `LLM_TEMPERATURE` | `0.2` | 采样温度 |
| `LLM_TIMEOUT_SECONDS` | `120` | 单次请求超时 |
| `LLM_MAX_RETRIES` | `3` | 失败重试次数（指数退避） |
| `MAX_VALIDATION_ROUNDS` | `3` | 最多校验轮次；无 blocker 时只会再迭代 1 次，**设为 1 可压到 1 轮** |
| `CONSISTENCY_METHOD` | `structural` | 一致性评分方法：`structural` / `backtranslate` / `embeddings` / `off` |
| `CONSISTENCY_MIN_SCORE` | `75` | 低于此分记为 major（进评审清单） |
| `CONSISTENCY_BLOCKER_SCORE` | `50` | 低于此分记为 blocker（触发下一轮修正） |
| `BACKTRANSLATE_CHUNK_CHARS` | `4000` | 回译请求的分片大小（越小越不容易被截断） |
| `EMBEDDINGS_BASE_URL` / `EMBEDDINGS_API_KEY` / `EMBEDDINGS_MODEL` | 跟随 LLM 配置 / `text-embedding-3-small` | 仅 `embeddings` 方法需要 |
| `LLM_MAX_TOKENS` | 服务端默认 | 输出被截断（JSON 解析失败）时显式调大，例如 `8192` |
| `MAX_INPUT_CHARS` | `4000` | 输入长度上限 |
| `CORS_ORIGINS` | `localhost:3000,...` | 允许的前端来源 |

> 真实模型一轮约 30–90 秒（结构化 + 校验各一次调用，`backtranslate` 方法还会多做 1~N 次回译调用）。
> 默认最多 3 轮，但**无 blocker 时只再迭代一次**，问题数不再下降也会提前结束，并交付排序最优的那一轮。
> 追求速度可以设 `MAX_VALIDATION_ROUNDS=1`，或把 `CONSISTENCY_METHOD` 设成默认的 `structural`（零额外成本）。

---

## API

### `POST /api/generate`

```bash
curl -s http://localhost:8000/api/generate \
  -H 'Content-Type: application/json' \
  -d '{"raw_text": "日本市场想要一个对老年人友好的支付流程", "target_langs": ["zh", "ja", "en"]}'
```

响应结构（节选）：

```jsonc
{
  "prd": { "product_name": "...", "target_langs": ["zh","ja","en"], "docs": { "zh": {...}, "ja": {...}, "en": {...} } },
  "glossary": [{ "term_zh": "...", "term_en": "...", "term_ja": "...", "note": "..." }],
  "markdown": { "zh": "# ...", "ja": "# ...", "en": "# ..." },
  "clarifications": { "goal": "...", "success_metrics": [...], "assumptions": [...], "open_questions": [...] },
  "consistency": {
    "method": "backtranslate",              // structural | backtranslate | embeddings
    "pivot": "zh",
    "overall": 96.4,                        // 0~100
    "terminology_coverage": 0.89,
    "pairs": [{ "lang": "ja", "score": 92.2, "components": { "ids": 1.0, "numeric": 1.0, "entity": 1.0, "semantic": 0.61 } }],
    "divergences": [{ "lang": "en", "story_id": "US-2", "score": 62.0, "reason": "同一条验收标准的数字阈值不一致：…" }]
  },
  "validation": {
    "passed": true,
    "status": "needs_review",              // passed | needs_review | blocked
    "consistency_score": 96.4,
    "counts": { "blocker": 0, "major": 3, "minor": 1 },
    "issues": [{ "severity": "major", "category": "testability", "message": "...", "suggestion": "..." }]
  },
  "rounds_used": 2,
  "status": "needs_review",
  "stalled": true,                          // 问题数不再下降 → 提前止损
  "provider": "openai",
  "trace": [{ "stage": "validator", "status": "needs_review", "round": 2, "detail": "..." }]
}
```

### `POST /api/generate/stream`（SSE）

逐阶段推送进度，适合长耗时循环的实时展示。事件类型：`stage`（每阶段开始/结束）、`result`（最终结果）、`error`。

```
event: stage
data: {"stage":"structurer","label":"PRD 结构化","status":"start","round":1,...}

event: stage
data: {"stage":"validator","label":"质量校验","status":"needs_review","round":1,"detail":"..."}
```

### 其他

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/health` | 健康检查 + 当前 provider |
| `GET` | `/api/meta` | 配置、支持语种、内置示例（前端"试试示例"用它） |
| `GET` | `/docs` | FastAPI 自动生成的交互式 API 文档 |

---

## 目录结构

```
spec-agent/
├── backend/
│   ├── app/
│   │   ├── agents/           # Clarifier（澄清）/ Structurer（结构化）/ Validator（校验）
│   │   ├── checks.py         # 确定性结构校验（不花 token 的那一半验收）
│   │   ├── llm.py            # OpenAI 兼容客户端 + 确定性 Mock + JSON 容错解析
│   │   ├── pipeline.py       # 唯一编排入口：事件流驱动同步接口与 SSE
│   │   ├── render.py         # PRD → Markdown
│   │   ├── schemas.py        # 结构化输出的 Pydantic Schema（同时当 JSON Schema 提示词用）
│   │   └── samples.py        # 内置示例
│   ├── scripts/smoke.py      # 命令行冒烟：跑流水线、存 Markdown
│   └── tests/                # pytest（43 项，默认 Mock 模式，无需联网）
├── frontend/                 # Next.js 14 App Router（SSE 实时进度 + 三语 Tab + 术语表 + 校验报告）
├── docs/                     # 交接文档、三语示例输出、截图
└── docker-compose.yml
```

---

## 测试与质量

```bash
cd backend
pytest -q          # 43 passed（Mock 模式，不联网、不花钱）
ruff check app tests
```

覆盖范围：LLM JSON 容错/截断抢救/重试、Mock 确定性、确定性结构校验（缺语种/故事数量/AC/术语表）、
校验语义（blocker 阻塞、major 只进清单）、迭代与止损（收敛 / 达上限 / 无改善提前停 / 无 blocker 只再迭代一次 / 交付最优轮）、
三语一致性（编号覆盖、AC 数量、数字阈值冲突、技术词保留、术语覆盖率、语义硬否决、回译语言校验、分片与二分重试、向量方法）、
API 校验与错误码、SSE 事件序列、Markdown 渲染。

CI 定义示例见 [`docs/ci-workflow.example.yml`](docs/ci-workflow.example.yml)：复制到 `.github/workflows/ci.yml` 即可启用
（跑 ruff + pytest + 前端构建；测试全程 Mock 模式，不需要任何密钥）。

---

## Roadmap

- [x] **v0.1** 三阶段流水线骨架 + PRD 模板 + Docker Compose
- [x] **v0.2** 接入 LLM（OpenAI 兼容 + Mock 降级）、三语 PRD 与术语对照表、可判定校验语义与迭代止损、SSE 流式进度、Next.js 前端、与真实模型的三语示例输出
- [x] **v0.3** 三语一致性量化评分：确定性信号（编号 / 数字阈值 / AC 数量 / 技术词）+ 回译或跨语言向量，低分条目按风险排序并附对照文本；长 PRD 分片回译、失败二分重试、回译语言校验
- [ ] **v0.4** 与 [VoC Agent](https://github.com/shiyuanyeming-hub/voc-agent) 联动：用户评论痛点 → 需求草稿 → PRD
- [ ] **v0.5** PRD 版本 diff（需求变更追踪）与 Confluence / Notion / Jira 导出
- [ ] **v0.6** 术语表持久化与团队级术语库（跨需求复用）

---

## 开源依据与差异化

本项目刻意不重复造轮子，调研并核实过两条上游路线：

- **[MetaGPT](https://github.com/FoundationAgents/MetaGPT)**（MIT，活跃）：`Code = SOP(Team)`，内置 PM/架构师/工程师角色，输入一行需求产出用户故事与需求文档——与"模糊需求 → 标准 PRD"同构。Spec Agent 采用同样"角色分工 + SOP"的思路，但把编排收敛成可测试的确定性事件流，便于服务化与回注迭代。
- **[agentic_prd](https://github.com/nanagajui/agentic_prd)**（crewAI）：体量小、角色分工（PM/PO/Designer/SME/QA）值得借鉴，但仅 CLI、单语言。

它们都没有解决的问题，正是本项目的定位：**中日英三语对齐 + 术语对照 + 三语一致性校验 + 可判定放行语义**。

---

## 与 VoC Agent 的关系

同系列项目 [VoC Agent](https://github.com/shiyuanyeming-hub/voc-agent) 回答"用户说了什么"（评论 → 痛点洞察），Spec Agent 回答"团队要做什么"（需求 → 标准 PRD）。两者拼起来覆盖「用户声音 → 开发交付」的完整链路。

## License

MIT © 2026 shiyuanyeming-hub
