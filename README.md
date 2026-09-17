# Spec Agent · 需求文档生成助手

> 把模糊的需求描述，变成跨国团队都能对齐的标准 PRD。
> Turn vague requirements into structured PRDs that global teams can align on.

[![Status](https://img.shields.io/badge/status-v0.1--WIP-orange)]() [![Python](https://img.shields.io/badge/python-3.11+-blue)]() [![License](https://img.shields.io/badge/license-MIT-green)]()

## 这是什么 / What is this

跨国产品协作中最常见的损耗：中国总部和海外市场团队对同一段需求描述的理解不一致。**Spec Agent** 用多智能体流水线把一段模糊的需求描述自动整理为结构化标准 PRD，支持中日英三语输出，在需求进入开发前消灭理解偏差。

Cross-team product collaboration loses the most at requirement handoff: headquarters and local market teams read the same vague one-liner differently. **Spec Agent** is a multi-agent pipeline that turns a vague requirement into a structured PRD — with zh/ja/en output — killing misalignment before development starts.

## 核心特性 / Key Features

- 🔁 **三阶段流水线**：需求澄清（Clarifier）→ 结构化（Structurer）→ 校验（Validator），每个 Agent 职责单一、可独立替换
- 🌐 **中日英三语 PRD 输出**：一次输入，三语对齐产出，附术语对照
- 📋 **标准 PRD 结构**：背景 / 目标 / 用户故事 / 功能需求 / 非功能需求 / 验收标准 / 风险项 / Open Questions
- ✅ **校验 Agent 把关**：检查用户故事 INVEST 原则、验收标准可测试性，输出修改建议
- 🔍 **全程可追溯**：每个 PRD 字段可回溯到原始输入的具体表述（与 VoC Agent 同款设计哲学）
- 🐳 **Docker Compose 一键部署**

## 架构 / Architecture

```
用户输入（任意语言的模糊需求）
        │
        ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Clarifier   │ → │  Structurer  │ → │  Validator   │
│  需求澄清     │    │  结构化为PRD  │    │  质量校验     │
└─────────────┘    └─────────────┘    └─────────────┘
        │                  │                  │
        └──────────────────┴──────────────────┘
                           ▼
              结构化 PRD（zh / ja / en）+ 校验报告
```

- **Clarifier**：识别缺失信息（目标用户？成功指标？范围边界？），生成澄清问题或基于合理假设补全（假设会显式标注）
- **Structurer**：将澄清后的需求映射到标准 PRD 模板，拆分用户故事（Epic → Story → AC）
- **Validator**：按 INVEST 原则与可测试性检查每个故事，不通过则回注 Structurer 迭代（最多 N 轮）

## 快速开始 / Quick Start

```bash
# 1. 克隆
git clone https://github.com/shiyuanyeming-hub/spec-agent.git
cd spec-agent

# 2. 配置
cp backend/.env.example backend/.env   # 填入 LLM API key（兼容 OpenAI 接口）

# 3. 一键启动
docker compose up --build

# 4. 打开前端
open http://localhost:3000
```

不使用 Docker：

```bash
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload          # API at :8000
cd frontend && npm install && npm run dev   # Web at :3000
```

## 使用示例 / Example

**输入**（一段典型的跨国需求原话）：

> 日本市场想要一个能让老年用户更容易用的支付流程，大概下个季度要。

**输出**（节选）：

```markdown
# PRD: 银发用户友好支付流程（日本市场）
## 背景
日本支付页面现有流程对高龄用户存在认知负担…
## 用户故事
US-1: 作为 65 岁以上的用户，我可以在不缩放的情况下
      看清所有支付按钮，以便快速完成支付。
      AC1: 主按钮字号 >= 18pt（可测试 ✓）
      AC2: 支付步骤 <= 3 步
## Open Questions
- 是否覆盖 PayPay / 乐天 Pay 等本地支付方式？（需与本地 GTM 确认）
```

## Roadmap

- [x] v0.1 三阶段流水线骨架 + 基础 PRD 模板
- [ ] v0.2 多语言输出（ja/en）与术语对照表
- [ ] v0.3 与 VoC Agent 联动：用户评论痛点 → 自动生成需求草稿
- [ ] v0.4 历史版本 diff（需求变更追踪）

## 与 VoC Agent 的关系

同系列项目：[VoC Agent](https://github.com/shiyuanyeming-hub/voc-agent) 解决"用户说了什么"（评论 → 洞察），Spec Agent 解决"团队要做什么"（洞察/需求 → 标准 PRD），二者共同覆盖从用户声音到开发交付的中间链路。

## License

MIT
