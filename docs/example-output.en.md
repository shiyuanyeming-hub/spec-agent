# Payment Flow Optimization for Older Adults PRD (Japan Market)

> **Source Requirement**：日本市场想要一个能让老年用户更容易用的支付流程，现在很多高龄用户走到支付页就放弃了，大概下个季度要上线，最好也能覆盖我们自己的 App 和网页端。

## Background
Older adult users (65+) in the Japan market have a high abandonment rate after reaching the payment page on our own app and web. The current baseline is assumed to be 38% but needs confirmation with actual data. Older adults may face barriers with complex operations, small fonts, and multi-step flows. The project is planned for launch next quarter, covering our own app and web, without backend re-architecture or changes for other age groups.

## Goal
Optimize the payment flow for older adult users in the Japan market to reduce payment page abandonment rate to below 25%, increase payment completion rate to above 70%, shorten average completion time to under 3 minutes, reduce payment-related customer support complaints by 30%, achieve a usability test task completion rate of 90% or higher, and launch next quarter on our own app and web.

## Success Metrics
- 高龄用户支付页放弃率从当前基线（需确认）降低至25%以下，测量口径：支付页埋点漏斗中，进入支付页但未完成支付的用户占比，按年龄段（65+）拆分。
- 高龄用户支付完成率提升至70%以上，测量口径：支付成功事件数 / 进入支付页事件数，按年龄段（65+）拆分。
- 高龄用户支付流程平均完成时长缩短至3分钟以内，测量口径：从进入支付页到支付成功的时间戳差值，取中位数。
- 高龄用户支付相关客服投诉量下降30%，测量口径：客服系统中标记为支付问题的工单数，按用户年龄段（65+）筛选，对比上线前后一个月。
- 高龄用户支付流程任务完成率（可用性测试）达到90%以上，测量口径：招募20名65岁以上日本用户进行可用性测试，成功完成支付任务的比例。

## Stated Assumptions
- 假设高龄用户指65岁及以上人群，这是日本市场常见的老年定义。
- 假设当前支付页放弃率基线为38%（基于行业常见数据），但需实际数据确认。
- 假设下个季度上线指从当前日期起3个月内完成开发并发布。
- 假设自有App和网页端使用同一套支付后端，前端可独立优化。
- 假设日本市场常用支付方式包括信用卡、便利店支付、银行转账、电子货币等，优化需覆盖这些方式。
- 假设可用性测试可在上线前完成，并招募到足够的高龄用户。
- 假设支付页放弃率可通过现有埋点系统按年龄段拆分，若无法拆分则需新增埋点。

## User Stories

### US-1 · As an older adult user in the Japan market, I can see enlarged and high-contrast text and buttons on the payment page, so that I can easily read and tap them.

- Acceptance Criteria：Body text on the payment page is at least 18pt, buttons are at least 48pt in height, and text-to-background contrast ratio is at least 4.5:1.
- Acceptance Criteria：In usability testing, at least 18 out of 20 Japanese users aged 65+ can identify the main action button without assistance.

### US-2 · As an older adult user in the Japan market, I can complete payment using a simplified flow of no more than 3 steps, so that I reduce operational burden and abandonment.

- Acceptance Criteria：The required steps from entering the payment page to successful payment are no more than 3 (select payment method, confirm amount, complete payment).
- Acceptance Criteria：In usability testing, at least 18 out of 20 Japanese users aged 65+ can complete payment independently within 3 minutes.

### US-3 · As an older adult user in the Japan market, I can use common Japanese payment methods (credit card, convenience store payment, bank transfer, e-money), so that I can choose a method I am familiar with.

- Acceptance Criteria：The payment page displays at least four payment methods: credit card, convenience store payment, bank transfer, and e-money.
- Acceptance Criteria：The entry point for each payment method is visible on the first screen of the payment page, with at least three visible without scrolling.

### US-4 · As an older adult user in the Japan market, I can see error messages in large Japanese text with clear resolution suggestions when a payment error occurs, so that I know how to correct it.

- Acceptance Criteria：Error messages use a font size of at least 18pt, are in Japanese, and include at least one specific resolution suggestion (e.g., 'Please check your card number').
- Acceptance Criteria：In usability testing, at least 18 out of 20 Japanese users aged 65+ can independently correct the error based on the error message.

### US-5 · As an older adult user in the Japan market, I can see the current step and progress indicator at any time during payment, so that I understand how many more operations are needed.

- Acceptance Criteria：The payment page displays a step indicator (e.g., 'Step 1 of 3') with clear progress marking for each step.
- Acceptance Criteria：In usability testing, at least 18 out of 20 Japanese users aged 65+ can correctly state the current step and number of remaining steps.

## Functional Requirements
- The payment page supports font enlargement, with a default font size of at least 18pt and a one-tap option to enlarge to 24pt.
- Reduce the payment flow steps from the current number to no more than 3, merging redundant confirmation pages.
- Display four payment methods on the first screen: credit card, convenience store payment, bank transfer, and e-money, and remember the last used method.
- Error messages use large text (at least 18pt), Japanese, high contrast, and include specific resolution suggestions.
- The payment page displays a step indicator and progress bar, clearly showing the current step and total steps.
- Our own app and web use the same payment backend, with independent frontend optimization to ensure a consistent experience.
- The tracking system segments payment page funnel data by age group (65+); if not possible, add new tracking.

## Non-Functional Requirements
- Payment page load time is under 3 seconds on a 4G network.
- Usability testing for the payment flow recruits 20 Japanese users aged 65+ in Tokyo or Osaka and is conducted on real devices.
- The payment page complies with Japanese accessibility standards (JIS X 8341-3) Level AA.
- Payment-related customer support complaints are filtered by age group (65+) and compared one month before and after launch.
- Payment flow optimization does not involve backend re-architecture, and frontend changes do not affect users in other age groups.

## Risks
- The current payment page abandonment rate of 38% is an assumption; if the actual baseline differs, target thresholds need re-evaluation.
- If the definition of older adult users is not ultimately 65+, tracking segmentation and test recruitment need adjustment.
- The launch date next quarter is unspecified; if the hard deadline is earlier than 3 months, scope may need to be reduced.
- It is unconfirmed whether our own app and web share the same payment flow; if not, they need separate optimization.
- Common Japanese payment methods may include others (e.g., PayPay); adding them would involve business negotiations.
- Usability test recruitment channels and budget are unconfirmed, which may affect the test schedule.
- Payment flow optimization may involve compliance or security review; special regulatory requirements for older users in Japan are unconfirmed.
- It is unconfirmed whether the customer support system can filter by age group; if not, new fields need to be added.

## Open Questions
1. What is the accurate baseline for the current payment page abandonment rate among older adult users? Is the measurement segmented by age group?
2. What is the specific definition of older adult users? Is it 65+ or another standard?
3. What is the specific launch date next quarter? Is there a hard deadline?
4. Do our own app and web share the same payment flow? Do they need separate optimization?
5. What are the most commonly used payment methods among older adult users in the Japan market? Do we need to add or adjust payment methods?
6. Are there existing usability test resources or recruitment channels? What are the test budget and sample size requirements?
7. Does payment flow optimization involve compliance or security review? Are there special regulatory requirements for older users in Japan?
8. Are the thresholds in the success metrics (e.g., abandonment rate below 25%, completion rate above 70%) reasonable? What are the requester's expected target values?
9. How is 'payment-related customer support complaints from older adult users' defined and measured? Can the existing support system filter by age group?
10. Does the optimized payment flow need to support multiple languages (e.g., Japanese and English)?

## Glossary

| zh | en | ja | note |
| --- | --- | --- | --- |
| 高龄用户 | Older adult users | 高齢ユーザー | 本项目指日本市场65岁及以上的用户；若需求方最终定义不同，需同步更新所有语种文档与埋点口径。 |
| 支付页 | Payment page | 支払いページ | 用户进入后开始选择支付方式并确认支付的页面；漏斗起点为该页面的曝光事件。 |
| 支付页放弃率 | Payment page abandonment rate | 支払いページ離脱率 | 进入支付页但未完成支付的用户占比，按年龄段（65+）拆分。 |
| 支付完成率 | Payment completion rate | 支払い完了率 | 支付成功事件数 ÷ 进入支付页事件数，按年龄段（65+）拆分。 |
| 支付流程平均完成时长 | Average payment flow completion time | 支払いフロー平均完了時間 | 从进入支付页到支付成功的时间戳差值，取中位数。 |
| 支付相关客服投诉量 | Payment-related customer support complaints | 支払い関連のカスタマーサポート苦情件数 | 客服系统中标记为支付问题的工单数，按用户年龄段（65+）筛选。 |
| 可用性测试任务完成率 | Usability test task completion rate | ユーザビリティテストのタスク完了率 | 招募20名65岁以上日本用户进行可用性测试，成功完成支付任务的比例。 |
| 便利店支付 | Convenience store payment | コンビニ決済 | 日本常用支付方式之一，用户在线下便利店完成付款。 |
| 银行转账 | Bank transfer | 銀行振込 | 日本常用支付方式之一，用户通过银行账户转账完成付款。 |
| 电子货币 | E-money | 電子マネー | 日本常用支付方式之一，如交通系IC卡等。 |

<!-- Validation issues fixed in this round: [major/testability] US-3 的验收标准「每种支付方式的选择入口在支付页首屏可见，无需滚动即可看到至少三种」缺少可判定的阈值（如首屏高度、设备分辨率、可见比例），无法客观判定通过/不通过。涉及语种：zh、ja、en。 → 修改建议：在 US-3 验收标准中补充可判定条件，例如：在 375×667 及以上常见移动端视口下，至少三种支付方式入口的完整可点击区域位于首屏内（无需滚动），并明确测试设备/浏览器清单。；[major/testability] US-5 的验收标准「每一步都有明确的进度标识」中「明确」无判定标准，无法客观验收。涉及语种：zh、ja、en。 → 修改建议：将「明确的进度标识」改为可判定表述，例如：每一步均显示「步骤 N/总数」文本或等效进度条，且进度条填充比例与当前步骤数一致（如第 2/3 步时填充约 66%）。；[major/testability] 目标中的「支付页放弃率降至 25% 以下」「支付完成率提升至 70% 以上」「平均完成时长缩短至 3 分钟以内」「客服投诉量下降 30%」均基于假设基线 38%，但未标注为待验证假设，也未定义测量窗口与统计口径，存在验收争议风险。涉及语种：zh、ja、en。 → 修改建议：在 goal 中显式标注「基线 38% 为假设值，需以实际数据确认后锁定目标」，并为每个指标补充测量窗口（如上线后 4 周）、数据来源与统计口径（分子/分母、年龄段筛选方式）。；[major/completeness] 风险项与待确认问题未覆盖「优化后的支付流程是否需要支持多语言（日语和英语）」这一输入中的不确定性；该问题仅出现在 open_questions 中，未在 risks 中体现其对范围与验收的影响。涉及语种：zh、ja、en。 → 修改建议：在 risks 中新增一条：若优化后的支付流程需支持多语言（日语/英语），将影响文案、错误提示与可用性测试设计，需评估范围与排期；并在 open_questions 中保留对应问题。；[major/completeness] 风险项未覆盖「可用性测试样本量 20 名 65+ 用户是否足以支撑 90% 完成率目标」的统计不确定性，也未说明若招募不足时的替代方案。涉及语种：zh、ja、en。 → 修改建议：在 risks 中补充：20 名样本量对 90% 完成率的置信区间较宽，若招募不足或样本偏差，可能影响结论；建议明确最小可接受样本量与备选招募渠道。 -->
