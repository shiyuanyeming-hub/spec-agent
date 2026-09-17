# Spec Agent 开发交接文档

> **文档目的**：说明项目定位、开源依据、当前状态与后续路线，供接手开发的同事快速进入。
> **一句话定位**：把模糊的需求描述自动整理为结构化标准 PRD，支持中日英三语对齐输出。
> **当前状态**：⭐ **v0.2 已可用**（真实模型跑通、43 项测试通过、前端可交互、已开源到 GitHub）。
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
2. **三语一致性校验**：Validator 在 INVEST / 可测试性之外，额外检查语种间的语义与结构等价
3. **可判定的放行语义**：blocker 才回注迭代，major/minor 作为评审清单随 PRD 交付（见 §3）
4. **与 VoC Agent 的数据闭环**：同系列项目 [voc-agent](https://github.com/shiyuanyeming-hub/voc-agent) 产出用户痛点洞察 → Spec Agent 转成需求草稿

---

## 2. 当前仓库状态（v0.2）

```
spec-agent/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── clarifier.py      # 澄清：goal/人群/成功指标/范围/假设/待确认问题
│   │   │   ├── structurer.py     # 结构化：多语种 PRD + 术语对照表
│   │   │   └── validator.py      # 校验：INVEST / 可测试性 / 三语等价（含判定语义）
│   │   ├── checks.py             # 确定性结构校验（缺语种、故事数量/编号、AC、术语表）
│   │   ├── llm.py                # OpenAI 兼容客户端 + 确定性 Mock + 容错 JSON 解析 + 重试
│   │   ├── pipeline.py           # 唯一编排入口：事件流（同步 + SSE 共用）
│   │   ├── render.py             # PRD → Markdown（三语标题/小节本地化）
│   │   ├── schemas.py            # 结构化输出的 Pydantic Schema（同时作为 JSON Schema 提示词）
│   │   ├── samples.py            # 内置示例（前端"试试示例"与冒烟脚本共用）
│   │   └── main.py               # FastAPI：/api/generate、/api/generate/stream、/api/meta、/api/health
│   ├── scripts/smoke.py          # 命令行冒烟：跑流水线、打印进度、导出 Markdown
│   └── tests/                    # 43 项 pytest（默认 Mock 模式，不联网、不花钱）
├── frontend/                     # Next.js 14 App Router：SSE 进度、三语 Tab、术语表、校验报告、导出 .md
├── docs/
│   ├── example-output.{zh,ja,en}.md   # 真实模型（deepseek-chat）生成的三语成品，未人工编辑
│   └── screenshots/                    # 界面截图
├── docker-compose.yml            # backend:8000 + frontend:3000（healthcheck + depends_on）
└── .github/workflows/ci.yml      # ruff + pytest + next build
```

### 已完成（v0.1 → v0.2）

- ✅ 接入真实 LLM（OpenAI 兼容：OpenAI / DeepSeek / Ollama / vLLM…），**无 key 时自动降级为确定性 Mock**
- ✅ 三个 Agent 全部真实工作：结构化输出用 Pydantic Schema 约束，输出 JSON 容错解析 + 重试
- ✅ 三语 PRD + 术语对照表 + 每语种 Markdown 导出
- ✅ 校验双轨：确定性结构校验（零 token）+ LLM 语义校验（INVEST / 可测试性 / 三语等价）
- ✅ 校验回注闭环 + **收敛止损**（问题数不再下降即停止，避免烧 token）
- ✅ SSE 流式进度：每阶段开始/结束实时推送；同步接口与流式接口共用一份编排
- ✅ Next.js 前端（零额外依赖，手写 CSS）：输入 → 进度 → 三语 Tab → 术语表 → 校验报告 → 复制/下载
- ✅ 测试与 CI：43 项 pytest + ruff + 前端构建
- ✅ 三语 README（zh / en / ja）

### 明确未做（避免接手人重复调研）

- ❌ 三语一致性的**量化**评分（回译 + embedding 相似度）——当前由 LLM 语义校验定性判断
- ❌ 术语表的持久化与团队级术语库（目前每次生成独立）
- ❌ 与 voc-agent 的实际 API 对接（只做了 README 层面的呼应）
- ❌ PRD 版本 diff / Confluence / Notion / Jira 导出
- ❌ 用户体系、鉴权、并发限流（当前是单租户工具定位）
- ❌ 前端 i18n（界面文案目前为中文，PRD 内容才是多语种）

---

## 3. 关键设计决策（接手人务必先读）

1. **放行语义：blocker 才算阻塞**
   让 LLM 当评审必然"每轮都有问题"。因此 `passed` 只由 `blocker` 决定：
   - `blocker`：缺某语种整份 PRD、无用户故事、故事无 AC、各语种故事数量/编号矛盾、某语种凭空增删需求
   - `major` / `minor`：进"评审清单"随 PRD 一起交付，不阻塞
   - 状态机：`blocked` → `needs_review` → `passed`（见 `validation.status`）

2. **迭代止损**：分数 `3×blocker + major` 不再下降时立即停止（`stalled=true`），把剩余问题交给人。
   上限由 `MAX_VALIDATION_ROUNDS` 控制（默认 3；设为 1 可把真实模型耗时压到 1 轮）。

3. **Mock 优先可跑**：`FakeLLM` 输出结构合法的多语种 PRD，因此测试、CI、没配 key 的演示都能跑通全链路。
   测试里用 `ScriptedValidatorLLM` 之类的子类脚本化"第几轮返回几个 blocker"来验证收敛/止损逻辑。

4. **提示词反占位符**：明确禁止 `X%` / `TBD` / `待定`，指标必须带阈值与测量口径，否则进 Open Questions。
   这是把"看似完整实则不可用"的 PRD 挡在门外的关键（v0.2 实测有效）。

5. **编排只有一处**：`iter_pipeline()` 产出 `("stage", event)` / `("result", result)`，
   `run_pipeline()` 与 SSE 接口都消费它——新增阶段或改事件字段时只需改一处。

---

## 4. 建议开发路线（按优先级）

| 阶段 | 任务 | 说明 |
| --- | --- | --- |
| **P0** | 三语一致性量化分数 | 回译 + embedding 相似度，给出一致性百分比与不一致片段定位 |
| P1 | 术语表持久化 | SQLite/JSON 存储 + 相似项目内复用，前端可编辑后回写 |
| P1 | 需求溯源 | 每个 PRD 字段回指原始输入的片段（voc-agent 同款设计哲学） |
| P2 | 与 voc-agent 联动 | 拉取洞察 → 生成需求草稿 → 自动跑流水线 → 回写 PRD 链接 |
| P2 | PRD 版本 diff | 需求变更追踪；导出 Confluence / Notion / Jira |
| P3 | 前端 i18n + 多用户 | 界面三语、鉴权、限流、审计日志 |

---

## 5. 约定

- 代码风格：Agent 保持 `run()` 单入口 + dataclass 输出；系统提示词放模块常量；Schema 放 `app/schemas.py`
- 提交前必须通过：`cd backend && ruff check app tests scripts && pytest -q`；改前端时 `npm run build`
- 新增 LLM 调用必须走 `app/llm.py` 的 `chat_json()`（保证 Mock 与真实模式行为一致、可测）
- 文档：README 三语同步更新；本文件在里程碑完成后更新
- 原作者：王喆（GitHub: [shiyuanyeming-hub](https://github.com/shiyuanyeming-hub)），同系列仓库 [voc-agent](https://github.com/shiyuanyeming-hub/voc-agent)
