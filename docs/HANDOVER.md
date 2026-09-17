# Spec Agent 开发交接文档

> **文档目的**：说明项目定位、开源依据、当前状态与后续路线，供接手开发的同事快速进入。
> **一句话定位**：把模糊的需求描述自动整理为结构化标准 PRD，支持中日英三语对齐输出，并给出三语一致性量化评分。
> **当前状态**：⭐ **v0.3 已可用**（真实模型跑通、68 项测试通过、前端可交互、已开源到 GitHub）。
> 本文档随开发推进更新；重大架构决策请在 PR 中记录。

---

## 1. 开源依据（已核实）

本项目不做从零造轮子，定位是"顺着成熟开源项目做垂直场景的二次开发"。调研确认的两条技术路线：

### 路线 A（参考主路径）：MetaGPT

| 核实项 | 结果 |
| --- | --- |
| 仓库 | [FoundationAgents/MetaGPT](https://github.com/FoundationAgents/MetaGPT) |
| 热度 | GitHub 多智能体框架头部项目（数万 star） |
| License | **MIT**（可商用、可闭源二次开发） |
| 维护状态 | 活跃（学术背书：AFlow，ICLR 2025 oral） |
| 相关性 | `Code = SOP(Team)`，内置产品经理/架构师/工程师角色，输入一行需求即可产出用户故事与需求文档——与"模糊需求 → 标准 PRD"直接同构 |

**我们的取舍**：保留"角色分工 + SOP"的思路（Clarifier / Structurer / Validator = 澄清 / 结构化 / 评审），
但没有引入 MetaGPT 作为运行时依赖——编排被收敛成 `app/pipeline.py` 里一条可测试的确定性事件流，
同步接口与 SSE 流式接口消费同一份事件，便于服务化、单测与成本控制。

### 路线 B（参考实现）：agentic_prd

| 核实项 | 结果 |
| --- | --- |
| 仓库 | [nanagajui/agentic_prd](https://github.com/nanagajui/agentic_prd) |
| 性质 | 基于 crewAI 的 PRD 生成器（PM / PO / Designer / SME / QA），体量小、易读 |
| 局限 | 仅 CLI、单语言、2025-04 后未更新 |

**借鉴点**：角色分工与"评审角色独立于生成角色"的思路；不采纳其 CLI-only、单语言形态。

### 我们的发散点（= 本项目存在的理由）

1. **中日英三语对齐**：一次输入三语产出，故事编号一一对应，附术语对照表——上游项目均为单语言
2. **三语一致性量化评分**：把"三个语种说的是不是同一件事"变成 0~100 的分数 + 人工复核清单（见 §3）
3. **可判定的放行语义**：blocker 才回注迭代，major/minor 作为评审清单随 PRD 交付（见 §3）
4. **与 VoC Agent 的数据闭环**：同系列项目 [voc-agent](https://github.com/shiyuanyeming-hub/voc-agent) 产出用户痛点洞察 → Spec Agent 转成需求草稿

---

## 2. 当前仓库状态（v0.3）

```
spec-agent/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── clarifier.py      # 澄清：goal/人群/成功指标/范围/假设/待确认问题
│   │   │   ├── structurer.py     # 结构化：多语种 PRD + 术语对照表
│   │   │   └── validator.py      # 校验：INVEST / 可测试性 / 三语等价 + 一致性评分接入
│   │   ├── checks.py             # 确定性结构校验（缺语种、故事数量/编号、AC、术语表）
│   │   ├── consistency.py        # 三语一致性评分：编号/数字/AC/技术词 + 回译 / 向量
│   │   ├── similarity.py         # 确定性相似度：Dice、包含度、数字集合、语种画像、伪嵌入
│   │   ├── embeddings.py         # OpenAI 兼容 /embeddings + 离线确定性伪嵌入
│   │   ├── llm.py                # OpenAI 兼容客户端 + 确定性 Mock + 容错/截断抢救 + 重试
│   │   ├── pipeline.py           # 唯一编排入口：事件流（同步 + SSE 共用）+ 轮次策略
│   │   ├── render.py             # PRD → Markdown（三语标题/小节本地化）
│   │   ├── schemas.py            # 结构化输出的 Pydantic Schema（同时作为 JSON Schema 提示词）
│   │   ├── samples.py            # 内置示例（前端"试试示例"与冒烟脚本共用）
│   │   └── main.py               # FastAPI：/api/generate、/api/generate/stream、/api/meta、/api/health
│   ├── scripts/smoke.py          # 命令行冒烟：跑流水线、打印进度、导出 Markdown
│   └── tests/                    # 68 项 pytest（默认 Mock 模式，不联网、不花钱）
├── frontend/                     # Next.js 14：SSE 进度、三语 Tab、术语表、一致性面板、校验报告、导出 .md
├── docs/
│   ├── example-output.{zh,ja,en}.md    # 真实模型（deepseek-chat）生成的三语成品
│   ├── example-consistency.json        # 同一次运行的一致性评分输出
│   └── screenshots/                    # 界面截图
├── docker-compose.yml
└── (CI 定义见 docs/ci-workflow.example.yml)
```

### 已完成（v0.1 → v0.3）

- ✅ 接入真实 LLM（OpenAI 兼容），**无 key 时自动降级为确定性 Mock**
- ✅ 三语 PRD + 术语对照表 + 每语种 Markdown 导出
- ✅ 校验双轨：确定性结构校验（零 token）+ LLM 语义校验（INVEST / 可测试性 / 三语等价）
- ✅ 校验回注闭环 + 收敛止损 + 无 blocker 只再迭代一次 + **交付最优轮**
- ✅ **三语一致性量化评分**（v0.3 核心）：`structural` / `backtranslate` / `embeddings` 三种方法
- ✅ SSE 流式进度；同步接口与流式接口共用一份编排
- ✅ Next.js 前端（零额外依赖）：输入 → 进度 → 三语 Tab → 术语表 → 一致性面板 → 校验报告 → 复制/下载
- ✅ 测试与 CI：68 项 pytest + ruff + 前端构建
- ✅ 三语 README（zh / en / ja）

### 明确未做（避免接手人重复调研）

- ❌ 三语一致性的**语义等价比对**只有回译/向量两条近似路径，没有人工标注的评测集（阈值是经验校准，见 §3）
- ❌ 术语表的持久化与团队级术语库（目前每次生成独立）
- ❌ 与 voc-agent 的实际 API 对接（只做了 README 层面的呼应）
- ❌ PRD 版本 diff / Confluence / Notion / Jira 导出
- ❌ 用户体系、鉴权、并发限流（当前是单租户工具定位）
- ❌ 前端 i18n（界面文案目前为中文，PRD 内容才是多语种）

---

## 3. 关键设计决策（接手人务必先读）

### 3.1 放行语义：blocker 才算阻塞

让 LLM 当评审必然"每轮都有问题"。因此 `passed` 只由 `blocker` 决定：

- `blocker`：缺某语种整份 PRD、无用户故事、故事无 AC、各语种故事数量/编号矛盾、某语种凭空增删需求、三语一致性严重漂移
- `major` / `minor`：进"评审清单"随 PRD 一起交付，不阻塞
- 状态机：`blocked` → `needs_review` → `passed`（见 `validation.status`）

### 3.2 迭代策略（v0.3 调整）

- 分数 `3×blocker + major` 不再下降 → 立即止损（`stalled=true`）
- **无 blocker 时最多再迭代一次**：后面几轮多半只是措辞抖动，不值得烧 token
- **交付排序最优的一轮**：先看有没有 blocker，再看加权分（模型抖动可能让某一轮更差）

### 3.3 三语一致性评分（v0.3 核心）

权重（缺失维度会重新归一化，因此 structural / backtranslate 的分数可比）：

| 信号 | 权重 | 说明 |
| --- | --- | --- |
| `ids` | 0.25 | 故事编号覆盖（漏译/多译） |
| `numeric` | 0.25 | **同一条 AC 对齐后**逐条比数字（18pt vs 24pt）；完全冲突 → 该故事压到 55 分以下 |
| `ac` | 0.15 | 每条故事的 AC 数量对齐 |
| `entity` | 0.15 | 技术词保留（WCAG / AA / TTS / PayPay…） |
| `semantic` | 0.20 | 回译或跨语言向量相似度 |

- **阈值**：`CONSISTENCY_MIN_SCORE=75`（major）、`CONSISTENCY_BLOCKER_SCORE=50`（blocker）；术语正文出现率 < 60% → minor
- **语义硬否决**：原始相似度 < 0.30（`SEMANTIC_VETO`）→ 该故事压到 40 分并判 blocker
- **校准曲线**：`SEMANTIC_FLOOR=0.30 / SEMANTIC_CEIL=0.50`，把忠实回译的原始相似度映射到 1.0
  **校准依据（真实 deepseek-chat 样本）**：忠实回译的原始 Dice = 0.498 / 0.517 / 0.531 / 0.533 / 0.57 / 0.605 / 0.669 / 0.678 / 0.713 / 0.745
  → 也就是"忠实"下限约 0.50；而"说的是另一件事"的合成样本只有 0.07。换模型后建议用 `scripts/smoke.py` 重新采样校准。
- **回译工程细节**（都是真实跑出来的坑）：
  1. 长 PRD（8 条故事）一次性回译会被 token 上限截断成非法 JSON → 按体积**分片**（`BACKTRANSLATE_CHUNK_CHARS`）
  2. 分片仍失败 → **二分重试**（最多 2 层），把"长输出破损"降级成"多次短输出"
  3. 模型偶尔把原文抄回来（或返回英文）→ **语种校验**（`matches_language`）不通过就丢弃该语种的语义信号并记 note，避免假阳性
  4. 结构化输出被截断时，`llm.salvage_truncated_json` 会救回"最后一个完整元素之前"的内容，而不是整轮失败

### 3.4 其它约定

- **Mock 优先可跑**：`FakeLLM` 输出结构合法的多语种 PRD 与"忠实回译"，因此测试、CI、没配 key 的演示都能跑通全链路
- **提示词反占位符**：禁止 `X%` / `TBD` / `待定`，指标必须带阈值与测量口径，否则进 Open Questions
- **用户故事 3~6 条**：限定首期范围，同时避免输出过长被截断
- **编排只有一处**：`iter_pipeline()` 产出 `("stage", event)` / `("result", result)`，同步与 SSE 都消费它

---

## 4. 建议开发路线（按优先级）

| 阶段 | 任务 | 说明 |
| --- | --- | --- |
| **P0** | 三语一致性评测集 | 人工标注 10~20 组"忠实 / 轻度漂移 / 严重漂移"样本，把阈值从经验值变成可回归的指标 |
| P1 | 术语表持久化 | SQLite/JSON 存储 + 跨需求复用，前端可编辑后回写，并纳入一致性评分 |
| P1 | 需求溯源 | 每个 PRD 字段回指原始输入的片段（voc-agent 同款设计哲学） |
| P2 | 与 voc-agent 联动 | 拉取洞察 → 生成需求草稿 → 自动跑流水线 → 回写 PRD 链接 |
| P2 | PRD 版本 diff | 需求变更追踪（一致性分数随版本变化可对比）；导出 Confluence / Notion / Jira |
| P3 | 前端 i18n + 多用户 | 界面三语、鉴权、限流、审计日志 |

---

## 5. 约定

- 代码风格：Agent 保持 `run()` 单入口 + dataclass 输出；系统提示词放模块常量；Schema 放 `app/schemas.py`
- 提交前必须通过：`cd backend && ruff check app tests scripts && pytest -q`；改前端时 `npm run build`
- 新增 LLM 调用必须走 `app/llm.py` 的 `chat_json()`（保证 Mock 与真实模式行为一致、可测）
- 新增评分维度：改 `consistency.py` 的 `WEIGHTS` + 在 `tests/test_consistency.py` 里加"应该扣分 / 不应该扣分"两侧用例
- 文档：README 三语同步更新；本文件在里程碑完成后更新
- 原作者：王喆（GitHub: [shiyuanyeming-hub](https://github.com/shiyuanyeming-hub)），同系列仓库 [voc-agent](https://github.com/shiyuanyeming-hub/voc-agent)
