# Spec Agent 开发交接文档

> **文档目的**：本仓库是 Spec Agent 项目的**起步骨架**（v0.1），由前一开发者（王喆）搭建并完成首次 commit。本文档写给接手开发的同事，说明项目定位、开源依据、当前状态与后续路线。
>
> **一句话定位**：基于成熟开源多智能体框架，把模糊需求描述自动整理为结构化标准 PRD，支持中日英三语输出。
>
> **当前状态**：⭐ **本仓库尚未 push 到 GitHub**（本地 git 已 init + 1 个 commit）。以下文档中涉及的所有开源项目均已核实存在且可用。

---

## 1. 开源依据（已核实，接手人可放心在此基础上发散）

本项目**不是从零造轮子**，定位是"顺着成熟开源项目做垂直场景的二次开发"。经调研确认了两条可选的技术路线：

### 路线 A（推荐主路径）：MetaGPT —— 成熟的多智能体框架

| 核实项 | 结果 |
|---|---|
| 仓库 | [FoundationAgents/MetaGPT](https://github.com/FoundationAgents/MetaGPT) |
| 热度 | 数万 star 级别（GitHub 多智能体框架头部项目） |
| License | **MIT**（可商用、可闭源二次开发，无传染性风险） |
| 维护状态 | **活跃**（最新提交 2026-01，2025 年持续更新；学术背书：AFlow 论文 ICLR 2025 oral） |
| 与本项目的相关性 | 核心理念 `Code = SOP(Team)`，内置"产品经理/架构师/工程师"角色，输入一行需求即可产出**用户故事、竞品分析、需求文档**——与我们"模糊需求 → 标准 PRD"的目标直接同构 |

### 路线 B（参考实现）：agentic_prd —— crewAI 的 PRD 生成器

| 核实项 | 结果 |
|---|---|
| 仓库 | [nanagajui/agentic_prd](https://github.com/nanagajui/agentic_prd) |
| 性质 | 基于 crewAI 的 PRD 生成器（角色：PM / PO / Designer / SME / QA），**体量小、代码好读**，适合当"怎么用通用框架做 PRD 生成"的参考实现 |
| License | 有 LICENSE 文件（接手时确认具体协议） |
| 局限 | 仅 CLI、单语言、社区小（2025-04 后未更新），不适合直接作为基座，但角色分工设计值得借鉴 |

### 我们的发散点（= 本项目存在的理由）

上游项目解决的是"从 0 到 1 生成一份 PRD"，我们聚焦它们**没有做**的垂直场景：

1. **中日英三语对齐**：一次输入，三语 PRD 同步产出 + 术语对照表——跨国团队（总部 ↔ 日本市场）的需求传递是真实痛点，上游项目均为单语言
2. **三语一致性校验**：Validator Agent 不仅查 INVEST/可测试性，还检查三语版本语义是否等价
3. **与 VoC Agent 的数据闭环**：同系列项目 [voc-agent](https://github.com/shiyuanyeming-hub/voc-agent)（已开源）产出用户痛点洞察 → Spec Agent 将其转化为需求草稿，形成"用户声音 → 开发交付"的完整链路

## 2. 当前仓库状态（接手人从这里开始）

### 已有内容（v0.1，冒烟测试通过）

```
spec-agent/
├── backend/
│   ├── app/main.py           # FastAPI 入口：POST /api/generate、GET /api/health
│   ├── app/pipeline.py       # 流水线编排：Clarifier → Structurer → Validator，
│   │                         #   Validator 不通过回注 Structurer，最多 3 轮
│   └── app/agents/
│       ├── clarifier.py      # 需求澄清（骨架，LLM 接入点见 TODO(v0.2)）
│       ├── structurer.py     # PRD 结构化（骨架）
│       └── validator.py      # INVEST/可测试性校验（骨架）
├── frontend/                 # Next.js 占位（package.json + Dockerfile，未初始化）
├── docker-compose.yml        # backend:8000 + frontend:3000
├── README.md                 # 对外门面：双语说明/架构图/示例/Roadmap（已可展示）
└── .env.example              # LLM API 配置模板（OpenAI 兼容接口）
```

- 冒烟测试：`cd backend && python -c "from app.pipeline import run_pipeline; ..."` 可端到端跑通（骨架阶段 Validator 必然打回空 PRD，属预期）
- 三个 Agent 内部的 `TODO(v0.2)` 注释标记了 LLM 接入点

### 明确未做（避免接手人重复调研）

- ❌ 未接 LLM（三个 Agent 的 `_SYSTEM_PROMPT` 已写好，只差调用 OpenAI 兼容接口 + JSON 解析）
- ❌ 未 push GitHub（本地 1 commit：`v0.1: multi-agent pipeline skeleton`）
- ❌ 前端未初始化（需 `npx create-next-app` 或直接复用 voc-agent 前端改皮）
- ❌ 未做多语言一致性校验（这是我们的核心发散点，见路线图）

## 3. 建议开发路线（按优先级）

| 阶段 | 任务 | 说明 |
|---|---|---|
| **P0（先跑通）** | 接入 LLM，让三 Agent 真正工作 | 用 MetaGPT 的 Role/Action 抽象**或**直接 OpenAI SDK 皆可——如果选 MetaGPT 路线，建议把现有骨架作为 FastAPI 服务层保留，MetaGPT 作为 Agent 执行层引入 |
| P0 | GitHub 建仓 push | README/LICENSE/commit 已就绪 |
| P1 | 中日英三语输出 + 术语对照表 | 本项目核心差异点，`target_langs` 参数已在 API 中预留 |
| P1 | Validator 回注循环的真实闭环 | 现有 `pipeline.py` 已实现轮次控制，需补 issues 解析 |
| P2 | 三语一致性校验（核心发散点） | 方案参考：对三语 PRD 各自回译后比对，或用 embedding 相似度 |
| P2 | 前端（Next.js + SSE 流式展示各 Agent 进度） | 可参考 voc-agent 的实现 |
| P3 | 与 voc-agent 联动：痛点 → 需求草稿 | 两个仓库 API 对接即可 |

## 4. 联系与约定

- 原作者：王喆（GitHub: shiyuanyeming-hub），voc-agent 仓库同属此账号，可参考其代码风格
- 代码风格：Agent 类保持 `run()` 单入口 + dataclass 输出，系统提示词放类常量 `_SYSTEM_PROMPT`
- 本文档随开发推进更新；重大架构决策（如是否引入 MetaGPT 作为执行层）请在 PR 中记录
