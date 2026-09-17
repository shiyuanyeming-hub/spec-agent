import type { ConsistencyReport } from "@/lib/api";

const COMPONENT_LABEL: Record<string, string> = {
  ids: "故事编号",
  ac: "AC 数量",
  numeric: "数字阈值",
  entity: "技术词保留",
  semantic: "语义（回译/向量）",
};

const METHOD_LABEL: Record<string, string> = {
  structural: "确定性信号（零额外成本）",
  backtranslate: "回译比对（每轮 1 次模型调用）",
  embeddings: "跨语言向量相似度",
};

function tone(score: number, report: ConsistencyReport) {
  if (score < report.thresholds.blocker_score) return "bad";
  if (score < report.thresholds.min_score) return "warn";
  return "";
}

function ScoreRow({ name, score, report }: { name: string; score: number; report: ConsistencyReport }) {
  return (
    <div className="score-row">
      <span className="name">{name}</span>
      <span className={`meter ${tone(score, report)}`}>
        <span style={{ width: `${Math.max(2, Math.min(100, score))}%` }} />
      </span>
      <span className="score-value">{score.toFixed(0)}</span>
    </div>
  );
}

export default function ConsistencyPanel({ report }: { report: ConsistencyReport | null }) {
  if (!report) {
    return <p className="hint">未启用三语一致性评分（CONSISTENCY_METHOD=off）。</p>;
  }
  if (report.pairs.length === 0) {
    return (
      <div>
        <p className="hint" style={{ marginTop: 0 }}>
          {report.notes.join(" ")}
        </p>
        <ScoreRow name="术语覆盖率" score={report.terminology_coverage * 100} report={report} />
      </div>
    );
  }

  const badgeClass = report.overall < report.thresholds.blocker_score ? "bad" : report.overall < report.thresholds.min_score ? "warn" : "ok";

  return (
    <div>
      <div className="badges" style={{ marginBottom: 12 }}>
        <span className={`badge ${badgeClass}`}>整体一致性 {report.overall.toFixed(0)} 分</span>
        <span className="badge">基准语种 {report.pivot_label}</span>
        <span className="badge">{METHOD_LABEL[report.method] ?? report.method}</span>
        <span className="badge">
          通过线 {report.thresholds.min_score} · 阻塞线 {report.thresholds.blocker_score}
        </span>
      </div>

      {report.pairs.map((pair) => (
        <div key={pair.lang} style={{ marginBottom: 14 }}>
          <ScoreRow name={`${pair.label} ↔ ${report.pivot_label}`} score={pair.score} report={report} />
          <div className="components">
            {Object.entries(pair.components).map(([key, value]) => (
              <span key={key} className="badge">
                {COMPONENT_LABEL[key] ?? key} {(value * 100).toFixed(0)}%
              </span>
            ))}
            {pair.missing_ids.length > 0 ? <span className="badge bad">编号缺失 {pair.missing_ids.join("、")}</span> : null}
          </div>
        </div>
      ))}

      <ScoreRow name="术语覆盖率" score={report.terminology_coverage * 100} report={report} />

      {report.divergences.length > 0 ? (
        <>
          <h3>需要人工复核的条目（{report.divergences.length}）</h3>
          {report.divergences.map((item, index) => (
            <div className="divergence" key={`${item.lang}-${item.story_id}-${index}`}>
              <p>
                <span className="badge warn">{item.label}</span>{" "}
                <strong>{item.story_id}</strong> · {item.score.toFixed(0)} 分 · {item.reason}
              </p>
              <div className="textpair">
                <div>
                  <b>基准语种（{report.pivot_label}）</b>
                  <div>{item.pivot_text || "—"}</div>
                </div>
                <div>
                  <b>{report.method === "backtranslate" ? "回译结果" : "该语种原文"}</b>
                  <div>{item.back_text || "—"}</div>
                </div>
              </div>
            </div>
          ))}
        </>
      ) : (
        <p className="hint">各语种结构、阈值与技术词均对齐，没有需要人工复核的条目。</p>
      )}

      {report.notes.length > 0 ? <p className="hint">{report.notes.join(" ")}</p> : null}
    </div>
  );
}
