import type { ValidationIssue, ValidationResult } from "@/lib/api";

const STATUS_TEXT: Record<string, string> = {
  passed: "校验通过：可直接进入评审",
  needs_review: "可交付：附评审清单",
  blocked: "存在阻塞问题：需人工介入",
};

const SEVERITY_LABEL: Record<string, string> = { blocker: "阻塞", major: "重要", minor: "建议" };

export default function ValidationPanel({ validation }: { validation: ValidationResult }) {
  const { status, counts, issues, summary } = validation;
  return (
    <div>
      <div className="badges" style={{ marginBottom: 10 }}>
        <span className={`badge ${status === "passed" ? "ok" : status === "needs_review" ? "warn" : "bad"}`}>
          {STATUS_TEXT[status] ?? status}
        </span>
        <span className="badge">阻塞 {counts.blocker}</span>
        <span className="badge">重要 {counts.major}</span>
        <span className="badge">建议 {counts.minor}</span>
        {validation.structural_issues > 0 ? (
          <span className="badge">结构校验 {validation.structural_issues}</span>
        ) : null}
      </div>
      <p className="hint" style={{ marginTop: 0 }}>{summary}</p>
      {issues.length === 0 ? (
        <p className="hint">没有发现问题。</p>
      ) : (
        issues.map((issue: ValidationIssue, index: number) => (
          <div className={`issue ${issue.severity}`} key={index}>
            <p className="title">
              <span className={`badge ${issue.severity === "blocker" ? "bad" : issue.severity === "major" ? "warn" : ""}`}>
                {SEVERITY_LABEL[issue.severity] ?? issue.severity}
              </span>{" "}
              <span className="mono hint">{issue.category}</span> {issue.message}
            </p>
            {issue.suggestion ? <p className="suggestion">修改建议：{issue.suggestion}</p> : null}
          </div>
        ))
      )}
    </div>
  );
}
