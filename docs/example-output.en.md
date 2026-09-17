# Payment Flow Optimization for Older Adult Users PRD (Japan Market)

> **Source Requirement**：日本市场想要一个能让老年用户更容易用的支付流程，现在很多高龄用户走到支付页就放弃了，大概下个季度要上线，最好也能覆盖我们自己的 App 和网页端。

## Background
Older adult users (65+) in the Japan market have a high abandonment rate on the payment page, and the current baseline needs to be obtained through tracking funnels. Optimize the payment flow on our own app and web to reduce abandonment and improve completion by simplifying the interface, enlarging fonts, reducing steps, and adding guidance. Target launch by the end of next quarter, covering our own app and web.

## Goal
Optimize the payment flow for older adult users in the Japan market to reduce payment page abandonment, improve payment completion, and launch by the end of next quarter covering our own app and web. Specific quantitative goals: reduce payment page abandonment rate for older adult users by 20% relative to baseline; increase payment completion rate to 70%; reduce average payment flow completion time to under 3 minutes; reduce payment-related customer support ticket volume by 15%. Baseline acquisition: use payment page tracking funnel, compare one full calendar month before and after optimization, with user age identified via account profile or survey. If baseline cannot be obtained, add tracking first and establish baseline before launch.

## Success Metrics
- 高龄用户支付页放弃率从当前基线降低20%（相对值），测量口径：支付页埋点漏斗，对比优化前后各一个完整自然月的数据，用户年龄通过账户资料或问卷标识。
- 高龄用户支付完成率提升至70%，测量口径：支付成功事件数除以进入支付页事件数，按用户年龄分组统计。
- 高龄用户支付流程平均完成时间缩短至3分钟以内，测量口径：从进入支付页到支付成功的时间戳差值，取中位数。
- 高龄用户支付相关客服工单量下降15%，测量口径：客服系统中标记为支付问题的工单数，按用户年龄分组。

## Stated Assumptions
- 假设高龄用户指65岁及以上，具体年龄阈值需确认。
- 假设当前支付页放弃率基线可通过现有埋点获取，若无法获取则需先补充埋点。
- 假设优化措施包括但不限于：大字体、高对比度、简化步骤、语音辅助、进度指示。
- 假设下个季度上线指自然季度末前，具体日期需确认。
- 假设自有App和网页端使用同一套支付流程逻辑，可复用优化方案。

## User Stories

### US-1 · As an older adult user in the Japan market, I can use a payment interface with large fonts and high contrast, so that I can read payment information more easily and complete payment.

- Acceptance Criteria：Payment page font size is at least 18pt, and a font enlargement toggle is provided; after toggling, font size is at least 24pt.
- Acceptance Criteria：Payment page text-to-background contrast ratio is at least 4.5:1, compliant with WCAG 2.1 AA.
- Acceptance Criteria：Large font and high contrast modes are effective on iOS and Android own app and web.

### US-2 · As an older adult user in the Japan market, I can complete payment with simplified steps, so that I can reduce operational burden and complete payment quickly.

- Acceptance Criteria：Payment flow steps are reduced by at least 2 steps from the current baseline, and total steps do not exceed 4.
- Acceptance Criteria：Each step retains only one primary action button (the button with the highest visual hierarchy in the main action area), and no more than one secondary action (text link or secondary button).
- Acceptance Criteria：Payment flow step count is consistent between own app and web.

### US-3 · As an older adult user in the Japan market, I can use Japanese voice guidance to assist with payment operations, so that I can understand the payment flow even with declining vision or cognitive ability.

- Acceptance Criteria：Voice guidance supports Japanese, and based on TTS engine output parameters, speech rate is set to no more than 180 Japanese characters per minute.
- Acceptance Criteria：Voice guidance automatically plays at each step of the payment flow, and a replay button is provided.
- Acceptance Criteria：Voice guidance volume is adjustable, and default volume is at least 50% of device maximum volume.

### US-4 · As an older adult user in the Japan market, I can see a clear progress indicator, so that I can understand the current payment progress and remaining steps.

- Acceptance Criteria：Payment page displays a progress indicator showing current step and total steps (e.g., "Step 2/4").
- Acceptance Criteria：Progress indicator is visible on both own app and web, with font size at least 16pt.
- Acceptance Criteria：Progress indicator updates in real time after each payment operation.

### US-5 · As an older adult user in the Japan market, I can get a consistent payment experience on own app and web, so that I can complete payment smoothly on either channel.

- Acceptance Criteria：After the same account enters the payment page on own app and web, the payment completion rate difference is no more than 5 percentage points. Statistical scope: calculated per calendar month, only for the older adult user group, sample size at least 1000, and the payment completion rate difference is an absolute value.
- Acceptance Criteria：Payment flow steps, interface layout, and guidance text are consistent between own app and web.
- Acceptance Criteria：Average payment flow completion time difference between own app and web is no more than 30 seconds.

## Functional Requirements
- Payment page supports large font mode, font size at least 18pt, switchable to 24pt or more.
- Payment page supports high contrast mode, text-to-background contrast ratio at least 4.5:1.
- Payment flow steps reduced to no more than 4 steps, with only one primary action button per step.
- Integrate Japanese TTS engine to provide voice guidance, speech rate no more than 180 Japanese characters per minute.
- Payment page displays progress indicator showing current step and total steps.
- Own app and web use the same payment flow logic to ensure consistency.
- Provide age identification mechanism to identify older adult users via account profile or survey.
- Tracking records events such as payment page entry, payment success, and payment failure to calculate abandonment rate, completion rate, and completion time.

## Non-Functional Requirements
- Payment page load time no more than 3 seconds on 4G network.
- Voice guidance response time no more than 1 second.
- System availability no less than 99.9%.
- Comply with Japanese local accessibility regulations (e.g., JIS X 8341-3) and WCAG 2.1 AA.
- Support Japanese and English interfaces, default Japanese.

## Risks
- The age identification method for older adult users is unconfirmed, which may affect metric grouping and implementation of optimization measures.
- The current payment page abandonment baseline may not be obtainable from existing tracking, requiring additional tracking and potentially delaying launch.
- Whether own app and web use the same payment flow is unconfirmed, and there may be technical limitations.
- Japanese local regulations or accessibility standards are unclear, which may require additional compliance work.
- Budget or resource constraints for optimization measures are unconfirmed, which may affect implementation scope.
- Voice guidance speech rate settings may vary by device or TTS engine, affecting consistency.

## Open Questions
1. What is the specific age definition for older adult users? If determined as 65+, only the identification method (account age, device settings, or survey) needs confirmation.
2. What is the current baseline payment page abandonment rate for older adult users? How to obtain it? If unobtainable, how to establish a baseline?
3. What is the specific deadline for launch next quarter?
4. Do own app and web use the same payment flow? Are there technical limitations?
5. Are there Japanese local regulations or accessibility standards to comply with?
6. Are there budget or resource constraints for optimization measures?
7. How to identify older adult users? Via account age, device settings, or other methods?
8. Are baseline data for success metrics (current abandonment rate, completion rate, completion time, ticket volume) obtainable? If not, how to establish a baseline?
9. Measurement scope for voice guidance speech rate: based on TTS engine output parameters or manual evaluation?

## Glossary

| zh | en | ja | note |
| --- | --- | --- | --- |
| 高龄用户 | Older adult users | 高齢ユーザー | 本项目指日本市场65岁及以上的支付用户；年龄识别方式待确认，见 open_questions。 |
| 支付页放弃率 | Payment page abandonment rate | 支払いページ離脱率 | 进入支付页后未完成支付的会话数除以进入支付页的会话数，按高龄用户分组统计。 |
| 支付完成率 | Payment completion rate | 支払い完了率 | 支付成功事件数除以进入支付页事件数，按高龄用户分组统计。 |
| 支付流程平均完成时间 | Average payment flow completion time | 支払いフロー平均完了時間 | 从进入支付页到支付成功的时间戳差值，取中位数。 |
| 支付相关客服工单量 | Payment-related customer support ticket volume | 支払い関連カスタマーサポートチケット数 | 客服系统中标记为支付问题的工单数，按高龄用户分组统计。 |
| 主要操作 | Primary action | 主要操作 | 视觉层级最高、位于主操作区的按钮，用于推进支付流程。 |
| 次要操作 | Secondary action | 二次操作 | 文字链接或次级按钮，用于返回、取消、查看帮助等非推进支付流程的操作。 |
| 语音提示 | Voice guidance | 音声ガイダンス | 通过TTS引擎输出的日语语音提示，用于辅助高龄用户完成支付。 |
| 进度指示 | Progress indicator | 進捗インジケーター | 显示当前步骤和剩余步骤的视觉元素。 |
| 大字体模式 | Large font mode | 大文字モード | 支付页字体放大至至少18pt，可切换。 |
| 高对比度模式 | High contrast mode | ハイコントラストモード | 支付页文字与背景对比度至少4.5:1，符合WCAG 2.1 AA。 |

<!-- Validation issues fixed in this round: [major/testability] zh/ja/en 三语种 PRD 的 goal 与 background 均未给出可量化的成功指标（如支付页放弃率下降幅度、支付完成率提升幅度），而 open_questions 中却提到「支付相关客服工单量下降15%」等指标，目标与开放问题不一致，无法判定上线是否达成业务目标。 → 修改建议：在 goal 中补充可量化目标，例如「支付页放弃率相对基线下降 X%」「支付完成率提升至 Y%」「支付相关客服工单量下降 15%」，并明确基线获取方式；若基线待定，需在 goal 中标注为待确认并给出占位符说明。；[major/testability] zh/ja/en 三语种 PRD 的 US-3 验收标准「语音提示支持日语，语速不高于每分钟180个日语字符」中，180 字符/分钟是否对应可理解语速缺少依据，且未定义如何测量（合成语音参数、播放速率还是人工评估），难以判定通过/不通过。 → 修改建议：补充测量口径，例如「以 TTS 引擎输出参数为准，语速设置为不超过 180 日语字符/分钟」，或改为可客观测量的指标（如「语速档位不超过 X 档」）。；[major/testability] zh/ja/en 三语种 PRD 的 US-5 验收标准「同一账户在自有App和网页端进入支付页后，支付完成率差异不超过5个百分点」缺少统计口径：未说明统计周期、样本量下限、是否按高龄用户分组，以及差异是绝对值还是相对值，难以判定。 → 修改建议：补充统计口径，例如「按自然月统计，仅统计高龄用户分组，样本量不少于 N，支付完成率差值为绝对值且不超过 5 个百分点」。；[major/testability] zh/ja/en 三语种 PRD 的 US-2 验收标准「每一步只保留一个主要操作按钮，次要操作不超过一个」中，「主要操作」与「次要操作」未定义判定标准，不同评审人可能得出不同结论。 → 修改建议：补充定义，例如「主要操作按钮指视觉层级最高、位于主操作区的按钮；次要操作为文字链接或次级按钮」，或给出具体页面元素清单。；[major/completeness] zh/ja/en 三语种 PRD 的 risks 与 open_questions 均提到高龄用户年龄识别方式未确认，但 glossary 中「高龄用户」注释已写明「本项目指日本市场65岁及以上的支付用户」，二者存在潜在矛盾：若已定义 65 岁及以上，则年龄识别方式与阈值应统一，否则指标分组无法落地。 → 修改建议：统一术语与开放问题：若确定 65 岁及以上，则在 open_questions 中删除「年龄定义」问题，仅保留「识别方式」问题；若未确定，则 glossary 注释应改为待确认，避免前后矛盾。 -->
